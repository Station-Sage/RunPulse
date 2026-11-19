"""부상 에피소드 → 조정 단독 트리거·AI 일반화·삭제 연쇄 (ADR-058)."""
import json
import sqlite3

import pytest

from src.db_setup import create_tables
from src.services import adjuster_v3
from src.services import adjustment_signals as S
from src.services import adjustment_signals_context as C
from src.services import adjustment_triggers_v3 as T
from src.services import context_episodes as E
from src.services import insight_rules as R
from src.services.adjustment_labels import trigger_label
from src.services.context_episode_delete import delete_episode
from src.services.illness_consent import redact_health_for_ai
from tests.helpers_pred import mem_conn

D = "2026-10-08"
HOLD = {"hold": False, "reasons": []}


def _ep(c, start, end=None, sev=None, kind="injury", last=None):
    c.execute("INSERT INTO context_episodes(kind,start_date,end_date,severity,detail_json,origin,status,last_confirmed_date)"
              " VALUES(?,?,?,?,?,'user','confirmed',?)", (kind, start, end, sev, json.dumps({"site": "무릎"}), last or start))


def _sig(c, day):
    return C.collect_injury(c, day)[0]


def _eval(c, day):
    return S.evaluate(S.collect(c, day, readiness={"fatigue_level": 0}, crs=None, hold=HOLD))


@pytest.fixture
def c():
    return mem_conn()


def test_active_injury_is_standalone_trigger(c):
    _ep(c, "2026-10-05", sev=2)
    s = _sig(c, D)
    assert s["value"] == 2 and s["detail"]["phase"] == "active" and s["detail"]["day_n"] == 4
    assert "site" not in s["detail"]                       # 부위는 신호에 싣지 않는다
    ev = _eval(c, D)
    assert "injury" in ev["triggers"] and ev["source"] == "pain" and ev["intensity"] == "rest"


def test_mild_active_injury_reduces(c):
    _ep(c, "2026-10-05", sev=1)
    assert _eval(c, D)["intensity"] == "reduce"
    c.execute("UPDATE context_episodes SET severity=NULL")
    assert _sig(c, D)["value"] == 1 and _eval(c, D)["intensity"] == "reduce"


def test_return_window_triggers_reduce_then_ends(c):
    _ep(c, "2026-10-01", end="2026-10-05", sev=2)
    assert _sig(c, "2026-10-05")["detail"]["phase"] == "active"          # 종료일 당일은 진행 중
    for day, n in (("2026-10-06", 1), ("2026-10-08", 3)):
        s = _sig(c, day)
        assert s["detail"] == {"episode_id": 1, "phase": "return", "day_n": n} and s["value"] == 2
        ev = _eval(c, day)
        assert "injury" in ev["triggers"] and ev["intensity"] == "reduce"   # 많이 아팠어도 복귀 구간은 reduce
    ended = _sig(c, "2026-10-09")
    assert ended["value"] is False and ended["detail"] == {}
    assert "injury" not in _eval(c, "2026-10-09")["triggers"]


def test_unconfirmed_or_future_injury_ignored(c):
    c.execute("INSERT INTO context_episodes(kind,start_date,severity,detail_json,origin,status)"
              " VALUES('injury','2026-10-05',2,'{}','user','candidate')")
    _ep(c, "2026-10-10", sev=2)
    assert _sig(c, D)["value"] is False


def test_illness_and_pain_unchanged():
    ill = {"signal": "illness", "value": 1, "freshness": "fresh", "detail": {}}
    assert T.triggered([ill]) == ["illness"] and T.intensity([ill], ["illness"]) == "rest" and T.primary(["illness"]) == "illness"
    pain = {"signal": "pain", "value": True, "freshness": "fresh"}
    assert T.intensity([pain], ["pain"]) == "rest" and T.primary(["pain"]) == "pain"
    inj = {"signal": "injury", "value": 1, "freshness": "fresh", "detail": {"phase": "active"}}
    assert T.primary(["injury", "illness"]) == "pain" and T.intensity([inj, ill], ["illness", "injury"]) == "rest"


def _plan_conn(wtype):
    x = sqlite3.connect(":memory:")
    create_tables(x)
    x.execute("INSERT INTO planned_workouts(id,date,workout_type,distance_km) VALUES (7,?,?,10.0)", (D, wtype))
    return x


def test_propose_uses_generic_reason(monkeypatch):
    monkeypatch.setattr("src.metrics.crs.evaluate", lambda conn, day: None)
    x = _plan_conn("interval")
    _ep(x, "2026-10-07", sev=2)
    w, sig = adjuster_v3.propose(x, D, HOLD)
    assert w["adjusted_type"] == "rest" and w["source"] == "pain"
    assert w["adjustment_reason"] == "컨디션 이상 신호" and "부상" not in json.dumps(w["reasons"], ensure_ascii=False)
    assert [s["signal"] for s in sig if s["role"] == "trigger"] == ["injury"]
    y = _plan_conn("interval")
    _ep(y, "2026-10-01", end="2026-10-06", sev=2)                       # 복귀 구간: 품질 → 이지
    assert adjuster_v3.propose(y, D, HOLD)[0]["adjusted_type"] == "easy"
    z = _plan_conn("easy")
    _ep(z, "2026-10-01", end="2026-10-06", sev=2)                       # 이지는 그대로(제안 없음)
    assert adjuster_v3.propose(z, D, HOLD)[0] is None


@pytest.mark.parametrize("consent", [False, True])
def test_injury_always_redacted_for_ai(monkeypatch, consent):
    monkeypatch.setattr("src.services.illness_consent.has_consent", lambda conn: consent)
    sigs = [{"signal": "injury", "role": "trigger", "value": 2, "detail": {"phase": "active", "episode_id": 3}},
            {"signal": "illness", "role": "trigger", "value": 1, "detail": {"site": "목"}}]
    out = redact_health_for_ai(None, sigs)
    assert out[0] == {"signal": "condition", "role": "trigger", "value": "컨디션 신호", "detail": None, "provider": "context"}
    assert out[1]["signal"] == ("illness" if consent else "condition")
    assert trigger_label(out[0]) == "컨디션 신호" and trigger_label(sigs[0]) == "부상 기록"


def test_insight_hides_injury_signal():
    cand = R.evaluate_signal_rules([{"signal": "injury", "value": 2, "freshness": "fresh", "detail": {"phase": "active"}}])
    assert [x["kind"] for x in cand] == ["pain_flag"] and cand[0]["signals"] == [] and "부상" not in cand[0]["text"]


def _adj(c, decision, signals):
    c.execute("INSERT INTO planned_workouts(date, workout_type, source) VALUES ('2026-10-20','interval','manual')")
    wid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    c.execute("INSERT INTO plan_adjustments(workout_id,date,source,before_json,after_json,reasons_json,signals_json,"
              "rule_version,decision) VALUES (?,?,?,?,?,?,?,?,?)",
              (wid, "2026-10-20", "pain", "{}", "{}", "[]", json.dumps(signals), "adjuster_v3", decision))
    return c.execute("SELECT last_insert_rowid()").fetchone()[0]


def test_delete_injury_withdraws_injury_only_proposal(c):
    e = E.open_episode(c, "injury", severity=2)
    inj = {"signal": "injury", "role": "trigger", "value": 2, "detail": {"phase": "active", "episode_id": e}}
    only = _adj(c, "proposed", [inj])
    mixed = _adj(c, "proposed", [inj, {"signal": "pain", "role": "trigger", "value": True}])
    acc = _adj(c, "accepted", [inj])
    assert delete_episode(c, e) == {"kind": "injury", "chat_deleted": 0}
    rows = {i: c.execute("SELECT decision, signals_json FROM plan_adjustments WHERE id=?", (i,)).fetchone()
            for i in (only, mixed, acc)}
    assert [rows[i][0] for i in (only, mixed, acc)] == ["reverted", "proposed", "accepted"]
    assert all('"injury"' not in sj and "condition" in sj for _d, sj in rows.values())

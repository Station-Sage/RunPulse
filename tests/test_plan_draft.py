"""AI 플랜 초안 — 검증 게이트·캐시·적용 (V2-AI-CLAUDE-QUEUE E5-c)."""
import json
import sqlite3

import pytest

from src.ai import provider_claude_queue as pcq
from src.db_setup import create_tables, migrate_db
from src.services import plan_draft as PD
from src.services import plan_replan_service as svc

WS = "2026-11-23"
CONS = {"goal": {}, "prefs": {"workout_weekdays": ["월", "화", "수", "목", "금", "토", "일"]},
        "limits": {"min_session_km": 6.0, "easy_max_km": 16, "long_abs_cap_km": 32}}
BASE = {WS: [
    {"date": "2026-11-23", "workout_type": "easy", "distance_km": 10.0, "description": "이지 10.0km"},
    {"date": "2026-11-25", "workout_type": "tempo", "distance_km": 12.0, "description": "템포 12.0km", "structure": {"a": 1}},
    {"date": "2026-11-29", "workout_type": "long", "distance_km": 20.0, "description": "롱런 20.0km"}]}
INP = {"constraints": CONS, "baseline": [{"week_start": WS, "sessions": []}]}


def _out(sessions, summary="이지 거리를 소폭 늘렸어요."):
    return json.dumps({"summary": summary, "weeks": [{"week_start": WS, "sessions": sessions}]}, ensure_ascii=False)


def _s(date, km, desc=None, why="회복 여유"):
    return {"date": date, "distance_km": km, "description": desc or f"이지 {km}km", "rationale": why}


@pytest.mark.parametrize("sessions,ok", [
    ([_s("2026-11-23", 11.0)], True),
    ([_s("2026-11-23", 12.0)], False),                       # +20% > 15%
    ([_s("2026-11-23", 11.0, "이지 9.0km")], False),          # 설명 km 불일치
    ([_s("2026-11-25", 13.0, "템포 13.0km")], False),         # 품질 세션 거리 변경
    ([_s("2026-11-24", 8.0)], False),                        # 알 수 없는 날짜
    ([_s("2026-11-29", 24.0, "롱런 24.0km")], False),         # 롱런 +20%
    ([_s("2026-11-29", 22.0, "롱런 22.0km")], True),
    ([_s("2026-11-23", 11.0, why="가" * 81)], False),
    ([_s("2026-11-23", 11.0, why="**강조**")], False),
])
def test_validate_gates(sessions, ok):
    res, why = PD.validate(INP, BASE, _out(sessions))
    assert (res is not None) is ok, why


def test_validate_merges_and_keeps_fixed_fields():
    res, _ = PD.validate(INP, BASE, _out([_s("2026-11-23", 11.0)]))
    rows = res["weeks"][WS]
    assert rows[0]["distance_km"] == 11.0 and rows[0]["rationale"] == "회복 여유"
    assert rows[1] == BASE[WS][1] and BASE[WS][0]["distance_km"] == 10.0   # 원본 불변


@pytest.mark.parametrize("out", [None, "not json", "{}", _out([], summary="")])
def test_validate_bad_format(out):
    assert PD.validate(INP, BASE, out)[0] is None


@pytest.fixture
def conn(tmp_path):
    c = sqlite3.connect(str(tmp_path / "running.db"))
    create_tables(c)
    migrate_db(c)
    return c


def _patch(monkeypatch, out):
    monkeypatch.setattr(svc, "preview", lambda c, p, t=None: {"plan_rows": [r for rs in BASE.values() for r in rs],
                                                              "anchor_monday": WS})
    monkeypatch.setattr(PD, "build_input", lambda c, b, m=None: INP)
    monkeypatch.setattr(pcq, "available", lambda c, cfg: True)
    calls = []
    monkeypatch.setattr(pcq, "try_complete", lambda *a, **k: calls.append(k) or out)
    return calls


def test_generate_ready_then_cached(conn, monkeypatch):
    calls = _patch(monkeypatch, _out([_s("2026-11-23", 11.0)]))
    body = PD.generate(conn, {}, {})
    assert body["state"] == "ready" and body["changed"] == 1 and calls[0]["kind"] == "plan_draft"
    assert PD.latest(conn)["state"] == "ready"
    PD.generate(conn, {}, {})
    assert len(calls) == 1


def test_generate_failure_records_reason(conn, monkeypatch):
    _patch(monkeypatch, _out([_s("2026-11-23", 14.0)]))
    body = PD.generate(conn, {}, {})
    assert body["state"] == "failed" and "±15%" in body["reason"]


def test_generate_retries_with_reason(conn, monkeypatch):
    calls = _patch(monkeypatch, None)
    outs = iter([_out([_s("2026-11-23", 14.0)]), _out([_s("2026-11-23", 11.0)])])
    monkeypatch.setattr(pcq, "try_complete", lambda *a, **k: calls.append(k) or next(outs))
    body = PD.generate(conn, {}, {})
    assert body["state"] == "ready" and len(calls) == 2
    assert "±15%" in calls[1]["prompt"]


def test_apply_draft_passes_override(conn, monkeypatch):
    _patch(monkeypatch, _out([_s("2026-11-23", 11.0)]))
    PD.generate(conn, {}, {})
    seen = {}
    monkeypatch.setattr(svc, "apply", lambda c, p, t=None: seen.update(p) or {"replan_id": 1})
    assert PD.apply_draft(conn, WS) == {"replan_id": 1}
    assert seen["plan_override"][WS][0]["distance_km"] == 11.0 and seen["expect_anchor"] == WS
    with pytest.raises(svc.ReplanError) as e:
        PD.apply_draft(conn, "2026-01-01")
    assert e.value.code == "CONFLICT"


def test_apply_without_draft(conn):
    with pytest.raises(svc.ReplanError) as e:
        PD.apply_draft(conn, WS)
    assert e.value.code == "NO_DRAFT"


def test_check_week_ignores_baseline_violations(monkeypatch):
    import src.training.plan_finalize as pf
    monkeypatch.setattr(pf, "week_violations", lambda rows, days: ["2026-11-23: 기존 위반"])
    base = [{"date": "2026-11-23", "workout_type": "easy", "distance_km": 10.0}]
    new = [{"date": "2026-11-23", "workout_type": "easy", "distance_km": 11.0}]
    assert PD._check_week(WS, base, new, INP) is None


def test_method_long_cap_gate():
    inp = {**INP, "method": {"long_cap_km": 21.0}}
    new = [dict(BASE[WS][0]), dict(BASE[WS][1]), {**BASE[WS][2], "distance_km": 22.0, "description": "롱런 22.0km"}]
    assert "방식의 롱런 상한" in PD._check_week(WS, BASE[WS], new, inp)
    assert PD._check_week(WS, BASE[WS], new, INP) is None


def test_method_info_and_input_hash(conn):
    info = PD.method_info("hansons")
    assert info["id"] == "hansons" and info["long_cap_km"] == 26.0 and info["ai_note"]
    a = PD.build_input(conn, BASE, "balanced")
    b = PD.build_input(conn, BASE, "hansons")
    assert PD.src_hash(a) != PD.src_hash(b)

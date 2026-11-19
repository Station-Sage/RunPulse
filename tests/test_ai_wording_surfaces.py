"""ADR-059 1단계 표면 — Today 조정·보류 사유, '이 러닝의 의미', Story 문단 (캐시 적중·미스·해시 변경·익명화·폴백)."""
from __future__ import annotations

import json
import sqlite3

import pytest

from src.db_setup import create_tables, migrate_db
from src.services import activity_impact_wording as aiw
from src.services import ai_wording as aw
from src.services import ai_wording_live as live
from src.services import story_service as ss
from src.services import story_wording as sw
from src.services import today_hero
from src.services import today_reason_wording as trw
from src.training.goals import add_goal

DAY = "2026-09-29"


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    migrate_db(c)
    yield c
    c.close()


@pytest.fixture(autouse=True)
def _no_threads(monkeypatch):
    """요청 경로가 예약하는 백그라운드 생성을 기록만 한다."""
    calls: list = []
    monkeypatch.setattr(aw, "warm_in_background", lambda *a, **k: calls.append(a))
    live.reset_cooldown()
    return calls


def _seed(c, surface, it: aw.Item, text: str) -> None:
    c.execute("INSERT OR REPLACE INTO ai_outputs(kind, scope_key, src_hash, body_json, created_at) VALUES (?,?,?,?,?)",
              (surface.kind, it.scope_key, aw.src_hash(surface, it), json.dumps({"text": text}), "t"))


# ── 공통: 요청 경로 예약 ───────────────────────────────────────────────────────

def test_present_or_warm_schedules_once_and_not_on_hit(conn, monkeypatch, _no_threads):
    monkeypatch.setattr(live, "_db_path", lambda c: "/tmp/x.db")
    it = aw.Item("k", "규칙 문장이에요.", {"tsb": -12.0})
    assert live.present_or_warm(conn, {}, trw.SURFACE, it) == {"text": "규칙 문장이에요.", "source": "rule"}
    live.present_or_warm(conn, {}, trw.SURFACE, it)          # 쿨다운 — 다시 예약하지 않음
    assert len(_no_threads) == 1
    _seed(conn, trw.SURFACE, it, "TSB 가 낮아 오늘은 쉬어 가요.")
    assert live.present_or_warm(conn, {}, trw.SURFACE, it)["source"] == "ai"
    assert len(_no_threads) == 1
    assert live.present_or_warm(conn, {}, trw.SURFACE, None) is None


def test_present_or_warm_memory_db_never_schedules(conn, _no_threads):
    live.present_or_warm(conn, {}, trw.SURFACE, aw.Item("k", "문장", {}))
    assert _no_threads == []


# ── Today 조정·보류 사유 ─────────────────────────────────────────────────────

def _today(conn, monkeypatch, adj: dict):
    gid = add_goal(conn, "테스트 대회", 42.195, race_date="2026-12-06")
    conn.execute("UPDATE goals SET created_at='2026-09-01 00:00:00', plan_weeks=14 WHERE id=?", (gid,))
    conn.execute("INSERT INTO planned_workouts (date, workout_type, distance_km, source, completed, goal_id)"
                 " VALUES (?, 'tempo', 10, 'planner', 0, 1)", (DAY,))
    base = {"id": 1, "date": DAY, "workout_type": "tempo", "distance_km": 10, "target_pace_min": None,
            "target_pace_max": None, "target_hr_zone": None, "original_type": "tempo", "adjusted_type": "tempo",
            "adjusted": False, "adjustment_reason": None, "volume_boost": False, "boost_held": False,
            "hold_reason": None, "fatigue_level": "high", "wellness": {"body_battery": 40, "sleep_score": 55},
            "tsb": -18.3}
    monkeypatch.setattr(today_hero, "todays_adjustment_with_hold", lambda c, d: {**base, **adj})
    return today_hero.build_briefing_state(conn, DAY, today_hero.build_week(conn, DAY))


def test_today_adjust_rule_then_ai(conn, monkeypatch):
    adj = {"adjusted": True, "adjusted_type": "easy", "adjustment_reason": "피로도 높음: TSB -18.3"}
    st = _today(conn, monkeypatch, adj)
    assert st["verdict"] == "down" and st["adjustment"]["to"] == "이지런"      # 판정은 규칙 그대로
    assert st["reason_wording"]["source"] == "rule"
    it = trw.item(conn, DAY, st, {**adj, "fatigue_level": "high", "wellness": {"body_battery": 40}}, None, 68)
    assert it.rule_text == "피로도 높음: TSB -18.3 — 오늘은 템포 대신 이지런으로 해요."
    assert it.facts["kind"] == "adjust" and it.facts["race_days_left"] == 68 and it.facts["fatigue"] == "높음"


def test_today_reason_ai_cached_and_stale_on_fact_change(conn, monkeypatch):
    adj = {"adjusted": True, "adjusted_type": "easy", "adjustment_reason": "피로도 높음: TSB -18.3"}
    st = _today(conn, monkeypatch, adj)
    week = today_hero.build_week(conn, DAY)
    _, a = today_hero.briefing_core(conn, DAY, week)
    it = trw.item(conn, DAY, st, a, week, today_hero.race_days_left(conn, DAY))
    _seed(conn, trw.SURFACE, it, "TSB -18 로 피로가 쌓여 대회 68일 전이라도 오늘은 이지런으로 가요.")
    st2 = today_hero.build_briefing_state(conn, DAY, week)
    assert st2["reason_wording"]["source"] == "ai"
    conn.execute("UPDATE planned_workouts SET distance_km=12")    # 근거(거리) 변경 → 규칙 문구
    st3 = today_hero.build_briefing_state(conn, DAY, today_hero.build_week(conn, DAY))
    assert st3["reason_wording"]["source"] == "rule"


def test_today_hold_reason_item(conn, monkeypatch):
    st = _today(conn, monkeypatch, {"boost_held": True,
                                    "hold_reason": [{"code": "crs_stale", "text": "컨디션 입력이 오래돼 증량은 보류했어요"}]})
    assert st["hold_reason"] and st["reason_wording"] == {"text": "컨디션 입력이 오래돼 증량은 보류했어요.", "source": "rule"}


def test_today_health_reason_redacted_for_ai(conn, monkeypatch):
    st = _today(conn, monkeypatch, {"adjusted": True, "adjusted_type": "easy",
                                    "adjustment_reason": "무릎 통증 기록이 있어요."})
    it = trw.item(conn, DAY, st, None, None, None)
    payload = aw._payload(trw.SURFACE, it)
    assert "무릎" not in json.dumps(payload, ensure_ascii=False) and aw.GENERIC_HEALTH in payload["text"]
    assert not any(t in json.dumps(it.facts, ensure_ascii=False) for t in aw.HEALTH_TERMS)


def test_today_no_reason_no_wording(conn, monkeypatch):
    assert _today(conn, monkeypatch, {})["reason_wording"] is None


# ── 이 러닝의 의미 ──────────────────────────────────────────────────────────

FULL = {"ctl_contribution": 2.3, "tsb": 5.2, "race": {"name": "서울마라톤", "days_left": 30},
        "similar": {"n": 6, "pace_rank": 2, "avg_pace_sec_km": 340, "pace_diff_sec": -12.4}}


def test_impact_lines_parity_with_old_frontend():
    lines = aiw.impact_lines(FULL)
    assert lines == ["이 날 체력(CTL) +2.3 · 폼(TSB) +5", "비슷한 거리 이전 6회 중 2번째로 빠른 페이스 (평균보다 12초/km 빠름)",
                     "서울마라톤 D-30에 쌓은 세션"]
    same = aiw.impact_lines({**FULL, "similar": {**FULL["similar"], "pace_diff_sec": 0}})
    assert "평균과 같음" in same[1]
    assert aiw.impact_lines({"ctl_contribution": None, "tsb": None, "similar": None, "race": None}) == [
        "판정할 기준이 아직 부족해요(같은 유형·코스 기록 5회 필요)"]
    cls = aiw.impact_lines({**FULL, "similar": {"basis": "same_class", "class_label": "이지런", "n": 8, "pace_rank": 3,
                                                 "avg_pace_sec_km": 340, "pace_diff_sec": 5, "load_median": 72,
                                                 "load_pct_vs_median": 35.2}})
    assert cls[1].startswith("같은 이지런 이전 8회") and cls[2] == "부하 대비: 같은 이지런 중앙값 72 대비 +35%"
    assert aiw.impact_lines({**FULL, "similar": {**FULL["similar"], "basis": "same_course"}})[1].startswith("같은 코스 이전")
    assert aiw.impact_lines({"ctl_contribution": -0.4, "tsb": -2.5})[0] == "이 날 체력(CTL) -0.4 · 폼(TSB) -2"


def _activity(conn):
    conn.execute("INSERT INTO activity_summaries (source, source_id, name, activity_type, start_time, distance_m,"
                 " duration_sec, avg_pace_sec_km) VALUES ('garmin','x','무릎 아픈 날','running','2026-09-28T07:00:00',"
                 " 10000, 3600, 360)")
    aid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute("INSERT INTO planned_workouts (date, workout_type, distance_km, source, completed, matched_activity_id)"
                 " VALUES ('2026-09-28','long',10,'manual',1,?)", (aid,))
    return aid


def test_impact_attach_rule_ai_and_hash(conn):
    aid = _activity(conn)
    out = aiw.attach(conn, aid, dict(FULL), {}, schedule=True)
    assert out["lines"] == aiw.impact_lines(FULL) and out["wording"]["source"] == "rule"
    it = aiw.item(conn, aid, FULL, out["lines"])
    assert it.scope_key == str(aid) and it.facts["planned"] == "롱런" and it.facts["avg_pace"] == "6:00/km"
    assert "무릎" not in json.dumps(it.facts, ensure_ascii=False)        # 활동 이름(자유 입력)은 보내지 않는다
    _seed(conn, aiw.SURFACE, it, "계획한 롱런 10km 를 대회 30일 전에 채워 체력(CTL)을 2.3 올렸어요.")
    assert aiw.attach(conn, aid, dict(FULL), None, schedule=False)["wording"]["source"] == "ai"
    changed = {**FULL, "ctl_contribution": 2.5}
    assert aiw.attach(conn, aid, changed, None, schedule=False)["wording"]["source"] == "rule"


def test_impact_attach_none():
    assert aiw.attach(None, 1, None, None) is None


# ── Story 문단 ─────────────────────────────────────────────────────────────

def _story_db(conn):
    for sid, st, dist in (("a1", "2026-09-02T07:00:00", 10000), ("a2", "2026-09-10T07:00:00", 21000)):
        conn.execute("INSERT INTO activity_summaries (source, source_id, name, activity_type, start_time, distance_m,"
                     " duration_sec) VALUES ('garmin', ?, '통증 러닝', 'running', ?, ?, 3000)", (sid, st, dist))


def test_story_rule_then_ai_then_stale(conn):
    _story_db(conn)
    r = ss.get_story(conn, "2026-09")
    assert r["paragraph_source"] == "rule" and "paragraph_rule" not in r
    rule = ss.build_story(conn, "2026-09")
    it = sw.item(rule, rule["paragraph_rule"])
    assert it.scope_key == "2026-09" and "통증" not in json.dumps(it.facts, ensure_ascii=False)
    _seed(conn, sw.SURFACE, it, "9월은 31km를 2회 달렸어요. 하프 거리 롱런이 이번 달의 중심이었어요.")
    r2 = ss.get_story(conn, "2026-09")
    assert r2["paragraph_source"] == "ai" and r2["paragraph"].startswith("9월은")
    conn.execute("INSERT INTO activity_summaries (source, source_id, activity_type, start_time, distance_m, duration_sec)"
                 " VALUES ('garmin','a3','running','2026-09-20T07:00:00',5000,1500)")
    assert ss.get_story(conn, "2026-09")["paragraph_source"] == "rule"


def test_story_no_records_and_future_have_no_item(conn):
    empty = ss.build_story(conn, "2020-01")
    assert sw.item(empty, empty["paragraph_rule"]) is None
    assert ss.get_story(conn, "2020-01")["paragraph_source"] == "rule"
    fut = ss.build_story(conn, "2099-01")
    assert sw.item(fut, fut["paragraph_rule"]) is None


def test_story_current_periods():
    assert sw.current_periods("2026-11-19") == ["2026-11", "2026-W47"]


# ── 동기화 워밍 collect ─────────────────────────────────────────────────────

def test_collectors_run_on_db(conn, monkeypatch):
    _story_db(conn)
    assert [i.scope_key for i in sw.collect(conn, "2026-09-10")] == ["2026-09", "2026-W37"]
    assert trw.collect(conn, DAY) == []
    items = aiw.collect(conn)
    assert items and all(i.rule_text for i in items)


def test_warm_after_sync_runs_all_surfaces(tmp_path, monkeypatch):
    p = tmp_path / "r.db"
    c = sqlite3.connect(p)
    create_tables(c)
    migrate_db(c)
    c.close()
    seen: list = []
    monkeypatch.setattr(aw, "warm", lambda conn, cfg, s, items: seen.append(s.name) or 0)

    class _Sync:
        def __init__(self, target, **kw):
            self.target = target

        def start(self):
            self.target()
    monkeypatch.setattr(live.threading, "Thread", _Sync)
    live.warm_after_sync(str(p), {})
    assert seen == ["today_reason", "story_paragraph", "activity_impact"]


def test_story_warm_end_to_end_and_invalid_falls_back(conn, monkeypatch):
    """큐 응답이 근거 수치만 쓰면 저장돼 AI 문단, 새 수치를 만들면 거부돼 규칙 문단."""
    from src.ai import llm_budget
    from src.ai import provider_claude_queue as pcq
    _story_db(conn)
    conn.execute("INSERT INTO coach_consent (id, provider, accepted_at) VALUES (1, 'claude_queue', 't')")
    monkeypatch.setattr(pcq, "available", lambda *a, **k: True)
    monkeypatch.setattr(llm_budget, "global_ratio", lambda: 0.0)
    reply = {"text": "9월엔 31km를 2회 달렸고 99km 롱런이 있었어요."}
    monkeypatch.setattr(pcq, "try_complete", lambda c, cfg, **kw: json.dumps([{"id": "2026-09", **reply}]))
    rule = ss.build_story(conn, "2026-09")
    it = sw.item(rule, rule["paragraph_rule"])
    assert aw.warm(conn, {}, sw.SURFACE, [it]) == 0                  # 99 는 근거에 없는 수치 → 거부
    assert ss.get_story(conn, "2026-09")["paragraph_source"] == "rule"
    reply["text"] = "9월엔 31km를 2회 달렸어요. 21km 롱런이 이번 달의 중심이었어요."
    assert aw.warm(conn, {}, sw.SURFACE, [it]) == 1
    assert ss.get_story(conn, "2026-09")["paragraph_source"] == "ai"

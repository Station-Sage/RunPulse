"""계획 조정 카드의 Today '오늘 이유' AI 문장 재사용(ADR-059 D20) — 캐시만, adjust 사유만, 실패는 None."""
from __future__ import annotations

import json
import sqlite3

import pytest

from src.db_setup import create_tables, migrate_db
from src.services import ai_wording as aw
from src.services import today_hero
from src.services import today_reason_wording as trw
from src.training.goals import add_goal

DAY = "2026-09-29"
ADJ = {"adjusted": True, "adjusted_type": "easy", "adjustment_reason": "피로도 높음: TSB -18.3"}


@pytest.fixture
def conn(monkeypatch):
    c = sqlite3.connect(":memory:")
    create_tables(c)
    migrate_db(c)
    gid = add_goal(c, "테스트 대회", 42.195, race_date="2026-12-06")
    c.execute("UPDATE goals SET created_at='2026-09-01 00:00:00', plan_weeks=14 WHERE id=?", (gid,))
    c.execute("INSERT INTO planned_workouts (date, workout_type, distance_km, source, completed, goal_id)"
              " VALUES (?, 'tempo', 10, 'planner', 0, 1)", (DAY,))
    yield c
    c.close()


def _patch(monkeypatch, adj: dict):
    base = {"id": 1, "date": DAY, "workout_type": "tempo", "distance_km": 10, "target_pace_min": None,
            "target_pace_max": None, "target_hr_zone": None, "original_type": "tempo", "adjusted_type": "tempo",
            "adjusted": False, "adjustment_reason": None, "volume_boost": False, "boost_held": False,
            "hold_reason": None, "fatigue_level": "high", "wellness": {"body_battery": 40, "sleep_score": 55},
            "tsb": -18.3}
    monkeypatch.setattr(today_hero, "todays_adjustment_with_hold", lambda c, d: {**base, **adj})


def _seed(c, text: str):
    it = trw.collect(c, DAY)[0]
    c.execute("INSERT OR REPLACE INTO ai_outputs(kind, scope_key, src_hash, body_json, created_at) VALUES (?,?,?,?,?)",
              (trw.SURFACE.kind, it.scope_key, aw.src_hash(trw.SURFACE, it), json.dumps({"text": text}), "t"))


def test_rule_only_returns_none(conn, monkeypatch):
    _patch(monkeypatch, ADJ)
    assert trw.ai_view_for_adjustment(conn, DAY) is None


def test_same_ai_sentence_as_today(conn, monkeypatch):
    _patch(monkeypatch, ADJ)
    _seed(conn, "TSB -18 로 피로가 쌓여 오늘은 이지런으로 가요.")
    hero = today_hero.build_briefing_state(conn, DAY, today_hero.build_week(conn, DAY))["reason_wording"]
    assert trw.ai_view_for_adjustment(conn, DAY) == hero == {"text": "TSB -18 로 피로가 쌓여 오늘은 이지런으로 가요.",
                                                             "source": "ai"}
    conn.execute("UPDATE planned_workouts SET distance_km=14")     # 근거 변경 → 낡은 문장은 쓰지 않음
    assert trw.ai_view_for_adjustment(conn, DAY) is None


def test_hold_reason_is_not_adjustment(conn, monkeypatch):
    _patch(monkeypatch, {"boost_held": True, "hold_reason": [{"code": "crs_stale", "text": "컨디션 입력이 오래돼 보류"}]})
    _seed(conn, "컨디션 입력이 오래돼 증량은 잠시 보류해요.")
    assert trw.ai_view_for_adjustment(conn, DAY) is None


def test_errors_fall_back_to_none(conn, monkeypatch):
    monkeypatch.setattr(trw, "collect", lambda c, d: (_ for _ in ()).throw(RuntimeError("x")))
    assert trw.ai_view_for_adjustment(conn, DAY) is None


def test_route_attaches_only_for_live_proposal(monkeypatch):
    from src.api import routes_plan
    from src.services import plan_adjustment_service as pas
    from src.services import plan_service
    calls: list = []
    monkeypatch.setattr(trw, "ai_view_for_adjustment", lambda c, d: calls.append(d) or {"text": "t", "source": "ai"})
    monkeypatch.setattr(plan_service, "get_todays_adjustment", lambda c: None)
    monkeypatch.setattr(pas, "get_user_adjustment", lambda c, d: None)

    class _P:
        def exists(self):
            return True

        def __str__(self):
            return ":memory:"
    monkeypatch.setattr(routes_plan, "db_path", lambda: _P())
    from flask import Flask
    from src.api import api_bp
    app = Flask(__name__)
    app.register_blueprint(api_bp, url_prefix="/api/v1")
    for state, expect in (("proposed", {"text": "t", "source": "ai"}), ("declined", None)):
        monkeypatch.setattr(pas, "get_day_adjustment", lambda c, d, s=state: {"state": s, "adjustment": {"id": 1}})
        body = app.test_client().get("/api/v1/coach/plan/adjustment").get_json()["data"]
        assert body["adjustment"].get("reason_wording") == expect
    assert len(calls) == 1

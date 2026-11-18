"""지난주 이행 리뷰 — 검증·캐시·API·도구 (V2-AI-CLAUDE-QUEUE E3)."""
import json
import sqlite3
from datetime import date

import pytest
from flask import Flask

from src.ai import provider_claude_queue as pcq
from src.ai.tool_exec_adherence import _exec_get_plan_adherence
from src.db_setup import create_tables, migrate_db
from src.services import adherence_review as AR

WS = date(2026, 11, 9)
INP = {"week": "2026-W46", "sessions": {"done": 3, "total": 4, "pct": 75},
       "volume": {"actual_km": 30.5, "planned_km": 36, "pct": 85},
       "quality": {"done": 1, "total": 2}, "unplanned_runs": 1,
       "days": [{"date": "2026-11-10", "state": "done", "planned_km": 8, "actual_km": 8.2}]}
GOOD = json.dumps({"summary": "계획 4회 중 3회를 달렸어요.",
                   "points": [{"text": "볼륨 85% 달성", "evidence_key": "volume"}],
                   "next_focus": "품질 세션 1회 보강"}, ensure_ascii=False)


def _mut(**kw):
    d = json.loads(GOOD)
    d.update(kw)
    return json.dumps(d, ensure_ascii=False)


@pytest.fixture
def conn(tmp_path):
    c = sqlite3.connect(str(tmp_path / "running.db"))
    create_tables(c)
    migrate_db(c)
    return c


def test_scope_and_last_week():
    assert AR.scope_key(WS) == "2026-W46"
    assert AR.last_week_start(date(2026, 11, 18)) == WS


def test_evidence_keys_and_hash():
    assert "day:2026-11-10" in AR.evidence_keys(INP) and "volume" in AR.evidence_keys(INP)
    assert AR.src_hash(INP) == AR.src_hash(dict(reversed(list(INP.items()))))


@pytest.mark.parametrize("out,ok", [
    (GOOD, True),
    ("앞말 " + GOOD + " 뒷말", True),
    (_mut(summary="9회 중 3회 달렸어요"), False),
    (_mut(points=[{"text": "x", "evidence_key": "nope"}]), False),
    (_mut(summary="가" * 161), False),
    (_mut(summary="**굵게** 3회"), False),
    (_mut(points=[{"text": "a", "evidence_key": "volume"}] * 4), False),
    ("not json", False), (None, False),
])
def test_validate(out, ok):
    assert (AR.validate(INP, out) is not None) is ok


def test_build_input_none_without_goal(conn):
    assert AR.build_input(conn, WS) is None


def test_generate_caches_and_skips_unavailable(conn, monkeypatch):
    monkeypatch.setattr(AR, "build_input", lambda c, w: INP)
    monkeypatch.setattr(pcq, "available", lambda *a: False)
    assert AR.generate(conn, {}, WS) is None
    monkeypatch.setattr(pcq, "available", lambda *a: True)
    calls = []
    monkeypatch.setattr(pcq, "try_complete", lambda *a, **k: calls.append(1) or GOOD)
    assert AR.generate(conn, {}, WS)["next_focus"] == "품질 세션 1회 보강"
    assert AR.generate(conn, {}, WS) is not None and len(calls) == 1  # 해시 일치 → 재호출 없음
    assert AR.review_for_view(conn, WS)["week"] == "2026-W46"


def test_generate_rejects_bad_output(conn, monkeypatch):
    monkeypatch.setattr(AR, "build_input", lambda c, w: INP)
    monkeypatch.setattr(pcq, "available", lambda *a: True)
    monkeypatch.setattr(pcq, "try_complete", lambda *a, **k: "엉망")
    assert AR.generate(conn, {}, WS) is None
    assert AR.review_for_view(conn, WS) is None


def test_tool_without_goal(conn):
    assert _exec_get_plan_adherence(conn, {})["weeks"] == []


def test_route_returns_null_then_review(tmp_path, monkeypatch):
    db_file = tmp_path / "running.db"
    c = sqlite3.connect(str(db_file))
    create_tables(c)
    migrate_db(c)
    c.close()
    import src.api.routes_plan as rp
    import src.utils.user_context as uc
    for mod in (rp, uc):
        monkeypatch.setattr(mod, "db_path", lambda: db_file)
    app = Flask(__name__)
    app.config["TESTING"] = True
    from src.api import api_bp
    app.register_blueprint(api_bp)
    with app.test_client() as cl:
        assert cl.get("/api/v1/coach/plan/adherence-review").get_json()["data"]["review"] is None
        monkeypatch.setattr(AR, "last_week_start", lambda today=None: WS)
        c = sqlite3.connect(str(db_file))
        c.execute("INSERT INTO ai_outputs(kind,scope_key,src_hash,body_json,created_at) VALUES ('adherence','2026-W46','h',?, 'x')", (GOOD,))
        c.commit()
        c.close()
        r = cl.get("/api/v1/coach/plan/adherence-review").get_json()["data"]["review"]
        assert r["summary"].startswith("계획 4회")


def test_all_tools_classified():
    from src.mcp_remote import policy
    assert not policy.unclassified_tools()


def _seed_week(conn):
    cur = conn.execute(
        "INSERT INTO activity_summaries (source, source_id, name, activity_type, start_time,"
        " distance_m, duration_sec, avg_pace_sec_km) VALUES ('garmin','a1','Run','running','2026-11-10T07:00:00',8200,2952,360)")
    pid = conn.execute(
        "INSERT INTO planned_workouts (date, workout_type, distance_km, source, matched_activity_id, completed, goal_id)"
        " VALUES ('2026-11-10','easy',8,'planner',?,0,1)", (cur.lastrowid,)).lastrowid
    conn.execute("INSERT INTO session_outcomes (planned_id, activity_id, date, actual_dist_km) VALUES (?,?,?,8.2)",
                 (pid, cur.lastrowid, "2026-11-10"))
    conn.commit()


def test_build_input_and_tool_with_real_week(conn, monkeypatch):
    from src.services import plan_service
    from src.training import goals
    monkeypatch.setattr(goals, "get_active_goal", lambda c: {"id": 1})
    monkeypatch.setattr(plan_service, "_effective_start", lambda g: date(2026, 11, 2))
    _seed_week(conn)
    inp = AR.build_input(conn, WS)
    assert inp["week"] == "2026-W46" and inp["sessions"]["total"] == 1
    assert any(d["date"] == "2026-11-10" for d in inp["days"])
    out = _exec_get_plan_adherence(conn, {"weeks": 1})
    assert out["fields"][0] == "week" and "sessions" in out

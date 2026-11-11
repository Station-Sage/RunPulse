"""V2-AUDIT-INDIV 묶음 E — 훈련 계획·코치 서버 쪽(P-10·P-12·P-16, C-05·C-11·C-14·C-16)."""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

import pytest
from flask import Flask

from src.db_setup import create_tables, migrate_db
from src.services import adaptation_service, coach_threads, input_limits, plan_service, plan_template_service

H = {"Origin": "http://localhost"}


def _metric(conn, day, name, value):
    conn.execute("INSERT INTO metric_store (scope_type, scope_id, metric_name, provider, numeric_value, is_primary)"
                 " VALUES ('daily', ?, ?, 'runpulse', ?, 1)", (day, name, value))


# ── P-10 ────────────────────────────────────────────────────────────────────

def test_acwr_range_comes_from_metric_definition(db_conn):
    from src.metrics.acwr import ACWRCalculator
    _metric(db_conn, "2026-09-22", "acwr", 1.12)
    out = adaptation_service.get_adaptation_status(db_conn, "2026-09-23")
    assert out["acwr"]["optimal_range"] == ACWRCalculator.ranges["optimal"]
    assert out["acwr"]["zone"] == "적정"


def test_ctl_scale_uses_one_year_peak(db_conn):
    today = date(2026, 11, 10)
    _metric(db_conn, (today - timedelta(days=30)).isoformat(), "ctl", 62.0)
    _metric(db_conn, (today - timedelta(days=400)).isoformat(), "ctl", 90.0)   # 1년 밖 — 무시
    assert plan_service.ctl_scale(db_conn, 40.0, today) == {"max": 62.0, "label": "최근 1년 최고"}
    assert plan_service.ctl_scale(db_conn, 70.0, today)["max"] == 70.0      # 현재값이 더 크면 현재값
    empty = sqlite3.connect(":memory:")
    create_tables(empty)
    migrate_db(empty)
    assert plan_service.ctl_scale(empty, None, today) is None


# ── P-12 ────────────────────────────────────────────────────────────────────

def test_finish_goal_templates_skip_achievability(db_conn):
    _metric(db_conn, date.today().isoformat(), "race_pred_vdot", 45.0)
    for t in plan_template_service.get_static_plan_templates(db_conn, 42.195, None):
        assert t["achievability_pct"] is None
        assert "이미 목표 수준" not in t["status_summary"]
        assert t["projected_time_end"] is not None


def test_finish_goal_summary_mentions_short_period():
    rec = {"optimal_min": 12, "optimal_max": 16}
    assert "짧아요" in plan_template_service.finish_goal_summary(8, rec)
    assert "짧아요" not in plan_template_service.finish_goal_summary(14, rec)


def test_target_pace_error():
    assert input_limits.target_pace_error(42.195, 1) is not None
    assert input_limits.target_pace_error(5, 5 * 119) is not None
    assert input_limits.target_pace_error(42.195, 3 * 3600) is None
    assert input_limits.target_pace_error(42.195, None) is None


@pytest.fixture
def app(tmp_path):
    db_file = tmp_path / "running.db"
    conn = sqlite3.connect(str(db_file))
    create_tables(conn)
    migrate_db(conn)
    conn.close()
    import src.api.routes_coach as rc
    import src.api.routes_plan as rp
    orig = rc.db_path, rp.db_path
    rc.db_path = rp.db_path = lambda: db_file
    flask_app = Flask(__name__)
    flask_app.config["TESTING"] = True
    from src.api import api_bp
    flask_app.register_blueprint(api_bp)
    with flask_app.test_client() as client:
        yield client, db_file
    rc.db_path, rp.db_path = orig


def test_templates_and_create_reject_impossible_target(app):
    client, _ = app
    res = client.get("/api/v1/coach/plan/templates?distance_km=42.195&target_time_sec=1")
    assert res.status_code == 400 and "너무 빨라요" in res.get_json()["error"]["message"]
    res = client.post("/api/v1/coach/plan", json={"distance_km": 10, "weeks": 8, "run_weekdays": [0, 2, 4],
                                                  "target_time_sec": 60}, headers=H)
    assert res.status_code == 400 and res.get_json()["error"]["details"]["target_time_sec"]


# ── P-16 ────────────────────────────────────────────────────────────────────

def test_save_empty_session_note_deletes(db_conn):
    plan_service.save_session_note(db_conn, "2026-11-10", "메모")
    plan_service.save_session_note(db_conn, "2026-11-10", "   ")
    n = db_conn.execute("SELECT COUNT(*) FROM user_inputs WHERE input_type='session_note'").fetchone()[0]
    assert n == 0


# ── C-11 ────────────────────────────────────────────────────────────────────

def test_derive_title_strips_markdown_and_spaces():
    assert coach_threads.derive_title("**굵게**  그리고\n\n`코드`") == "굵게 그리고 코드"
    assert coach_threads.derive_title('<img src=x onerror="a"> [링크](http://x) 안녕') == "링크 안녕"
    long = "오늘 훈련 강도가 적당했는지 그리고 내일은 어떻게 해야 하는지 궁금해요"
    t = coach_threads.derive_title(long)
    assert t.endswith("…") and len(t) <= coach_threads.TITLE_MAX_LEN + 1 and not t[:-1].endswith(" ")
    assert coach_threads.derive_title("**") == "**"   # 걷어 내고 빈 문자열이면 원문


def test_coach_service_reexports_title():
    from src.services import coach_service
    assert coach_service._derive_title("a\nb") == "a b"


# ── C-05·C-16 ───────────────────────────────────────────────────────────────

def _threads(conn, n, same_time=True):
    for i in range(n):
        conn.execute("INSERT INTO chat_threads (title, updated_at) VALUES (?, ?)",
                     (f"t{i}", "2026-11-10 10:00:00" if same_time else f"2026-11-{i % 28 + 1:02d} 10:00:00"))
    conn.commit()


def test_list_threads_tie_breaks_by_id(db_conn):
    _threads(db_conn, 3)
    ids = [t["id"] for t in coach_threads.list_threads(db_conn)]
    assert ids == sorted(ids, reverse=True)


def test_list_threads_page_has_more(db_conn):
    _threads(db_conn, 35)
    first = coach_threads.list_threads_page(db_conn)
    assert len(first["threads"]) == 30 and first["has_more"] and first["next_offset"] == 30
    second = coach_threads.list_threads_page(db_conn, offset=first["next_offset"])
    assert len(second["threads"]) == 5 and not second["has_more"]
    assert not {t["id"] for t in first["threads"]} & {t["id"] for t in second["threads"]}


def test_threads_route_paging_and_validation(app):
    client, db_file = app
    conn = sqlite3.connect(str(db_file))
    _threads(conn, 32)
    conn.close()
    data = client.get("/api/v1/coach/threads").get_json()["data"]
    assert len(data["threads"]) == 30 and data["has_more"] is True
    data = client.get("/api/v1/coach/threads?offset=30").get_json()["data"]
    assert len(data["threads"]) == 2 and data["has_more"] is False
    assert client.get("/api/v1/coach/threads?limit=0").status_code == 400
    assert client.get("/api/v1/coach/threads?offset=abc").status_code == 400


# ── C-14 ────────────────────────────────────────────────────────────────────

def test_unexpected_exception_is_not_network():
    import httpx
    from src.ai.provider_common import REASON_LABELS, wrap_transport_error
    assert wrap_transport_error(httpx.ConnectError("x")).reason == "network"
    assert wrap_transport_error(httpx.ReadTimeout("x")).reason == "timeout"
    assert wrap_transport_error(RuntimeError("blocked")).reason == "unexpected"
    assert REASON_LABELS["unexpected"] == "예기치 못한 오류"


def test_run_chain_marks_unexpected(monkeypatch, db_conn):
    from src.ai import chat_engine_result as cer

    def boom(*a, **k):
        raise RuntimeError("x")
    monkeypatch.setattr(cer, "complete", boom)
    text, prov, attempts = cer.run_chain(db_conn, "q", {}, ["gemini"], tools=False)
    assert text is None and attempts[0].reason == "unexpected"

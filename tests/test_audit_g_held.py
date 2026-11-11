"""V2-AUDIT-INDIV 묶음 G — 보류 항목 추천안 반영(P-14 롱런 요일, D-21 확장, A-36 스트림 다운샘플, D-32 표기)."""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

import pytest
from flask import Flask

from src.db_setup import create_tables, migrate_db
from src.services import plan_template_service
from src.services.stream_downsample import downsample_streams, parse_max_points
from src.training.planner_config import resolve_long_run_weekday
from src.training.planner_store import set_long_run_weekday
from tests.helpers_pred import mem_conn, seed_run, with_days

H = {"Origin": "http://localhost"}


# ── P-14 롱런 요일 ───────────────────────────────────────────────────────────

def _seeded():
    c = with_days(mem_conn())
    end = date.today() - timedelta(days=1)
    for w in range(8):
        for i, d in enumerate((0, 2, 4, 6)):
            dist = 40.0 * (0.4 if d == 6 else 0.2) * 1000
            seed_run(c, sid=f"{w}-{i}", date=(end - timedelta(weeks=w, days=d)).isoformat(),
                     dist=dist, moving=int(dist / 3.0))
    return c


def _long_weekdays(c) -> set[int]:
    rows = c.execute("SELECT date FROM planned_workouts WHERE source='planner'"
                     " AND workout_type IN ('long','long_mp')").fetchall()
    return {date.fromisoformat(r[0]).weekday() for r in rows}


def test_resolve_and_store_long_run_weekday(db_conn):
    assert resolve_long_run_weekday({}) is None
    assert resolve_long_run_weekday({"long_run_weekday_mask": 1 << 3}) == 3
    assert set_long_run_weekday(db_conn, 6) == 1 << 6
    assert set_long_run_weekday(db_conn, None) == 0
    with pytest.raises(ValueError):
        set_long_run_weekday(db_conn, 7)


def test_plan_puts_long_run_on_preferred_weekday():
    c = _seeded()
    plan_template_service.create_plan_from_template(c, 21.097, None, 6, name="h", run_weekdays=[1, 3, 5, 6],
                                                    long_run_weekday=3)
    assert _long_weekdays(c) == {3}


def test_plan_without_preference_keeps_weekend_default():
    c = _seeded()
    plan_template_service.create_plan_from_template(c, 21.097, None, 6, name="h", run_weekdays=[1, 3, 5, 6])
    assert _long_weekdays(c) == {6}


def test_long_run_weekday_must_be_run_day():
    c = _seeded()
    from src.training.planner_store import WeekdaysRequired
    with pytest.raises(WeekdaysRequired):
        plan_template_service.create_plan_from_template(c, 10, None, 4, run_weekdays=[1, 3], long_run_weekday=6)


# ── 라우트(D-21 확장·P-14·A-36) ─────────────────────────────────────────────

@pytest.fixture
def client(tmp_path, monkeypatch):
    db_file = tmp_path / "running.db"
    conn = sqlite3.connect(str(db_file))
    create_tables(conn)
    migrate_db(conn)
    conn.execute("INSERT INTO activity_summaries (source, source_id, activity_type, start_time, distance_m,"
                 " duration_sec) VALUES ('garmin','s1','running','2026-04-01T08:00:00Z',10000,3600)")
    aid = conn.execute("SELECT id FROM activity_summaries").fetchone()[0]
    conn.executemany("INSERT INTO activity_streams (activity_id, source, elapsed_sec, heart_rate) VALUES (?,?,?,?)",
                     [(aid, "garmin", t, 120 + t % 30) for t in range(1000)])
    conn.commit()
    conn.close()
    import src.api.routes_coach as rc
    import src.api.routes_library_streams as rls
    import src.api.routes_plan as rp
    import src.api.routes_plan_adjust as rpa
    import src.api.routes_prediction as rpred
    for m in (rc, rls, rp, rpa, rpred):
        monkeypatch.setattr(m, "db_path", lambda: db_file)
    app = Flask(__name__)
    app.config["TESTING"] = True
    from src.api import api_bp
    app.register_blueprint(api_bp)
    with app.test_client() as c:
        yield c, aid


@pytest.mark.parametrize("method,path", [
    ("post", "/api/v1/coach/plan/session/2026-11-12/note"),
    ("post", "/api/v1/coach/plan/1/restore"),
    ("post", "/api/v1/coach/plan/adjustments/1/accept"),
    ("post", "/api/v1/coach/plan/workouts/1/action"),
    ("post", "/api/v1/coach/plan/replan"),
    ("post", "/api/v1/coach/messages/1/regenerate"),
    ("put", "/api/v1/coach/consent"),
    ("put", "/api/v1/races/1/confirm"),
])
def test_non_object_json_body_is_400(client, method, path):
    c, _ = client
    for raw in ("[1]", "{broken"):
        res = getattr(c, method)(path, data=raw, content_type="application/json", headers=H)
        assert res.status_code == 400, (path, raw, res.status_code)
        assert res.get_json()["error"]["code"] == "INVALID_PARAM"


def test_create_plan_rejects_long_run_outside_run_days(client):
    c, _ = client
    res = c.post("/api/v1/coach/plan", json={"distance_km": 10, "weeks": 4, "run_weekdays": [1, 3],
                                             "long_run_weekday": 6}, headers=H)
    assert res.status_code == 400
    assert "long_run_weekday" in res.get_json()["error"]["details"]


def test_parse_max_points():
    assert parse_max_points(None) is None and parse_max_points("") is None
    assert parse_max_points("500") == 500
    for bad in ("abc", "-5", "10", "999999"):
        with pytest.raises(ValueError):
            parse_max_points(bad)


def test_downsample_keeps_ends_and_order_per_source():
    rows = [{"source": s, "elapsed_sec": t} for t in range(1000) for s in ("garmin", "strava")]
    out, info = downsample_streams(rows, 200)
    assert info == {"from": 2000, "to": len(out)} and len(out) <= 202
    for s in ("garmin", "strava"):
        ts = [r["elapsed_sec"] for r in out if r["source"] == s]
        assert ts[0] == 0 and ts[-1] == 999 and ts == sorted(ts)
    assert downsample_streams(rows, None) == (rows, None)


def test_streams_route_max_points(client):
    c, aid = client
    full = c.get(f"/api/v1/library/activities/{aid}/streams").get_json()["data"]
    assert len(full["streams"]) == 1000 and "downsampled" not in full
    small = c.get(f"/api/v1/library/activities/{aid}/streams?max_points=100").get_json()["data"]
    assert len(small["streams"]) == 100 and small["downsampled"] == {"from": 1000, "to": 100}
    assert c.get(f"/api/v1/library/activities/{aid}/streams?max_points=x").status_code == 400


# ── D-32 소스 이름 표기 ──────────────────────────────────────────────────────

def test_intervals_display_name_is_intervals_icu():
    from src.services import data_connect_service, metrics_version_events, provider_matrix_collect
    assert data_connect_service._NAMES["intervals"] == "Intervals.icu"
    assert metrics_version_events._PROV["intervals"] == "Intervals.icu"
    assert provider_matrix_collect.PROVIDER_LABELS["intervals"] == "Intervals.icu"


# ── C-17 폴백 opt-in ─────────────────────────────────────────────────────────

def test_consent_defaults_are_opt_in(db_conn):
    from src.services import coach_consent
    c = coach_consent.save_consent(db_conn, "gemini")
    assert c["fallback_enabled"] is False and c["exclude_notes"] is True


def test_consent_route_defaults_opt_in(client):
    c, _ = client
    data = c.put("/api/v1/coach/consent", json={"provider": "gemini"}, headers=H).get_json()["data"]
    assert data["consent"]["fallback_enabled"] is False and data["consent"]["exclude_notes"] is True


def test_engine_lists_fallback_providers_before_consent(db_conn):
    from src.services import coach_engine_health
    cfg = {"ai": {"provider": "gemini", "gemini_api_key": "k", "groq_api_key": "k"}}
    out = coach_engine_health.get_engine(db_conn, cfg)
    assert out["chain"] == []  # 동의 전 호출 0회 그대로
    assert out["fallback_providers"] == [{"provider": "groq", "label": "Groq"}]


# ── C-13 규칙 답변 표기 ──────────────────────────────────────────────────────

def test_rule_engine_labels_share_one_format():
    from src.services.coach_engine_health import engine_label
    labels = [engine_label(s, "rule", None, 0, None) for s in ("fallback", "rule_only", "rule_by_choice", "legacy_rule")]
    assert all(lb.startswith("규칙 답변 (") for lb in labels), labels

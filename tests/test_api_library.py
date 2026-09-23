"""tests/test_api_library.py — GET /api/v1/library/activities(+:id, +:id/streams, /metrics/:slug) 테스트."""
from __future__ import annotations

import sqlite3

import pytest
from flask import Flask

from src.db_setup import create_tables, migrate_db
from src.metrics.engine import run_activity_metrics, run_daily_metrics


@pytest.fixture
def mini_app(tmp_path):
    db_file = tmp_path / "running.db"
    conn = sqlite3.connect(str(db_file))
    create_tables(conn)
    migrate_db(conn)
    conn.executemany(
        "INSERT INTO activity_summaries"
        " (source, source_id, name, activity_type, start_time, distance_m, duration_sec)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            ("garmin", "g1", "아침 러닝", "running", "2026-04-01T08:00:00Z", 10_000, 3600),
            ("garmin", "g2", "자전거", "cycling", "2026-04-02T08:00:00Z", 20_000, 3600),
        ],
    )
    conn.commit()
    act_id = conn.execute("SELECT id FROM activity_summaries WHERE source_id='g1'").fetchone()[0]
    conn.execute(
        "INSERT INTO activity_streams (activity_id, source, elapsed_sec, heart_rate)"
        " VALUES (?, 'garmin', 0, 120)",
        (act_id,),
    )
    conn.commit()
    conn.close()

    import src.api.routes_library as routes_library
    _orig_route = routes_library.db_path
    routes_library.db_path = lambda: db_file

    app = Flask(__name__)
    app.config["TESTING"] = True
    from src.api import api_bp
    app.register_blueprint(api_bp)

    with app.test_client() as client:
        yield client, act_id

    routes_library.db_path = _orig_route


def test_list_activities_default(mini_app):
    client, _ = mini_app
    res = client.get("/api/v1/library/activities")
    assert res.status_code == 200
    body = res.get_json()
    assert body["data"]["total"] == 2
    assert len(body["data"]["activities"]) == 2
    assert body["meta"]["page"] == 1


def test_list_activities_sport_filter(mini_app):
    client, _ = mini_app
    res = client.get("/api/v1/library/activities?sport=running")
    body = res.get_json()
    assert body["data"]["total"] == 1
    assert body["data"]["activities"][0]["activity_type"] == "running"


def test_get_activity_detail(mini_app):
    client, act_id = mini_app
    res = client.get(f"/api/v1/library/activities/{act_id}")
    assert res.status_code == 200
    body = res.get_json()
    assert body["data"]["activity"]["core"]["name"] == "아침 러닝"


def test_get_activity_detail_not_found(mini_app):
    client, _ = mini_app
    res = client.get("/api/v1/library/activities/9999")
    assert res.status_code == 404
    body = res.get_json()
    assert body["error"]["code"] == "NOT_FOUND"


def test_get_activity_streams(mini_app):
    client, act_id = mini_app
    res = client.get(f"/api/v1/library/activities/{act_id}/streams")
    assert res.status_code == 200
    body = res.get_json()
    assert len(body["data"]["streams"]) == 1
    assert body["data"]["streams"][0]["heart_rate"] == 120


# ── /library/metrics/:slug 라우트 테스트 ─────────────────────────────────────

@pytest.fixture
def metric_app(tmp_path):
    """ctl 메트릭이 계산된 상태의 앱 픽스처."""
    db_file = tmp_path / "running.db"
    conn = sqlite3.connect(str(db_file))
    create_tables(conn)
    migrate_db(conn)
    conn.execute(
        "INSERT INTO activity_summaries "
        "(source, source_id, name, activity_type, start_time, "
        "distance_m, moving_time_sec, avg_hr, max_hr, avg_speed_ms) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        ["garmin", "1", "Morning Run", "running", "2026-04-01 08:00:00",
         10000, 3000, 155, 185, 3.33],
    )
    conn.execute(
        "INSERT INTO daily_wellness (date, resting_hr, body_battery_high, sleep_score) "
        "VALUES (?, ?, ?, ?)", ["2026-04-01", 52, 80, 85],
    )
    conn.commit()
    act_id = conn.execute("SELECT id FROM activity_summaries WHERE source_id='1'").fetchone()[0]
    run_activity_metrics(conn, act_id)
    conn.commit()
    run_daily_metrics(conn, "2026-04-01")
    conn.commit()
    conn.close()

    import src.api.routes_library as routes_library
    _orig = routes_library.db_path
    routes_library.db_path = lambda: db_file

    app = Flask(__name__)
    app.config["TESTING"] = True
    from src.api import api_bp
    app.register_blueprint(api_bp)

    with app.test_client() as client:
        yield client

    routes_library.db_path = _orig


def test_get_metric_breakdown_200(metric_app):
    res = metric_app.get("/api/v1/library/metrics/ctl?scope_type=daily&scope_id=2026-04-01")
    assert res.status_code == 200
    body = res.get_json()
    assert "metric" in body["data"]
    metric = body["data"]["metric"]
    assert metric["slug"] == "ctl"
    assert metric["value"] is not None
    assert "children" in metric
    assert "inputs" in metric


def test_get_metric_breakdown_404(metric_app):
    res = metric_app.get("/api/v1/library/metrics/nonexistent?scope_type=daily&scope_id=2026-04-01")
    assert res.status_code == 404
    body = res.get_json()
    assert body["error"]["code"] == "NOT_FOUND"


def test_get_metric_breakdown_missing_scope_id(metric_app):
    res = metric_app.get("/api/v1/library/metrics/ctl?scope_type=daily")
    assert res.status_code == 400
    body = res.get_json()
    assert body["error"]["code"] == "INVALID_PARAM"


def test_get_metric_breakdown_default_scope_type(metric_app):
    """scope_type 생략 시 기본값 'daily' 적용."""
    res = metric_app.get("/api/v1/library/metrics/ctl?scope_id=2026-04-01")
    assert res.status_code == 200
    body = res.get_json()
    assert body["data"]["metric"]["slug"] == "ctl"


# ── /library/activities/:id/providers 라우트 테스트 ──────────────────────────

def test_get_activity_providers_200(mini_app):
    """단독 활동(그룹 없음) → 200, state='single_provider'."""
    client, act_id = mini_app
    res = client.get(f"/api/v1/library/activities/{act_id}/providers")
    assert res.status_code == 200
    body = res.get_json()
    comparison = body["data"]["comparison"]
    assert comparison["state"] in ("single_provider", "loaded")
    assert comparison["activity_id"] == act_id
    assert "rows" in comparison


def test_get_activity_providers_404(mini_app):
    """존재하지 않는 활동 → 404, NOT_FOUND."""
    client, _ = mini_app
    res = client.get("/api/v1/library/activities/9999/providers")
    assert res.status_code == 404
    body = res.get_json()
    assert body["error"]["code"] == "NOT_FOUND"


# ── /library/metrics 브라우저 라우트 테스트 ─────────────────────────────────

def test_get_metrics_browser_200(metric_app):
    """GET /library/metrics → 200, categories 포함."""
    res = metric_app.get("/api/v1/library/metrics?date=2026-04-01")
    assert res.status_code == 200
    body = res.get_json()
    data = body["data"]
    assert "date" in data
    assert "categories" in data
    assert isinstance(data["categories"], list)
    assert len(data["categories"]) > 0


def test_get_metrics_browser_no_date(metric_app):
    """date 없이 호출 → 자동 최신 날짜 사용."""
    res = metric_app.get("/api/v1/library/metrics")
    assert res.status_code == 200
    body = res.get_json()
    assert "date" in body["data"]


# ── /library/metrics/:slug/trend 라우트 테스트 ──────────────────────────────

def test_get_metric_trend_200(metric_app):
    """GET /library/metrics/ctl/trend → 200, points 포함."""
    res = metric_app.get("/api/v1/library/metrics/ctl/trend?period=1y")
    assert res.status_code == 200
    body = res.get_json()
    data = body["data"]
    assert data["slug"] == "ctl"
    assert "points" in data
    assert "current" in data
    assert "peak" in data


def test_get_metric_trend_404(metric_app):
    """존재하지 않는 메트릭 → 404, NOT_FOUND."""
    res = metric_app.get("/api/v1/library/metrics/nonexistent_xyz/trend")
    assert res.status_code == 404
    body = res.get_json()
    assert body["error"]["code"] == "NOT_FOUND"

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


def test_list_activities_search_filter(mini_app):
    client, _ = mini_app
    res = client.get("/api/v1/library/activities?search=아침")
    body = res.get_json()
    assert body["data"]["total"] == 1
    assert "아침" in body["data"]["activities"][0]["name"]


def test_list_activities_dist_min_filter(mini_app):
    client, _ = mini_app
    # dist_min=15km → 15000m: 아침 러닝(10km) 제외, 자전거(20km) 포함
    res = client.get("/api/v1/library/activities?dist_min=15")
    body = res.get_json()
    assert body["data"]["total"] == 1
    assert body["data"]["activities"][0]["activity_type"] == "cycling"


def test_list_activities_dist_min_invalid(mini_app):
    client, _ = mini_app
    res = client.get("/api/v1/library/activities?dist_min=abc")
    assert res.status_code == 400
    body = res.get_json()
    assert body["error"]["code"] == "INVALID_PARAM"


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
    assert body["data"]["time_basis"] == "unknown"


def test_get_activity_streams_returns_meta(mini_app, tmp_path):
    client, act_id = mini_app
    import sqlite3 as _s, src.api.routes_library as rl
    c = _s.connect(str(rl.db_path()))
    c.execute("INSERT INTO activity_stream_meta (activity_id, source, time_basis, time_key, sample_count,"
              " stored_count, median_dt_sec) VALUES (?, 'garmin', 'measured', 'sumElapsedDuration', 1, 1, 2.0)",
              (act_id,))
    c.commit(); c.close()
    data = client.get(f"/api/v1/library/activities/{act_id}/streams").get_json()["data"]
    assert data["time_basis"] == "measured" and data["median_dt_sec"] == 2.0


def test_get_activity_detail_etag_304_on_revalidate(mini_app):
    """무거운 페이로드(활동 상세) 재요청 시 ETag가 같으면 본문 없이 304(02-performance.md, 사용자 증가 대비 캐싱)."""
    client, act_id = mini_app
    first = client.get(f"/api/v1/library/activities/{act_id}")
    assert first.status_code == 200
    etag = first.headers.get("ETag")
    assert etag

    second = client.get(
        f"/api/v1/library/activities/{act_id}", headers={"If-None-Match": etag}
    )
    assert second.status_code == 304
    assert second.get_data() == b""


def test_get_activity_streams_etag_304_on_revalidate(mini_app):
    client, act_id = mini_app
    first = client.get(f"/api/v1/library/activities/{act_id}/streams")
    etag = first.headers.get("ETag")
    assert etag

    second = client.get(
        f"/api/v1/library/activities/{act_id}/streams", headers={"If-None-Match": etag}
    )
    assert second.status_code == 304


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
    assert body["data"]["compare_group"]["key"] == "ctl"


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
    assert data["compare_group"]["key"] == "ctl"


def test_get_metric_trend_404(metric_app):
    """존재하지 않는 메트릭 → 404, NOT_FOUND."""
    res = metric_app.get("/api/v1/library/metrics/nonexistent_xyz/trend")
    assert res.status_code == 404
    body = res.get_json()
    assert body["error"]["code"] == "NOT_FOUND"


# ── /library/wellness 라우트 테스트 ─────────────────────────────────────────

def test_get_wellness_200(metric_app):
    """GET /library/wellness?date=2026-04-01 → 200, 필수 키 포함."""
    res = metric_app.get("/api/v1/library/wellness?date=2026-04-01")
    assert res.status_code == 200
    body = res.get_json()
    data = body["data"]
    assert data["date"] == "2026-04-01"
    assert "core" in data
    assert "metrics_by_category" in data
    assert "readiness_summary" in data
    assert data["core"]["sleep_score"] == 85


def test_get_wellness_no_date(metric_app):
    """date 없이 호출 → 200, date 키 포함."""
    res = metric_app.get("/api/v1/library/wellness")
    assert res.status_code == 200
    body = res.get_json()
    assert "date" in body["data"]


def test_get_wellness_bad_date_400(metric_app):
    """date 형식 오류 → 400 INVALID_PARAM."""
    res = metric_app.get("/api/v1/library/wellness?date=2026-13-45")
    assert res.status_code == 400
    assert res.get_json()["error"]["code"] == "INVALID_PARAM"


def test_get_wellness_future_date_clamped_to_today(metric_app):
    """미래 날짜 → 오늘로 대체(has_record 키 포함)."""
    res = metric_app.get("/api/v1/library/wellness?date=2999-01-01")
    data = res.get_json()["data"]
    assert res.status_code == 200 and data["date"] != "2999-01-01" and "has_record" in data


def test_get_wellness_trend_bad_end_400(metric_app):
    res = metric_app.get("/api/v1/library/wellness/trend?end=nope")
    assert res.status_code == 400


def test_get_wellness_trend_200(metric_app):
    """GET /library/wellness/trend → 200, 필수 시계열 키 포함."""
    res = metric_app.get("/api/v1/library/wellness/trend?days=30")
    assert res.status_code == 200
    body = res.get_json()
    data = body["data"]
    assert "dates" in data
    assert "sleep_score" in data
    assert "hrv_last_night" in data
    assert "utrs" in data


def test_get_wellness_trend_invalid_days(metric_app):
    """days 파라미터가 정수가 아닌 경우 → 400, INVALID_PARAM."""
    res = metric_app.get("/api/v1/library/wellness/trend?days=abc")
    assert res.status_code == 400
    body = res.get_json()
    assert body["error"]["code"] == "INVALID_PARAM"


# ── /library/providers/matrix 라우트 테스트 ─────────────────────────────────

def test_get_providers_matrix_200(mini_app):
    """GET /library/providers/matrix → 200, S6 응답 구조."""
    client, _ = mini_app
    res = client.get("/api/v1/library/providers/matrix")
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["days"] == 28 and data["sport"] == "running"
    assert "state" in data and isinstance(data["sections"], list)


def test_get_providers_matrix_invalid_days(mini_app):
    """days가 28/56/84가 아니면 400."""
    client, _ = mini_app
    for q in ("abc", "90"):
        res = client.get(f"/api/v1/library/providers/matrix?days={q}")
        assert res.status_code == 400
        assert res.get_json()["error"]["code"] == "INVALID_PARAM"


def test_get_providers_pairs_route(mini_app):
    """pairs: 알 수 없는 그룹 404, 정의 행은 not_comparable."""
    client, _ = mini_app
    assert client.get("/api/v1/library/providers/pairs/nope").status_code == 404
    res = client.get("/api/v1/library/providers/pairs/vo2max_vdot")
    assert res.status_code == 200 and res.get_json()["data"]["state"] == "not_comparable"
    assert client.get("/api/v1/library/providers/pairs/ctl?days=7").status_code == 400


# ── /library/providers/coverage 라우트 테스트 ────────────────────────────────

def test_get_providers_coverage_200(mini_app):
    """GET /library/providers/coverage → 200, providers 4개 포함."""
    client, _ = mini_app
    res = client.get("/api/v1/library/providers/coverage")
    assert res.status_code == 200
    body = res.get_json()
    data = body["data"]
    assert "months" in data
    assert "providers" in data
    assert len(data["providers"]) == 4


def test_get_activity_detail_streams_opt_in(mini_app):
    """streams는 기본 응답에서 빠지고 ?include=streams 일 때만 내려온다."""
    client, act_id = mini_app
    base = client.get(f"/api/v1/library/activities/{act_id}").get_json()["data"]["activity"]
    assert base["streams"] is None
    full = client.get(f"/api/v1/library/activities/{act_id}?include=streams").get_json()["data"]["activity"]
    assert len(full["streams"]) == 1

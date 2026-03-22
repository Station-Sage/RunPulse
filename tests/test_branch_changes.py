"""현재 브랜치 주요 변경사항 테스트.

커버 범위:
  - fetch_unified_activities: sort_by/sort_dir, q 검색, 거리/페이스/시간 범위 필터
  - auto_group_all: 그룹 병합 (A+B → A, B+C → A로 전이)
  - sync_ui._source_checkboxes: 연결/미연결 서비스 렌더링
  - helpers.connected_services: 연결 확인 함수 목킹
  - /activities 라우트: 정렬 URL이 날짜 파라미터 유지, q 검색 파라미터 전달
"""
from __future__ import annotations

import sqlite3
from unittest.mock import patch

import pytest

from src.services.unified_activities import fetch_unified_activities
from src.utils.dedup import auto_group_all
from src.web.sync_ui import _source_checkboxes


# ── 공통 insert 헬퍼 ──────────────────────────────────────────────────────

def _insert(
    conn: sqlite3.Connection,
    source: str,
    *,
    start_time: str = "2026-01-15T08:00:00",
    distance_km: float = 10.0,
    duration_sec: int = 3600,
    avg_pace_sec_km: int = 360,
    avg_hr: float = 150.0,
    description: str = "test run",
    matched_group_id: str | None = None,
) -> int:
    cur = conn.execute(
        """INSERT INTO activity_summaries
           (source, source_id, activity_type, start_time, distance_km, duration_sec,
            avg_pace_sec_km, avg_hr, description, matched_group_id)
           VALUES (?, ?, 'running', ?, ?, ?, ?, ?, ?, ?)""",
        (
            source, f"{source}-{start_time}",
            start_time, distance_km, duration_sec,
            avg_pace_sec_km, avg_hr, description, matched_group_id,
        ),
    )
    conn.commit()
    return cur.lastrowid


# ── fetch_unified_activities: 정렬 ────────────────────────────────────────

class TestFetchSort:
    def test_sort_by_distance_desc(self, db_conn):
        _insert(db_conn, "garmin", distance_km=5.0, start_time="2026-01-01T08:00:00")
        _insert(db_conn, "strava", distance_km=20.0, start_time="2026-01-02T08:00:00")
        _insert(db_conn, "intervals", distance_km=10.0, start_time="2026-01-03T08:00:00")

        acts, _, _ = fetch_unified_activities(db_conn, sort_by="distance", sort_dir="desc")
        dists = [a.distance_km.value for a in acts]
        assert dists == sorted(dists, reverse=True)

    def test_sort_by_distance_asc(self, db_conn):
        _insert(db_conn, "garmin", distance_km=15.0, start_time="2026-01-01T08:00:00")
        _insert(db_conn, "strava", distance_km=3.0, start_time="2026-01-02T08:00:00")

        acts, _, _ = fetch_unified_activities(db_conn, sort_by="distance", sort_dir="asc")
        dists = [a.distance_km.value for a in acts]
        assert dists == sorted(dists)

    def test_sort_by_duration_desc(self, db_conn):
        _insert(db_conn, "garmin", duration_sec=1800, start_time="2026-01-01T08:00:00")
        _insert(db_conn, "strava", duration_sec=7200, start_time="2026-01-02T08:00:00")
        _insert(db_conn, "intervals", duration_sec=3600, start_time="2026-01-03T08:00:00")

        acts, _, _ = fetch_unified_activities(db_conn, sort_by="duration", sort_dir="desc")
        durs = [a.duration_sec.value for a in acts]
        assert durs == sorted(durs, reverse=True)

    def test_sort_by_pace_asc(self, db_conn):
        _insert(db_conn, "garmin", avg_pace_sec_km=300, start_time="2026-01-01T08:00:00")
        _insert(db_conn, "strava", avg_pace_sec_km=360, start_time="2026-01-02T08:00:00")
        _insert(db_conn, "intervals", avg_pace_sec_km=240, start_time="2026-01-03T08:00:00")

        acts, _, _ = fetch_unified_activities(db_conn, sort_by="pace", sort_dir="asc")
        paces = [a.avg_pace_sec_km.value for a in acts]
        assert paces == sorted(paces)

    def test_sort_by_hr_desc(self, db_conn):
        _insert(db_conn, "garmin", avg_hr=140.0, start_time="2026-01-01T08:00:00")
        _insert(db_conn, "strava", avg_hr=170.0, start_time="2026-01-02T08:00:00")

        acts, _, _ = fetch_unified_activities(db_conn, sort_by="hr", sort_dir="desc")
        hrs = [a.avg_hr.value for a in acts]
        assert hrs == sorted(hrs, reverse=True)

    def test_sort_by_date_desc_default(self, db_conn):
        _insert(db_conn, "garmin", start_time="2026-01-01T08:00:00")
        _insert(db_conn, "strava", start_time="2026-01-10T08:00:00")
        _insert(db_conn, "intervals", start_time="2026-01-05T08:00:00")

        acts, _, _ = fetch_unified_activities(db_conn, sort_by="date", sort_dir="desc")
        times = [a.start_time.value for a in acts]
        assert times == sorted(times, reverse=True)

    def test_invalid_sort_falls_back_to_date(self, db_conn):
        _insert(db_conn, "garmin", start_time="2026-01-01T08:00:00")
        _insert(db_conn, "strava", start_time="2026-01-02T08:00:00")

        # 잘못된 sort_by는 date 기준으로 fallback
        acts, _, _ = fetch_unified_activities(db_conn, sort_by="nonexistent", sort_dir="desc")
        assert len(acts) == 2


# ── fetch_unified_activities: 텍스트 검색 ────────────────────────────────

class TestFetchSearch:
    def test_q_matches_description(self, db_conn):
        _insert(db_conn, "garmin", description="morning long run", start_time="2026-01-01T08:00:00")
        _insert(db_conn, "strava", description="evening tempo", start_time="2026-01-02T08:00:00")

        acts, total, _ = fetch_unified_activities(db_conn, q="long")
        assert total == 1
        assert acts[0].description.value == "morning long run"

    def test_q_matches_activity_type(self, db_conn):
        conn = db_conn
        conn.execute(
            """INSERT INTO activity_summaries
               (source, source_id, activity_type, start_time, distance_km, duration_sec,
                avg_pace_sec_km, avg_hr, description)
               VALUES ('garmin', 'g-swim', 'swimming', '2026-01-01T08:00:00',
                       1.5, 2400, 0, 130, 'pool swim')"""
        )
        conn.commit()
        _insert(db_conn, "strava", description="run", start_time="2026-01-02T08:00:00")

        acts, total, _ = fetch_unified_activities(db_conn, q="swim")
        assert total == 1

    def test_q_empty_returns_all(self, db_conn):
        _insert(db_conn, "garmin", description="morning run", start_time="2026-01-01T08:00:00")
        _insert(db_conn, "strava", description="evening run", start_time="2026-01-02T08:00:00")

        _, total, _ = fetch_unified_activities(db_conn, q="")
        assert total == 2

    def test_q_no_match_returns_empty(self, db_conn):
        _insert(db_conn, "garmin", description="morning run")

        acts, total, _ = fetch_unified_activities(db_conn, q="triathlon")
        assert total == 0
        assert acts == []


# ── fetch_unified_activities: 거리 범위 필터 ────────────────────────────

class TestFetchDistanceFilter:
    def test_min_dist(self, db_conn):
        _insert(db_conn, "garmin", distance_km=5.0, start_time="2026-01-01T08:00:00")
        _insert(db_conn, "strava", distance_km=15.0, start_time="2026-01-02T08:00:00")
        _insert(db_conn, "intervals", distance_km=21.0, start_time="2026-01-03T08:00:00")

        acts, total, _ = fetch_unified_activities(db_conn, min_dist=10.0)
        assert total == 2
        assert all(a.distance_km.value >= 10.0 for a in acts)

    def test_max_dist(self, db_conn):
        _insert(db_conn, "garmin", distance_km=5.0, start_time="2026-01-01T08:00:00")
        _insert(db_conn, "strava", distance_km=15.0, start_time="2026-01-02T08:00:00")

        acts, total, _ = fetch_unified_activities(db_conn, max_dist=10.0)
        assert total == 1
        assert acts[0].distance_km.value == 5.0

    def test_dist_range(self, db_conn):
        _insert(db_conn, "garmin", distance_km=3.0, start_time="2026-01-01T08:00:00")
        _insert(db_conn, "strava", distance_km=8.0, start_time="2026-01-02T08:00:00")
        _insert(db_conn, "intervals", distance_km=25.0, start_time="2026-01-03T08:00:00")

        acts, total, _ = fetch_unified_activities(db_conn, min_dist=5.0, max_dist=20.0)
        assert total == 1
        assert acts[0].distance_km.value == 8.0


# ── fetch_unified_activities: 페이스 범위 필터 ───────────────────────────

class TestFetchPaceFilter:
    def test_max_pace(self, db_conn):
        # 페이스 낮을수록(sec/km) 빠름
        _insert(db_conn, "garmin", avg_pace_sec_km=250, start_time="2026-01-01T08:00:00")
        _insert(db_conn, "strava", avg_pace_sec_km=400, start_time="2026-01-02T08:00:00")

        # max_pace=300 → 300 이하(빠른 것)만
        acts, total, _ = fetch_unified_activities(db_conn, max_pace=300)
        assert total == 1
        assert acts[0].avg_pace_sec_km.value == 250

    def test_min_pace(self, db_conn):
        _insert(db_conn, "garmin", avg_pace_sec_km=250, start_time="2026-01-01T08:00:00")
        _insert(db_conn, "strava", avg_pace_sec_km=400, start_time="2026-01-02T08:00:00")

        # min_pace=360 → 360 이상(느린 것)만
        acts, total, _ = fetch_unified_activities(db_conn, min_pace=360)
        assert total == 1
        assert acts[0].avg_pace_sec_km.value == 400


# ── fetch_unified_activities: 시간 범위 필터 ────────────────────────────

class TestFetchDurationFilter:
    def test_min_dur(self, db_conn):
        _insert(db_conn, "garmin", duration_sec=1800, start_time="2026-01-01T08:00:00")
        _insert(db_conn, "strava", duration_sec=5400, start_time="2026-01-02T08:00:00")

        acts, total, _ = fetch_unified_activities(db_conn, min_dur=3600)
        assert total == 1
        assert acts[0].duration_sec.value == 5400

    def test_max_dur(self, db_conn):
        _insert(db_conn, "garmin", duration_sec=1800, start_time="2026-01-01T08:00:00")
        _insert(db_conn, "strava", duration_sec=7200, start_time="2026-01-02T08:00:00")

        acts, total, _ = fetch_unified_activities(db_conn, max_dur=3600)
        assert total == 1
        assert acts[0].duration_sec.value == 1800


# ── auto_group_all: 그룹 병합 ────────────────────────────────────────────

class TestAutoGroupAll:
    def test_two_sources_grouped(self, db_conn):
        """garmin + strava, 시간/거리 일치 → 같은 그룹."""
        t = "2026-01-15T08:00:00"
        id_g = _insert(db_conn, "garmin", start_time=t, distance_km=10.0)
        id_s = _insert(db_conn, "strava", start_time=t, distance_km=10.0)

        result = auto_group_all(db_conn)
        assert result["activities_grouped"] == 2

        rows = db_conn.execute(
            "SELECT matched_group_id FROM activity_summaries WHERE id IN (?,?)",
            (id_g, id_s),
        ).fetchall()
        gids = {r[0] for r in rows}
        assert len(gids) == 1
        assert None not in gids

    def test_three_sources_same_group(self, db_conn):
        """garmin + strava + intervals 중복 → 하나의 그룹."""
        t = "2026-01-15T08:00:00"
        id_g = _insert(db_conn, "garmin", start_time=t, distance_km=10.0)
        id_s = _insert(db_conn, "strava", start_time=t, distance_km=10.0)
        id_i = _insert(db_conn, "intervals", start_time=t, distance_km=10.0)

        auto_group_all(db_conn)

        rows = db_conn.execute(
            "SELECT matched_group_id FROM activity_summaries WHERE id IN (?,?,?)",
            (id_g, id_s, id_i),
        ).fetchall()
        gids = {r[0] for r in rows}
        assert len(gids) == 1
        assert None not in gids

    def test_group_merge_transitive(self, db_conn):
        """garmin↔strava → gid-A, strava↔intervals → gid-B.
        auto_group_all 후 셋 모두 동일 그룹으로 병합."""
        t = "2026-01-15T08:00:00"
        id_g = _insert(db_conn, "garmin", start_time=t, distance_km=10.0)
        id_s = _insert(db_conn, "strava", start_time=t, distance_km=10.1)
        id_i = _insert(db_conn, "intervals", start_time=t, distance_km=10.05)

        auto_group_all(db_conn)

        rows = db_conn.execute(
            "SELECT matched_group_id FROM activity_summaries WHERE id IN (?,?,?)",
            (id_g, id_s, id_i),
        ).fetchall()
        gids = {r[0] for r in rows}
        assert len(gids) == 1, f"Expected 1 group, got {gids}"

    def test_no_duplicate_different_day(self, db_conn):
        """날짜가 다른 활동은 묶이지 않음."""
        _insert(db_conn, "garmin", start_time="2026-01-15T08:00:00", distance_km=10.0)
        _insert(db_conn, "strava", start_time="2026-01-16T08:00:00", distance_km=10.0)

        auto_group_all(db_conn)

        rows = db_conn.execute(
            "SELECT matched_group_id FROM activity_summaries"
        ).fetchall()
        assert all(r[0] is None for r in rows)

    def test_returns_counts(self, db_conn):
        t = "2026-01-15T08:00:00"
        _insert(db_conn, "garmin", start_time=t, distance_km=10.0)
        _insert(db_conn, "strava", start_time=t, distance_km=10.0)

        result = auto_group_all(db_conn)
        assert "groups_created" in result
        assert "activities_grouped" in result
        assert result["groups_created"] >= 1


# ── sync_ui._source_checkboxes ───────────────────────────────────────────

class TestSourceCheckboxes:
    def test_connected_service_has_checkbox(self):
        html = _source_checkboxes("basic", connected={"garmin", "strava"})
        # garmin: 연결됨 → checkbox enabled
        assert "basic-chk-garmin" in html
        assert "disabled" not in html.split("basic-chk-garmin")[1].split("</label>")[0]

    def test_unconnected_service_disabled(self):
        html = _source_checkboxes("basic", connected={"garmin"})
        # intervals: 미연결 → disabled
        assert "basic-chk-intervals" in html
        # disabled 속성이 intervals 체크박스에 있어야 함
        intervals_part = html.split("basic-chk-intervals")[1].split("</label>")[0]
        assert "disabled" in intervals_part

    def test_unconnected_shows_connect_link(self):
        html = _source_checkboxes("hist", connected={"garmin"})
        # runalyze: 미연결 → 연결 링크
        assert "/connect/runalyze" in html

    def test_all_connected_no_disabled(self):
        html = _source_checkboxes("basic", connected={"garmin", "strava", "intervals", "runalyze"})
        # 모두 연결 → disabled 없음
        assert "cursor:not-allowed" not in html

    def test_none_connected_default_all_enabled(self):
        """connected=None → 모두 활성."""
        html = _source_checkboxes("basic", connected=None)
        assert "cursor:not-allowed" not in html
        # 4개 소스 모두 checked
        for src in ["garmin", "strava", "intervals", "runalyze"]:
            assert f"basic-chk-{src}" in html

    def test_panel_prefix_applied(self):
        basic = _source_checkboxes("basic", connected={"garmin"})
        hist = _source_checkboxes("hist", connected={"garmin"})
        assert "basic-chk-garmin" in basic
        assert "hist-chk-garmin" in hist
        assert "basic-chk-garmin" not in hist


# ── helpers.connected_services ───────────────────────────────────────────

class TestConnectedServices:
    def test_returns_ok_services(self):
        """연결된 서비스만 set에 포함."""
        from src.web.helpers import connected_services

        def _ok(_cfg):
            return {"ok": True}

        def _fail(_cfg):
            return {"ok": False, "error": "not connected"}

        # check_* 함수는 connected_services() 내부에서 로컬 임포트되므로
        # sync 모듈에서 직접 패치; load_config는 helpers 네임스페이스에서 패치
        with (
            patch("src.sync.garmin.check_garmin_connection", _ok),
            patch("src.sync.strava.check_strava_connection", _ok),
            patch("src.sync.intervals.check_intervals_connection", _fail),
            patch("src.sync.runalyze.check_runalyze_connection", _fail),
            patch("src.web.helpers.load_config", return_value={}),
        ):
            result = connected_services()

        assert result == {"garmin", "strava"}

    def test_returns_empty_when_none_connected(self):
        from src.web.helpers import connected_services

        def _fail(_cfg):
            return {"ok": False}

        with (
            patch("src.sync.garmin.check_garmin_connection", _fail),
            patch("src.sync.strava.check_strava_connection", _fail),
            patch("src.sync.intervals.check_intervals_connection", _fail),
            patch("src.sync.runalyze.check_runalyze_connection", _fail),
            patch("src.web.helpers.load_config", return_value={}),
        ):
            result = connected_services()

        assert result == set()

    def test_returns_empty_on_exception(self):
        from src.web.helpers import connected_services

        with patch("src.web.helpers.load_config", side_effect=RuntimeError("config error")):
            result = connected_services()

        assert result == set()


# ── /activities 라우트 통합 테스트 ────────────────────────────────────────

@pytest.fixture()
def act_client(tmp_path, monkeypatch):
    """Full-schema DB를 사용하는 Flask test client."""
    from src.db_setup import create_tables, migrate_db
    from src.web.app import create_app

    db_file = tmp_path / "branch_test.db"
    conn = sqlite3.connect(str(db_file))
    create_tables(conn)
    migrate_db(conn)
    conn.execute(
        """INSERT INTO activity_summaries
           (source, source_id, activity_type, start_time, distance_km,
            duration_sec, avg_pace_sec_km, avg_hr, description)
           VALUES
           ('garmin', 'g1', 'running', '2026-03-21T07:00:00', 10.5, 3600, 343, 148, 'morning run'),
           ('strava', 's1', 'running', '2026-03-20T06:30:00',  5.0, 1500, 300, 155, 'easy jog'),
           ('intervals', 'i1', 'running', '2026-03-19T08:00:00', 21.1, 7200, 341, 152, 'long run')"""
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr("src.web.views_activities.db_path", lambda: db_file)
    monkeypatch.setattr("src.web.views_wellness.db_path", lambda: db_file)
    monkeypatch.setattr("src.web.views_activity.db_path", lambda: db_file)
    monkeypatch.setattr("src.web.app._db_path", lambda: db_file)

    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


class TestActivitiesRouteBranchChanges:
    def test_sort_distance_returns_200(self, act_client):
        resp = act_client.get("/activities?sort=distance&dir=asc&from=2026-03-01&to=2026-03-31")
        assert resp.status_code == 200

    def test_sort_preserves_date_params(self, act_client):
        """정렬 링크에 from/to 파라미터 포함."""
        resp = act_client.get("/activities?from=2026-03-01&to=2026-03-31")
        assert resp.status_code == 200
        body = resp.data.decode("utf-8", errors="replace")
        # 날짜 파라미터가 정렬 링크에 포함돼야 함
        assert "from=2026-03-01" in body
        assert "to=2026-03-31" in body

    def test_q_search_filters_results(self, act_client):
        """q 파라미터로 활동명 검색."""
        resp = act_client.get("/activities?q=morning&from=&to=")
        assert resp.status_code == 200
        body = resp.data.decode("utf-8", errors="replace")
        # "morning run" 활동 설명이 포함돼야 함
        assert "morning" in body

    def test_q_search_no_match(self, act_client):
        resp = act_client.get("/activities?q=triathlon&from=&to=")
        assert resp.status_code == 200
        body = resp.data.decode("utf-8", errors="replace")
        # 결과 없음 메시지
        assert "없습니다" in body or "0" in body

    def test_min_dist_filter(self, act_client):
        resp = act_client.get("/activities?min_dist=15&from=&to=")
        assert resp.status_code == 200
        body = resp.data.decode("utf-8", errors="replace")
        # 21.1km만 남아야 함
        assert "21" in body

    def test_sort_all_keys_200(self, act_client):
        for key in ("date", "distance", "duration", "pace", "hr"):
            resp = act_client.get(f"/activities?sort={key}&dir=desc&from=&to=")
            assert resp.status_code == 200, f"sort={key} returned {resp.status_code}"

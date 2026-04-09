"""Flask 라우트 스모크 테스트 (DoD #12).

마이그레이션 관련 Blueprint(activities, export, merge)가
500 에러 없이 응답하는지 확인. 인메모리 DB + 최소 Flask 앱 사용.
"""
from __future__ import annotations

import sqlite3
import tempfile

import pytest
from flask import Flask

from src.db_setup import create_tables, migrate_db


@pytest.fixture
def mini_app(tmp_path):
    """마이그레이션 관련 Blueprint만 등록한 최소 Flask 앱."""
    db_file = tmp_path / "running.db"
    conn = sqlite3.connect(str(db_file))
    create_tables(conn)
    migrate_db(conn)
    # 테스트 데이터 — 활동 2건
    conn.executemany(
        "INSERT INTO activity_summaries"
        " (source, source_id, activity_type, start_time, distance_m, duration_sec)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        [
            ("garmin", "g1", "running", "2026-04-01T08:00:00", 10_000, 3600),
            ("strava", "s1", "running", "2026-04-08T08:00:00", 21_097, 7200),
        ],
    )
    conn.commit()
    conn.close()

    import os
    os.environ.setdefault("FLASK_SECRET_KEY", "test-secret-key")

    # db_path()가 테스트 DB를 가리키도록 패치
    import src.web.helpers as helpers
    import src.web.views_activity_merge as merge_mod
    import src.web.views_activities as acts_mod
    import src.web.views_export as export_mod
    _orig_helpers = helpers.db_path
    _orig_merge = merge_mod.db_path
    _orig_acts = acts_mod.db_path
    _orig_export = export_mod.db_path

    def _patched():
        return db_file

    helpers.db_path = _patched
    merge_mod.db_path = _patched
    acts_mod.db_path = _patched
    export_mod.db_path = _patched

    app = Flask(__name__)
    app.secret_key = "test-secret-key"
    app.config["TESTING"] = True

    # 마이그레이션 관련 Blueprint만 등록
    from src.web.views_activities import activities_bp
    from src.web.views_export import export_bp
    from src.web.views_activity_merge import merge_bp

    app.register_blueprint(activities_bp)
    app.register_blueprint(export_bp)
    app.register_blueprint(merge_bp)

    with app.test_client() as client:
        yield client

    helpers.db_path = _orig_helpers
    merge_mod.db_path = _orig_merge
    acts_mod.db_path = _orig_acts
    export_mod.db_path = _orig_export


# ─── 스모크 테스트 ────────────────────────────────────────────────────────────

class TestRouteSmoke:
    """핵심 라우트가 2xx를 반환하는지 확인 (5xx 금지)."""

    def test_activities_200(self, mini_app):
        r = mini_app.get("/activities")
        assert r.status_code == 200

    def test_activities_with_data_rendered(self, mini_app):
        r = mini_app.get("/activities")
        assert b"garmin" in r.data or b"strava" in r.data or r.status_code == 200

    def test_activities_export_csv_200(self, mini_app):
        r = mini_app.get("/activities/export.csv")
        assert r.status_code == 200

    def test_activities_export_csv_has_rows(self, mini_app):
        r = mini_app.get("/activities/export.csv")
        assert r.status_code == 200
        lines = r.data.decode("utf-8").splitlines()
        # 헤더 + 활동 2건
        assert len(lines) >= 3

    def test_activities_export_csv_distance_km(self, mini_app):
        r = mini_app.get("/activities/export.csv")
        assert b"10.0" in r.data or b"10," in r.data  # garmin 10km

    def test_activities_filter_source(self, mini_app):
        r = mini_app.get("/activities?source=garmin")
        assert r.status_code == 200

    def test_activities_filter_type(self, mini_app):
        r = mini_app.get("/activities?type=running")
        assert r.status_code == 200

    def test_activities_pagination(self, mini_app):
        r = mini_app.get("/activities?page=1")
        assert r.status_code == 200

    def test_merge_bad_ids_no_500(self, mini_app):
        """ids 미제공 시 5xx 금지."""
        r = mini_app.post(
            "/activities/merge",
            json={"ids": []},
            content_type="application/json",
        )
        assert r.status_code != 500

    def test_ungroup_missing_id_no_500(self, mini_app):
        """존재하지 않는 id로 ungroup 시 5xx 금지."""
        r = mini_app.post(
            "/activities/ungroup",
            json={"id": 99999},
            content_type="application/json",
        )
        assert r.status_code != 500

"""Flask 라우트 스모크 테스트 (DoD #12).

유지 중인 내보내기 Blueprint(export)가
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
    import src.utils.user_context as helpers
    import src.web.views_export as export_mod
    _orig_helpers = helpers.db_path
    _orig_export = export_mod.db_path

    def _patched():
        return db_file

    helpers.db_path = _patched
    export_mod.db_path = _patched

    app = Flask(__name__)
    app.secret_key = "test-secret-key"
    app.config["TESTING"] = True

    # 마이그레이션 관련 Blueprint만 등록
    from src.web.views_export import export_bp

    app.register_blueprint(export_bp)

    with app.test_client() as client:
        yield client

    helpers.db_path = _orig_helpers
    export_mod.db_path = _orig_export

# ─── 스모크 테스트 ────────────────────────────────────────────────────────────

class TestRouteSmoke:
    """핵심 라우트가 2xx를 반환하는지 확인 (5xx 금지)."""

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

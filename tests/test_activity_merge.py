"""활동 그룹 병합/분리 API 엔드포인트 테스트."""
from __future__ import annotations

import json
import sqlite3
from unittest.mock import patch

import pytest

from src.web.views_activity_merge import merge_bp
from flask import Flask


@pytest.fixture
def app(tmp_path):
    db_file = tmp_path / "running.db"
    conn = sqlite3.connect(str(db_file))
    conn.execute("""
        CREATE TABLE activity_summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            source_id TEXT,
            activity_type TEXT,
            start_time TEXT,
            distance_km REAL,
            duration_sec INTEGER,
            avg_pace_sec_km INTEGER,
            avg_hr REAL,
            max_hr REAL,
            avg_cadence REAL,
            elevation_gain REAL,
            calories REAL,
            description TEXT,
            matched_group_id TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute(
        "INSERT INTO activity_summaries (source, source_id) VALUES ('garmin', 'g1')"
    )
    conn.execute(
        "INSERT INTO activity_summaries (source, source_id) VALUES ('strava', 's1')"
    )
    conn.execute(
        "INSERT INTO activity_summaries (source, source_id, matched_group_id)"
        " VALUES ('intervals', 'i1', 'existing-group')"
    )
    conn.commit()
    conn.close()

    flask_app = Flask(__name__)
    flask_app.register_blueprint(merge_bp)
    flask_app.testing = True

    with patch("src.web.views_activity_merge.db_path", return_value=db_file):
        yield flask_app, db_file


class TestMergeEndpoint:
    def test_merge_two_activities(self, app):
        flask_app, db_file = app
        with flask_app.test_client() as client:
            resp = client.post(
                "/activities/merge",
                data=json.dumps({"ids": [1, 2]}),
                content_type="application/json",
            )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["ok"] is True
        assert data["group_id"]

        conn = sqlite3.connect(str(db_file))
        rows = conn.execute(
            "SELECT matched_group_id FROM activity_summaries WHERE id IN (1, 2)"
        ).fetchall()
        conn.close()
        gids = {r[0] for r in rows}
        assert len(gids) == 1
        assert None not in gids

    def test_merge_requires_two(self, app):
        flask_app, _ = app
        with flask_app.test_client() as client:
            resp = client.post(
                "/activities/merge",
                data=json.dumps({"ids": [1]}),
                content_type="application/json",
            )
        assert resp.status_code == 400

    def test_merge_missing_ids(self, app):
        flask_app, _ = app
        with flask_app.test_client() as client:
            resp = client.post(
                "/activities/merge",
                data=json.dumps({}),
                content_type="application/json",
            )
        assert resp.status_code == 400

    def test_merge_invalid_ids(self, app):
        flask_app, _ = app
        with flask_app.test_client() as client:
            resp = client.post(
                "/activities/merge",
                data=json.dumps({"ids": ["a", "b"]}),
                content_type="application/json",
            )
        assert resp.status_code == 400


class TestUngroupEndpoint:
    def test_ungroup_activity(self, app):
        flask_app, db_file = app
        # id=3 는 existing-group에 속함
        with flask_app.test_client() as client:
            resp = client.post(
                "/activities/ungroup",
                data=json.dumps({"id": 3}),
                content_type="application/json",
            )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["ok"] is True

        conn = sqlite3.connect(str(db_file))
        row = conn.execute(
            "SELECT matched_group_id FROM activity_summaries WHERE id = 3"
        ).fetchone()
        conn.close()
        assert row[0] is None

    def test_ungroup_missing_id(self, app):
        flask_app, _ = app
        with flask_app.test_client() as client:
            resp = client.post(
                "/activities/ungroup",
                data=json.dumps({}),
                content_type="application/json",
            )
        assert resp.status_code == 400

    def test_ungroup_invalid_id(self, app):
        flask_app, _ = app
        with flask_app.test_client() as client:
            resp = client.post(
                "/activities/ungroup",
                data=json.dumps({"id": "bad"}),
                content_type="application/json",
            )
        assert resp.status_code == 400

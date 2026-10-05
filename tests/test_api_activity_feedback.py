"""활동 피드백 API 테스트."""
import sqlite3

import pytest
from flask import Flask

from src.db_setup import create_tables


@pytest.fixture
def client(tmp_path, monkeypatch):
    f = tmp_path / "running.db"
    c = sqlite3.connect(str(f))
    create_tables(c)
    c.execute("INSERT INTO activity_summaries(source, source_id, activity_type, start_time, distance_m, duration_sec)"
              " VALUES ('garmin','g1','running','2026-04-01T08:00:00Z',5000,1800)")
    c.commit()
    aid = c.execute("SELECT id FROM activity_summaries").fetchone()[0]
    c.close()
    import src.api.routes_library_feedback as r
    monkeypatch.setattr(r, "db_path", lambda: f)
    app = Flask(__name__)
    from src.api import api_bp
    app.register_blueprint(api_bp)
    with app.test_client() as cl:
        yield cl, aid


def test_get_empty_null(client):
    cl, aid = client
    assert cl.get(f"/api/v1/library/activities/{aid}/feedback").get_json()["data"]["feedback"] is None


def test_unknown_activity_404(client):
    cl, _ = client
    assert cl.get("/api/v1/library/activities/9999/feedback").status_code == 404
    assert cl.put("/api/v1/library/activities/9999/feedback", json={"rpe": 5}).status_code == 404


def test_put_get_delete(client):
    cl, aid = client
    u = f"/api/v1/library/activities/{aid}/feedback"
    r = cl.put(u, json={"rpe": 7, "pain": "mild", "pain_sites": ["knee"]})
    assert r.status_code == 200 and r.get_json()["data"]["feedback"]["rpe"] == 7
    assert cl.get(u).get_json()["data"]["feedback"]["pain_sites"] == ["knee"]
    assert cl.put(u, json={}).get_json()["data"]["feedback"] is None
    cl.put(u, json={"rpe": 3})
    assert cl.delete(u).status_code == 204
    assert cl.get(u).get_json()["data"]["feedback"] is None


def test_put_invalid_400_code(client):
    cl, aid = client
    r = cl.put(f"/api/v1/library/activities/{aid}/feedback", json={"rpe": 99})
    assert r.status_code == 400 and r.get_json()["error"]["code"] == "INVALID_RPE"
    assert cl.put(f"/api/v1/library/activities/{aid}/feedback", data="x").status_code == 400

"""P7-PRED-53·71: 예측 비교·대회 확인 API."""
from __future__ import annotations

import sqlite3

import pytest
from flask import Flask

from src.db_setup import create_tables, migrate_db
from src.utils.db_helpers import upsert_metric
from tests.helpers_pred import seed_run


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_file = tmp_path / "running.db"
    conn = sqlite3.connect(str(db_file))
    create_tables(conn)
    migrate_db(conn)
    aid = seed_run(conn, sid="1", date="2026-09-12", name="Forest run", event_type="race")
    upsert_metric(conn, "daily", "2026-09-26", "race_pred_10k_sec", "runpulse:formula_v1", numeric_value=2739)
    conn.commit()
    conn.close()
    import src.api.routes_prediction as rp
    monkeypatch.setattr(rp, "db_path", lambda: db_file)
    app = Flask(__name__)
    app.config["TESTING"] = True
    from src.api import api_bp
    app.register_blueprint(api_bp)
    with app.test_client() as c:
        c.aid = aid
        yield c


def test_compare(client):
    r = client.get("/api/v1/prediction/compare?bucket=10k&date=2026-09-26")
    assert r.status_code == 200
    rows = r.get_json()["data"]["rows"]
    assert [x["key"] for x in rows] == ["garmin", "ref", "self"] and rows[2]["value_sec"] == 2739
    assert client.get("/api/v1/prediction/compare?bucket=3k").status_code == 400


def test_profile(client):
    d = client.get("/api/v1/prediction/profile?date=2026-09-26").get_json()["data"]
    assert d == {"as_of": "2026-09-26", "hr_profile": None, "heat_model": None, "training_response": None}


def test_confirm_flow(client):
    r = client.get("/api/v1/races/candidates?since=2026-01-01")
    assert r.get_json()["data"]["items"][0]["activity_id"] == client.aid
    r = client.put(f"/api/v1/races/{client.aid}/confirm", json={"effort": "allout", "official_time_sec": 2800})
    assert r.status_code == 200 and r.get_json()["data"]["effort"] == "allout"
    assert client.put(f"/api/v1/races/{client.aid}/confirm", json={"effort": "x"}).status_code == 400
    assert client.put("/api/v1/races/999/confirm", json={"effort": "allout"}).status_code == 404
    assert client.delete(f"/api/v1/races/{client.aid}/confirm").get_json()["data"]["deleted"] is True

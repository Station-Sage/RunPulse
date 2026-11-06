"""/api/v1/shoes* + 활동 신발 PUT/DELETE — 봉투·Origin 관문·검증·비러닝·409·200건 제한."""
import sqlite3

import pytest
from flask import Flask

from src.db_setup import create_tables

H = {"Origin": "http://localhost"}


@pytest.fixture
def ctx(tmp_path, monkeypatch):
    f = tmp_path / "running.db"
    c = sqlite3.connect(str(f))
    create_tables(c)
    c.execute("INSERT INTO activity_summaries (source, source_id, activity_type, start_time, distance_m)"
              " VALUES ('garmin','a1','running','2026-05-01T07:00:00',10000),"
              " ('garmin','a2','swimming','2026-05-01T09:00:00',1000)")
    c.execute("INSERT INTO gear (id, source, source_gear_id, name, gear_type) VALUES (7,'strava','g7','Peg','shoes')")
    c.commit()
    c.close()
    import src.api.routes_shoes as m
    monkeypatch.setattr(m, "db_path", lambda: f)
    from src.api import api_bp
    from src.web import request_guard as rg
    app = Flask(__name__)
    app.register_blueprint(api_bp)
    rg.init_request_guard(app)
    return app.test_client()


def _create(cl, **kw):
    return cl.post("/api/v1/shoes", json={"name": "Road", **kw}, headers=H)


def test_crud_envelope(ctx):
    r = _create(ctx, category="daily", initial_distance_km=100, default_for="road")
    assert r.status_code == 201
    d = r.get_json()["data"]
    sid = d["id"]
    assert d["mileage_km"] == 100.0 and d["status"] == "ok"  # 기본 신발은 지정일(오늘) 이전 활동에 배정 안 함
    lst = ctx.get("/api/v1/shoes").get_json()["data"]
    assert [s["id"] for s in lst["shoes"]] == [sid] and lst["unassigned_count"] == 1
    assert len(lst["suggestions"]) == 1
    r = ctx.patch(f"/api/v1/shoes/{sid}", json={"retired_at": "2026-05-09"}, headers=H)
    assert r.get_json()["data"]["status"] == "retired"
    assert ctx.get("/api/v1/shoes?include_retired=0").get_json()["data"]["shoes"] == []
    assert ctx.get(f"/api/v1/shoes/{sid}/activities").get_json()["data"]["total"] == 0
    assert ctx.delete(f"/api/v1/shoes/{sid}", headers=H).status_code == 200
    r = ctx.get(f"/api/v1/shoes/{sid}")
    assert r.status_code == 404 and r.get_json()["error"]["code"] == "NOT_FOUND"


def test_write_without_origin_403(ctx):
    assert ctx.post("/api/v1/shoes", json={"name": "x"}).status_code == 403


def test_validation_400(ctx):
    for body in ({}, {"name": "x" * 61}, {"name": "a", "category": "zzz"}, {"name": "a", "retire_km": 50},
                 {"name": "a", "initial_distance_km": 3001}, {"name": "a", "start_date": "2026/01/01"}):
        r = ctx.post("/api/v1/shoes", json=body, headers=H)
        assert r.status_code == 400 and r.get_json()["error"]["code"] == "INVALID_PARAM", body


def test_activity_shoe_put_delete(ctx):
    sid = _create(ctx).get_json()["data"]["id"]
    r = ctx.put("/api/v1/library/activities/1/shoe", json={"shoe_id": sid}, headers=H)
    assert r.status_code == 200 and r.get_json()["data"]["shoe"]["method"] == "manual"
    r = ctx.put("/api/v1/library/activities/1/shoe", json={"shoe_id": None}, headers=H)
    assert r.get_json()["data"]["shoe"] == {"id": None, "name": None, "status": None, "method": "manual", "source": None,
                                             "conflict": False, "conflict_sources": []}
    r = ctx.delete("/api/v1/library/activities/1/shoe", headers=H)
    assert r.get_json()["data"]["shoe"]["method"] == "none"
    r = ctx.put("/api/v1/library/activities/2/shoe", json={"shoe_id": sid}, headers=H)
    assert r.status_code == 400 and r.get_json()["error"]["code"] == "NOT_RUNNING"
    assert ctx.put("/api/v1/library/activities/999/shoe", json={"shoe_id": sid}, headers=H).status_code == 404
    assert ctx.put("/api/v1/library/activities/1/shoe", json={}, headers=H).status_code == 400


def test_gear_link_conflict_409(ctx):
    a = _create(ctx, name="A").get_json()["data"]["id"]
    b = _create(ctx, name="B").get_json()["data"]["id"]
    assert ctx.post(f"/api/v1/shoes/{a}/gear", json={"gear_id": 7}, headers=H).status_code == 200
    r = ctx.post(f"/api/v1/shoes/{b}/gear", json={"gear_id": 7}, headers=H)
    assert r.status_code == 409 and r.get_json()["error"]["code"] == "GEAR_LINKED"
    assert ctx.delete(f"/api/v1/shoes/{a}/gear/7", headers=H).status_code == 200
    r = ctx.post(f"/api/v1/shoes/{a}/merge", json={"source_shoe_id": b}, headers=H)
    assert r.status_code == 200 and ctx.get(f"/api/v1/shoes/{b}").status_code == 404


def test_bulk_assign_limit_and_import(ctx):
    sid = _create(ctx).get_json()["data"]["id"]
    r = ctx.post(f"/api/v1/shoes/{sid}/assign", json={"activity_ids": list(range(1, 202))}, headers=H)
    assert r.status_code == 400
    r = ctx.post(f"/api/v1/shoes/{sid}/assign", json={"activity_ids": [1, 2]}, headers=H)
    assert r.get_json()["data"] == {"assigned": 1, "skipped_non_running": 1, "skipped_missing": 0}
    assert ctx.get("/api/v1/shoes/unassigned").get_json()["data"]["total"] == 0
    r = ctx.post("/api/v1/shoes/import-gear", headers=H)
    assert r.get_json()["data"] == {"created": 1, "linked": 1}
    assert ctx.get("/api/v1/shoes/alert").get_json()["data"] == {"alert": None}


def test_activity_detail_has_shoe_field(ctx, tmp_path):
    from src.services.activity_detail_service import get_activity_detail
    c = sqlite3.connect(str(tmp_path / "running.db"))
    assert get_activity_detail(c, 1)["shoe"]["method"] == "none"
    assert get_activity_detail(c, 2)["shoe"] is None

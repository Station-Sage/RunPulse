"""생성 화면 훈련 방식 — 목표 없는 후보·추천(/coach/plan/methods/draft)과 plan_method 생성 반영."""
import sqlite3

import pytest
from flask import Flask

from src.db_setup import create_tables, migrate_db
from src.services import method_recommend as mr
from src.services import method_recommend_draft as md
from src.services import plan_template_service as pts


@pytest.fixture
def db(tmp_path):
    f = tmp_path / "running.db"
    c = sqlite3.connect(str(f))
    create_tables(c)
    migrate_db(c)
    c.commit()
    c.close()
    return f


def _client(f, monkeypatch):
    import src.api.routes_plan_replan as m
    monkeypatch.setattr(m, "db_path", lambda: f)
    monkeypatch.setattr(mr, "_consent_ok", lambda conn: False)
    monkeypatch.setattr(md.threading, "Thread", lambda target, **k: type("T", (), {"start": lambda s: None})())
    md._cooldown.clear()
    app = Flask(__name__)
    from src.api import api_bp
    app.register_blueprint(api_bp)
    return app.test_client()


def test_draft_candidates_by_distance_and_days(db, monkeypatch):
    cl = _client(db, monkeypatch)
    d = cl.get("/api/v1/coach/plan/methods/draft?distance_km=42.195&run_days=3").get_json()["data"]
    ids = [m["id"] for m in d["methods"]]
    assert d["distance_label"] == "full" and "balanced" in ids and "first_run3" in ids and "hansons" not in ids
    assert d["source"] == "rule" and d["recommended"] == "first_run3" and d["pending"] is True
    d2 = cl.get("/api/v1/coach/plan/methods/draft?distance_km=42.195&run_days=3").get_json()["data"]
    assert d2["pending"] is False
    d10 = cl.get("/api/v1/coach/plan/methods/draft?distance_km=10&run_days=5").get_json()["data"]
    assert d10["distance_label"] == "10k" and d10["recommended"] == "balanced"


def test_draft_requires_distance(db, monkeypatch):
    assert _client(db, monkeypatch).get("/api/v1/coach/plan/methods/draft").status_code == 400


def test_create_plan_sets_method_and_guards(db):
    c = sqlite3.connect(str(db))
    with pytest.raises(pts.InvalidMethod):
        pts.create_plan_from_template(c, 10.0, None, 8, run_weekdays=[0, 2, 4], plan_method="hansons")
    gid = pts.create_plan_from_template(c, 10.0, None, 8, run_weekdays=[0, 2, 4, 5], plan_method="threshold_vo2")
    assert c.execute("SELECT plan_method FROM goals WHERE id=?", (gid,)).fetchone()[0] == "threshold_vo2"
    gid2 = pts.create_plan_from_template(c, 10.0, None, 8, run_weekdays=[0, 2, 4, 5])
    assert c.execute("SELECT plan_method FROM goals WHERE id=?", (gid2,)).fetchone()[0] == "balanced"

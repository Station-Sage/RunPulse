"""심화 분석 서비스·API (V2-AI-CLAUDE-QUEUE E5-d)."""
import sqlite3
import time

import pytest
from flask import Flask

from src.db_setup import create_tables, migrate_db
from src.services import deep_analysis as da

H = {"Origin": "http://localhost"}
GOOD = "가" * 120 + '\n```json\n{"suggestions": ["a", "b", "c", "d"]}\n```'


@pytest.fixture
def db(tmp_path):
    f = tmp_path / "running.db"
    c = sqlite3.connect(str(f))
    c.row_factory = sqlite3.Row
    create_tables(c)
    migrate_db(c)
    c.execute("INSERT INTO activity_summaries(source, source_id, start_time, distance_m) VALUES ('garmin','1','2026-11-18T07:00:00',8000)")
    c.execute("INSERT INTO activity_summaries(source, source_id, activity_type, start_time) VALUES ('garmin','2','cycling','2026-11-19T07:00:00')")
    c.commit()
    yield f, c
    c.close()


def test_split_output():
    r = da.split_output(GOOD)
    assert len(r["suggestions"]) == 3 and "json" not in r["text"] and len(r["text"]) == 120
    assert da.split_output("짧음") is None and da.split_output(None) is None


def test_pick_activity_id_prefers_latest_run(db):
    _, c = db
    assert da.pick_activity_id(c) == 1
    assert da.pick_activity_id(c, 2) == 2 and da.pick_activity_id(c, 99) is None


def test_generate_stores_and_caches(db, monkeypatch):
    _, c = db
    from src.ai import claude_queue, provider_claude_queue as pcq
    monkeypatch.setattr(da, "build_prompt", lambda conn, a: "P")
    monkeypatch.setattr(pcq, "available", lambda conn, cfg: True)
    calls = []
    monkeypatch.setattr(claude_queue, "run_job", lambda *a, **k: calls.append(k) or {"ok": True, "text": GOOD, "reason": None})
    out = da.generate(c, {}, 1)
    assert out["state"] == "ready" and calls[0]["model"] == "opus" and calls[0]["tools"] == "read"
    assert da.generate(c, {}, 1)["state"] == "ready" and len(calls) == 1


def test_generate_failures(db, monkeypatch):
    _, c = db
    from src.ai import claude_queue, provider_claude_queue as pcq
    monkeypatch.setattr(da, "build_prompt", lambda conn, a: "P")
    monkeypatch.setattr(pcq, "available", lambda conn, cfg: True)
    monkeypatch.setattr(claude_queue, "run_job", lambda *a, **k: {"ok": False, "text": "", "reason": "cancelled"})
    assert da.generate(c, {}, 1)["state"] == "cancelled"
    monkeypatch.setattr(claude_queue, "run_job", lambda *a, **k: {"ok": True, "text": "짧", "reason": None})
    assert da.generate(c, {}, 1)["state"] == "failed" and da.get_cached(c, 1) is None
    monkeypatch.setattr(pcq, "available", lambda conn, cfg: False)
    assert "큐" in da.generate(c, {}, 1)["reason"]


def test_background_progress_and_cancel(db, monkeypatch):
    f, _ = db
    key = str(f)

    def fake(conn, cfg, aid, run_key=None):
        while not da._runs[run_key]["cancel"]:
            time.sleep(0.01)
        return {"state": "cancelled", "reason": "취소됨"}
    monkeypatch.setattr(da, "generate", fake)
    assert da.start_background(key, {}, 1) is True and da.start_background(key, {}, 1) is False
    assert da.run_state(key)["state"] == "running" and da.cancel(key) is True
    for _ in range(100):
        if da.run_state(key)["state"] != "running":
            break
        time.sleep(0.02)
    assert da.run_state(key)["state"] == "cancelled" and da.cancel(key) is False


def test_api(db, monkeypatch):
    f, _ = db
    import src.api.routes_deep_analysis as r
    import src.api.routes_plan_replan as rp
    monkeypatch.setattr(r, "db_path", lambda: f)
    monkeypatch.setattr(rp, "db_path", lambda: f)
    monkeypatch.setattr(r.pcq, "available", lambda conn, cfg: False)
    app = Flask(__name__)
    from src.api import api_bp
    app.register_blueprint(api_bp)
    cl = app.test_client()
    d = cl.get("/api/v1/coach/deep").get_json()["data"]
    assert d["activity_id"] == 1 and d["result"] is None and d["available"] is False
    assert cl.post("/api/v1/coach/deep", json={}, headers=H).status_code == 409
    assert cl.post("/api/v1/coach/deep/cancel", json={}, headers=H).get_json()["data"]["cancelled"] is False

"""v1 동기화 경로(/bg-sync/*, /trigger-sync-stream)가 sync_sources 토글을 따르는지 검증."""
import json

import pytest

import src.web.app as web_app


@pytest.fixture
def client(monkeypatch):
    app = web_app.create_app() if hasattr(web_app, "create_app") else None
    if app is None:
        pytest.skip("create_app 없음")
    app.config["TESTING"] = True
    cfg = {"sync_sources": ["garmin"]}
    monkeypatch.setattr(web_app, "load_config", lambda user_id=None: cfg)
    import src.web.bg_sync as bgs
    monkeypatch.setattr(bgs, "start_job", lambda *a, **k: "job1")
    monkeypatch.setattr(bgs, "resume_job", lambda *a, **k: True)
    with app.test_client() as c:
        yield c


def test_bg_start_blocks_disabled_source(client):
    r = client.post("/bg-sync/start", data={"source": "strava", "from_date": "2026-01-01"})
    assert r.status_code == 409 and "꺼져" in r.get_json()["error"]


def test_bg_start_allows_enabled_source(client):
    r = client.post("/bg-sync/start", data={"source": "garmin", "from_date": "2026-01-01"})
    assert r.status_code == 200 and r.get_json()["job_id"] == "job1"


def test_bg_resume_blocks_disabled_source(client):
    assert client.post("/bg-sync/resume", data={"source": "strava"}).status_code == 409


def test_stream_skips_disabled_source(client):
    r = client.post("/trigger-sync-stream", data={"source": "strava"})
    events = [json.loads(l[6:]) for l in r.get_data(as_text=True).splitlines() if l.startswith("data: ")]
    done = [e for e in events if e.get("type") == "source_done"]
    assert done and done[0]["reason"] == "disabled" and done[0]["skipped"] is True

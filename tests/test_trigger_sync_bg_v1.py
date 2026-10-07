"""v1 /trigger-sync-bg — 서비스 판정 위임 후에도 응답 포맷 유지."""
from __future__ import annotations

from datetime import date

from src.services.sync_trigger_service import SkipReason


def test_v1_response_shape(monkeypatch, tmp_path):
    from src.web import app as webapp
    import src.services.sync_trigger_service as svc
    import src.web.bg_sync as bg

    monkeypatch.setattr(webapp, "_db_path", lambda: tmp_path / "x.db")
    monkeypatch.setattr(webapp, "load_config", lambda user_id=None: {})
    monkeypatch.setattr(svc, "plan_incremental", lambda *a, **k: (
        ["garmin"], {"garmin": "2026-10-01"},
        [SkipReason("strava", "cooldown", "쿨다운", 30), SkipReason("runalyze", "not_connected", "미연결")]))
    monkeypatch.setattr(bg, "start_basic_sync", lambda *a, **k: {"garmin": "j1"})

    app = webapp.create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        d = c.post("/trigger-sync-bg", data={"source": "all"}).get_json()
    assert d["ok"] is True and d["started"] == ["garmin"] and d["job_ids"] == {"garmin": "j1"}
    assert {"source": "strava", "error": "쿨다운", "retry_after_sec": 30} in d["skipped"]
    assert {"source": "runalyze", "error": "미연결"} in d["skipped"]

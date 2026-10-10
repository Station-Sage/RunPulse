"""auto_sync — 실행마다 config 재로딩(G1), restart 후 스레드 유지(G7)."""
import time

from src.web import auto_sync


def _patch_sync(monkeypatch, captured):
    import src.web.bg_sync as bg
    import src.utils.sync_state as ss
    monkeypatch.setattr(bg, "start_basic_sync", lambda sources, *a, **k: captured.append(list(sources)) or [])
    monkeypatch.setattr(ss, "mark_auto_sync_ran", lambda uid: None)
    monkeypatch.setattr("src.utils.user_context.set_current_user", lambda uid: None)


def test_trigger_uses_reloaded_config(monkeypatch):
    got = []
    _patch_sync(monkeypatch, got)
    import src.utils.config as cfg
    monkeypatch.setattr(cfg, "load_config", lambda user_id=None: {
        "garmin": {"email": "a"}, "strava": {"refresh_token": "t"}, "sync_sources": ["garmin"]})
    stale = {"garmin": {"email": "a"}, "strava": {"refresh_token": "t"}, "sync_sources": ["garmin", "strava"]}
    auto_sync._trigger(stale, "u", 2)
    assert got == [["garmin"]]


def test_trigger_falls_back_on_reload_failure(monkeypatch):
    got = []
    _patch_sync(monkeypatch, got)
    import src.utils.config as cfg

    def boom(user_id=None):
        raise RuntimeError("x")
    monkeypatch.setattr(cfg, "load_config", boom)
    auto_sync._trigger({"garmin": {"email": "a"}}, "u", 2)
    assert got == [["garmin"]]


def test_trigger_skips_when_all_disabled(monkeypatch):
    got = []
    _patch_sync(monkeypatch, got)
    import src.utils.config as cfg
    monkeypatch.setattr(cfg, "load_config", lambda user_id=None: {
        "garmin": {"email": "a"}, "sync_sources": []})
    auto_sync._trigger({}, "u", 2)
    assert got == []


def test_restart_keeps_thread_running(monkeypatch):
    monkeypatch.setattr(auto_sync, "_loop", lambda *a: auto_sync._stop_event.wait(30))
    cfg = {"auto_sync": {"enabled": True}}
    auto_sync.start(cfg)
    auto_sync.restart(cfg)
    time.sleep(0.1)
    assert auto_sync.status()["running"] is True
    auto_sync.stop()
    auto_sync._thread.join(timeout=5)

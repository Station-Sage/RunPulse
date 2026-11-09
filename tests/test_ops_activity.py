"""활동 신호(T2) — 10분 스로틀, 캘린더 피드 0 write, 복귀 시 poke, before_request 훅."""
from datetime import datetime, timedelta

from src.ops import activity as A
from src.ops.store import OpsStore, default_store

NOW = datetime(2026, 11, 6, 12, 0, 0)


class Mono:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def _rec(tmp_path, **kw):
    store = OpsStore(tmp_path / "ops.db")
    mono = Mono()
    return A.ActivityRecorder(store, clock=lambda: NOW, monotonic=mono, **kw), store, mono


def test_throttle_two_in_ten_minutes_one_write(tmp_path):
    rec, store, mono = _rec(tmp_path)
    assert rec.touch("u") is True
    mono.t += 599
    assert rec.touch("u") is False
    mono.t += 2
    assert rec.touch("u") is True
    assert store.last_active("u") == NOW


def test_empty_uid_ignored(tmp_path):
    rec, store, _ = _rec(tmp_path)
    assert rec.touch(None) is False and store.all_activity() == {}


def test_return_after_week_pokes(tmp_path):
    poked = []
    rec, store, _ = _rec(tmp_path, on_return=poked.append)
    store.touch_activity("u", NOW - timedelta(days=8))
    store.touch_activity("v", NOW - timedelta(days=2))
    rec.touch("u")
    rec.touch("v")
    assert poked == ["u"]


def test_store_failure_does_not_raise(tmp_path):
    class Bad:
        def touch_activity(self, *a):
            raise OSError("disk")
    rec = A.ActivityRecorder(Bad())
    assert rec.touch("u") is False


def test_should_record_excludes_calendar_feed():
    assert A.should_record("/api/v1/today")
    assert not A.should_record("/feeds/cal/abc.ics")


def test_before_request_hook_records_and_skips_feed(tmp_path):
    from flask import Flask, session
    app = Flask(__name__)
    app.secret_key = "t"
    A.init_activity_hook(app)

    @app.get("/x")
    def x():
        return "ok"

    @app.get("/feeds/cal/<t>")
    def feed(t):
        return "ics"

    @app.get("/login")
    def login():
        session["user_id"] = "a@x.com"
        return "ok"
    c = app.test_client()
    c.get("/login")                      # 로그인 요청 자체(세션 없음 → 기록 없음)
    A.recorder.reset()
    c.get("/feeds/cal/tok")
    assert default_store().all_activity() == {}
    c.get("/x")
    c.get("/x")
    assert list(default_store().all_activity()) == ["a@x.com"]


def test_module_touch_uses_default_store():
    assert A.touch("m@x.com") is True
    assert default_store().last_active("m@x.com") is not None

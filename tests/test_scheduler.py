"""MultiUserScheduler(T5) — tick() 직접 호출: 동시 상한, in-flight 중복 0, 예외 격리, busy/gated, 연체순, 휴면."""
import random
import threading
from datetime import datetime, timedelta

import pytest

from src.ops.store import OpsStore
from src.sync.scheduler import MultiUserScheduler, RunResult, SchedCfg

NOW = datetime(2026, 11, 6, 12, 0, 0)


class Clock:
    def __init__(self, t=NOW):
        self.t = t

    def __call__(self):
        return self.t


class DeferredExecutor:
    """submit 을 모아 두고 run_all 때 실행 — 동시 상한 검사용."""

    def __init__(self):
        self.jobs = []

    def submit(self, fn, *a):
        self.jobs.append((fn, a))

    def run_all(self):
        jobs, self.jobs = self.jobs, []
        for fn, a in jobs:
            fn(*a)


def make(tmp_path, users, trigger, *, last=None, interval=4, cfg=None, clock=None):
    clock = clock or Clock()
    store = OpsStore(tmp_path / "ops.db", clock=clock)
    ex = DeferredExecutor()
    suspended = []
    s = MultiUserScheduler(clock=clock, wait=lambda s: True, executor=ex, rng=random.Random(0),
                           users=lambda: list(users), trigger=trigger, store=store, cfg=cfg or SchedCfg(),
                           last_auto_run=lambda uid: (last or {}).get(uid), user_interval=lambda uid: interval,
                           suspend=lambda uid, svc: suspended.append((uid, svc)), release_user=lambda: None)
    return s, store, ex, clock, suspended


def ok(uid):
    return RunResult("ok", 4, ["garmin"], ["j"], {"garmin": "completed"})


def test_max_two_concurrent(tmp_path):
    s, _, ex, _, _ = make(tmp_path, ["a", "b", "c"], ok)
    rep = s.tick()
    assert rep.dispatched == 2 and len(ex.jobs) == 2 and rep.inflight == 2
    assert s.tick().dispatched == 0          # 슬롯이 차 있으면 더 보내지 않음
    ex.run_all()
    assert s.inflight() == set()
    assert s.tick().dispatched == 1          # c 차례


def test_inflight_not_duplicated(tmp_path):
    s, _, ex, _, _ = make(tmp_path, ["a"], ok)
    s.tick()
    s.tick()
    assert [a for _, a in ex.jobs] == [("a",)]


def test_exception_isolated(tmp_path):
    def trig(uid):
        if uid == "bad":
            raise RuntimeError("boom")
        return ok(uid)
    s, store, ex, _, _ = make(tmp_path, ["bad", "good"], trig)
    s.tick()
    ex.run_all()
    assert store.get_state("bad")["last_result"] == "fail"
    assert store.get_state("bad")["fail_streak"] == 1
    assert store.get_state("good")["last_result"] == "ok"
    assert s.inflight() == set()


def test_busy_defers_15min(tmp_path):
    s, store, ex, clock, _ = make(tmp_path, ["a"], lambda u: RunResult("skipped_busy", 4))
    s.tick()
    ex.run_all()
    assert store.get_state("a")["next_due_at"] == NOW + timedelta(minutes=15)
    assert s.tick().skipped == {"busy": 1}


def test_gated_uses_retry_after(tmp_path):
    at = NOW + timedelta(hours=3)
    s, store, ex, _, _ = make(tmp_path, ["a"], lambda u: RunResult("skipped_gated", 4, retry_at=at))
    s.tick()
    ex.run_all()
    assert store.get_state("a")["next_due_at"] == at


def test_slot_skip_keeps_due_and_no_run_row(tmp_path):
    s, store, ex, _, _ = make(tmp_path, ["a"], lambda u: RunResult("skipped_slot", 4))
    s.tick()
    ex.run_all()
    assert store.get_state("a")["next_due_at"] == NOW
    assert store.runs_since(NOW - timedelta(days=1)) == []


def test_overdue_order(tmp_path):
    last = {"a": NOW - timedelta(hours=5), "b": NOW - timedelta(hours=9), "c": NOW - timedelta(hours=6)}
    s, _, ex, _, _ = make(tmp_path, ["a", "b", "c"], ok, last=last)
    s.tick()
    assert [a[0] for _, a in ex.jobs] == ["b", "c"]


def test_not_due_not_dispatched(tmp_path):
    s, _, ex, _, _ = make(tmp_path, ["a"], ok, last={"a": NOW - timedelta(hours=1)})
    assert s.tick().dispatched == 0


def test_dormant_skipped_and_poke_reinit(tmp_path):
    s, store, ex, clock, _ = make(tmp_path, ["a"], ok)
    store.touch_activity("a", NOW - timedelta(days=31))
    rep = s.tick()
    assert rep.skipped == {"dormant": 1} and rep.dispatched == 0
    assert store.get_state("a")["state"] == "dormant"
    store.touch_activity("a", NOW)       # 활동 복귀
    s.poke("a")
    assert s.tick().dispatched == 1
    assert store.get_state("a")["state"] == "active"


def test_pinned_ignores_dormancy(tmp_path):
    s, store, ex, _, _ = make(tmp_path, ["a"], ok, cfg=SchedCfg(pinned=frozenset({"a"})))
    store.touch_activity("a", NOW - timedelta(days=90))
    assert s.tick().dispatched == 1


def test_ok_next_due_interval_plus_jitter_and_run_row(tmp_path):
    s, store, ex, _, _ = make(tmp_path, ["a"], ok)
    s.tick()
    ex.run_all()
    d = store.get_state("a")["next_due_at"] - NOW
    assert timedelta(hours=4) <= d <= timedelta(hours=4, minutes=10)
    assert store.runs_since(NOW - timedelta(hours=1))[0]["result"] == "ok"


def test_fail_backoff_grows(tmp_path):
    clock = Clock()
    s, store, ex, _, _ = make(tmp_path, ["a"], lambda u: RunResult("fail", 4), clock=clock)
    for _ in range(2):
        st = store.get_state("a")
        store.put_state("a", next_due_at=clock.t, fail_streak=st["fail_streak"] if st else 0)
        s.tick()
        ex.run_all()
    st = store.get_state("a")
    assert st["fail_streak"] == 2
    assert st["next_due_at"] - NOW >= timedelta(hours=16)


def test_auth_three_times_suspends_source(tmp_path):
    res = RunResult("auth", 4, ["garmin"], ["j"], {"garmin": "auth_required"})
    s, store, ex, clock, suspended = make(tmp_path, ["a"], lambda u: res)
    for _ in range(3):
        st = store.get_state("a")
        if st:
            store.put_state("a", next_due_at=NOW, fail_streak=st["fail_streak"], auth_streak=st["auth_streak"])
        s.tick()
        ex.run_all()
    assert suspended == [("a", "garmin")]


def test_thread_local_released(tmp_path):
    from src.utils import user_context as uc
    seen = []

    def trig(uid):
        uc.set_current_user(uid)
        return ok(uid)
    clock = Clock()
    store = OpsStore(tmp_path / "ops.db", clock=clock)
    ex = DeferredExecutor()
    s = MultiUserScheduler(clock=clock, wait=lambda s: True, executor=ex, rng=random.Random(0),
                           users=lambda: ["a"], trigger=trig, store=store,
                           last_auto_run=lambda u: None, user_interval=lambda u: 4)
    s.tick()
    ex.run_all()
    seen.append(getattr(uc._LOCAL, "user_id", None))
    assert seen == [None]


def test_loop_start_stop(tmp_path):
    ticks = threading.Event()
    s, *_ = make(tmp_path, [], ok)
    s.wait = lambda sec: ticks.set() or s._stop.wait(0.01)
    s.cfg.start_grace_sec = 0
    s.start()
    assert ticks.wait(2)
    s.stop()
    s._thread.join(2)
    assert not s.running()


def test_tick_log_throttled(tmp_path, caplog):
    import logging
    s, *_ = make(tmp_path, [], ok)
    with caplog.at_level(logging.INFO, logger="runpulse.sched"):
        for _ in range(3):
            s._log_tick(s.tick())
    assert sum("tick due=" in r.message for r in caplog.records) == 1

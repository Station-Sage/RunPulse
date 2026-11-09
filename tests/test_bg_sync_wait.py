"""bg_sync_wait(T4) — 가짜 스레드 join, 타임아웃 반환, 서비스 토큰 비차단 실패."""
import threading

import pytest

from src.sync import bg_sync, bg_sync_wait as W


@pytest.fixture(autouse=True)
def _fresh(monkeypatch):
    W.reset_services()
    monkeypatch.setattr(bg_sync, "_threads", {})
    yield
    W.reset_services()


class FakeThread:
    def __init__(self, job_id, alive_joins=0):
        self.job_id, self._left, self.joins = job_id, alive_joins, 0

    def is_alive(self):
        return self._left > 0

    def join(self, timeout=None):
        self.joins += 1
        self._left -= 1


def test_wait_user_joins_until_done():
    t = FakeThread("j1", alive_joins=2)
    bg_sync._threads[("u", "garmin")] = t
    bg_sync._threads[("other", "garmin")] = FakeThread("j1", alive_joins=99)  # 다른 사용자 무시
    res = W.wait_user("u", ["j1"], timeout=60)
    assert res.done and t.joins == 2


def test_wait_user_timeout_returns_pending():
    clock = iter([0.0, 0.0, 100.0, 100.0])
    bg_sync._threads[("u", "strava")] = FakeThread("j2", alive_joins=99)
    res = W.wait_user("u", ["j2"], timeout=10, clock=lambda: next(clock))
    assert not res.done and res.pending == ["j2"]


def test_wait_user_no_threads_is_done():
    assert W.wait_user("u", ["missing"], timeout=1).done


def test_real_thread_join():
    ev = threading.Event()

    class T(threading.Thread):
        job_id = "j3"

        def run(self):
            ev.wait(0.2)
    t = T(daemon=True)
    bg_sync._threads[("u", "intervals")] = t
    t.start()
    assert W.wait_user("u", ["j3"], timeout=5, poll=0.05).done


def test_garmin_slot_global_one_nonblocking():
    assert W.acquire_services(["garmin", "strava"]) == ["garmin", "strava"]
    assert W.acquire_services(["garmin"]) is None          # 전역 1 — 비차단 실패
    assert W.acquire_services(["strava"]) == ["strava"]    # strava 는 2
    assert W.acquire_services(["strava"]) is None
    W.release_services(["garmin"])
    assert W.acquire_services(["garmin"]) == ["garmin"]


def test_acquire_failure_releases_partial():
    W.acquire_services(["strava"])
    W.acquire_services(["strava"])
    assert W.acquire_services(["garmin", "strava"]) is None  # garmin 잡았다가 strava 실패 → garmin 반납
    assert W.acquire_services(["garmin"]) == ["garmin"]


def test_over_release_ignored():
    W.release_services(["runalyze", "runalyze", "runalyze"])
    assert W.acquire_services(["runalyze"]) == ["runalyze"]

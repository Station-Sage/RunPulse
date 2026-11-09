"""bg_sync 완료 대기·서비스 전역 토큰 — 스케줄러가 동기화 스레드 수를 실제로 제한하게 한다(multiuser-sync §3.2·T4).

`wait_user`: start_basic_sync 가 띄운 (사용자, 서비스) 스레드가 끝날 때까지 기다린다(타임아웃 시 즉시 반환, 스레드는 계속).
`acquire_services`/`release_services`: garmin 전역 1, 나머지 2 — 비차단·정렬 순 획득(교착 방지).
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Callable

from src.sync.scheduler_policy import SERVICE_SLOTS

_DEFAULT_SLOTS = 2
_sems: dict[str, threading.BoundedSemaphore] = {}
_sems_lock = threading.Lock()


def _sem(service: str) -> threading.BoundedSemaphore:
    with _sems_lock:
        if service not in _sems:
            _sems[service] = threading.BoundedSemaphore(SERVICE_SLOTS.get(service, _DEFAULT_SLOTS))
        return _sems[service]


def acquire_services(services: list[str]) -> list[str] | None:
    """정렬 순으로 비차단 획득. 하나라도 실패하면 이미 잡은 것을 놓고 None."""
    got: list[str] = []
    for svc in sorted(set(services)):
        if not _sem(svc).acquire(blocking=False):
            release_services(got)
            return None
        got.append(svc)
    return got


def release_services(services: list[str]) -> None:
    for svc in services:
        try:
            _sem(svc).release()
        except ValueError:
            pass  # 과다 반납 — 무시


def reset_services() -> None:
    """테스트용 — 세마포어 초기화."""
    with _sems_lock:
        _sems.clear()


@dataclass
class WaitResult:
    done: bool
    pending: list[str] = field(default_factory=list)   # 타임아웃 시 아직 살아 있는 job_id


def _threads_for(user_id: str, job_ids: list[str]) -> list:
    from src.sync import bg_sync
    wanted = set(job_ids)
    with bg_sync._lock:
        return [t for (uid, _svc), t in bg_sync._threads.items()
                if uid == user_id and getattr(t, "job_id", None) in wanted]


def wait_user(user_id: str, job_ids: list[str], timeout: float,
              clock: Callable[[], float] = time.monotonic, poll: float = 1.0) -> WaitResult:
    """job_ids 스레드가 모두 끝나거나 timeout(초)이 지날 때까지 기다린다.

    join 이 없는 객체는 poll 간격으로 다시 확인한다. clock 은 monotonic 초(테스트 주입).
    """
    deadline = clock() + max(0.0, timeout)
    while True:
        alive = [t for t in _threads_for(user_id, job_ids) if t.is_alive()]
        if not alive:
            return WaitResult(True)
        remaining = deadline - clock()
        if remaining <= 0:
            return WaitResult(False, sorted(getattr(t, "job_id", "") for t in alive))
        t = alive[0]
        join = getattr(t, "join", None)
        if join is not None:
            join(timeout=min(remaining, max(poll, 0.01) * 30))
        else:
            time.sleep(min(remaining, poll))

"""만료된 내보내기 zip 주기 정리 스레드 — 모든 사용자 폴더를 훑는다 (data-export §2.2)."""
from __future__ import annotations

import logging
import threading

from src.services import export_service

log = logging.getLogger(__name__)
INTERVAL_SEC = 6 * 3600
_started = False


def purge_all() -> int:
    """모든 사용자에 대해 purge_expired 실행. 실패는 경고만."""
    from src.utils.user_context import list_user_ids

    n = 0
    for uid in list_user_ids():
        try:
            n += export_service.purge_expired(uid)
        except Exception as e:  # noqa: BLE001
            log.warning("[export_purge] %s 정리 실패: %s", uid, e)
    return n


def _loop(stop: threading.Event, interval: float) -> None:
    while not stop.is_set():
        try:
            purge_all()
        except Exception as e:  # noqa: BLE001
            log.warning("[export_purge] 실패: %s", e)
        stop.wait(interval)


def start(interval: float = INTERVAL_SEC) -> threading.Event | None:
    global _started
    if _started:
        return None
    _started = True
    stop = threading.Event()
    threading.Thread(target=_loop, args=(stop, interval), daemon=True, name="export-purge").start()
    return stop

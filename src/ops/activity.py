"""활동 신호 — 인증된 웹 요청·/mcp Bearer·local-sync 를 uid 별 10분 1회 ops.db 에 기록한다(multiuser-sync §3.4, T2).

캘린더 피드(`/feeds/cal/`)는 캘린더 앱의 자동 폴링이라 제외한다. 기록 실패는 요청을 막지 않는다(로그만).
7일 넘게 쉬었던 사용자가 돌아오면 multi 스케줄러를 poke 해 휴면·저빈도 주기를 즉시 해제한다.
"""
from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Callable

from src.sync.scheduler_policy import SLOW_AFTER_DAYS

log = logging.getLogger("runpulse.sched")

THROTTLE_SEC = 600
EXCLUDED_PREFIXES = ("/feeds/cal/", "/static/")


class ActivityRecorder:
    """uid 별 메모리 스로틀 + ops.db UPSERT. store·clock·monotonic·on_return 주입 가능."""

    def __init__(self, store=None, *, clock: Callable[[], datetime] = datetime.now,
                 monotonic: Callable[[], float] = time.monotonic,
                 on_return: Callable[[str], object] | None = None, throttle_sec: float = THROTTLE_SEC):
        self._store = store
        self.clock, self.monotonic, self.throttle_sec = clock, monotonic, throttle_sec
        self.on_return = on_return
        self._last: dict[str, float] = {}
        self._lock = threading.Lock()

    def store(self):
        if self._store is not None:
            return self._store
        from src.ops.store import default_store
        return default_store()

    def touch(self, uid: str | None) -> bool:
        """기록했으면 True(스로틀·오류로 건너뛰면 False)."""
        if not uid:
            return False
        t = self.monotonic()
        with self._lock:
            last = self._last.get(uid)
            if last is not None and t - last < self.throttle_sec:
                return False
            self._last[uid] = t
            if len(self._last) > 10000:
                self._last = {k: v for k, v in self._last.items() if t - v < self.throttle_sec}
        try:
            now = self.clock()
            prev = self.store().touch_activity(uid, now)
        except Exception:  # noqa: BLE001
            log.warning("활동 신호 기록 실패", exc_info=True)
            return False
        if prev is not None and now - prev > timedelta(days=SLOW_AFTER_DAYS):
            self._returned(uid)
        return True

    def _returned(self, uid: str) -> None:
        try:
            if self.on_return is not None:
                self.on_return(uid)
            else:
                from src.sync.scheduler_run import poke
                poke(uid)
        except Exception:  # noqa: BLE001
            log.warning("스케줄러 poke 실패", exc_info=True)

    def reset(self) -> None:
        with self._lock:
            self._last.clear()


recorder = ActivityRecorder()


def touch(uid: str | None) -> bool:
    """모듈 공용 기록기로 활동 신호 1회."""
    return recorder.touch(uid)


def should_record(path: str) -> bool:
    return not any(path.startswith(p) for p in EXCLUDED_PREFIXES)


def init_activity_hook(app) -> None:
    """before_request — 인증된(active) 세션 사용자의 웹 요청을 활동 신호로 남긴다."""
    from flask import g, request, session

    @app.before_request
    def _record_activity():
        if not should_record(request.path) or getattr(g, "auth_state", "active") != "active":
            return
        uid = session.get("user_id")
        if uid:
            touch(uid)

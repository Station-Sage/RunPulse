"""프로세스 메모리 슬라이딩 윈도 레이트 리미터 (워커 1개 전제)."""
from __future__ import annotations

import threading
import time
from collections import deque

_lock = threading.Lock()
_hits: dict[str, deque] = {}
_MAX_KEYS = 5000


def hit(key: str, limit: int, window_s: float, now: float | None = None) -> bool:
    """기록 후 한도 이내면 True, 초과면 False (초과 시도는 기록하지 않음)."""
    t = time.monotonic() if now is None else now
    with _lock:
        if len(_hits) > _MAX_KEYS:
            for k in [k for k, q in _hits.items() if not q or q[-1] < t - window_s]:
                _hits.pop(k, None)
        q = _hits.setdefault(key, deque())
        while q and q[0] <= t - window_s:
            q.popleft()
        if len(q) >= limit:
            return False
        q.append(t)
        return True


def count(key: str, window_s: float, now: float | None = None) -> int:
    t = time.monotonic() if now is None else now
    with _lock:
        q = _hits.get(key)
        return sum(1 for x in q if x > t - window_s) if q else 0


def reset() -> None:
    with _lock:
        _hits.clear()

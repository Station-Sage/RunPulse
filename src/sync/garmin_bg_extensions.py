"""웹 bg_sync 용 Garmin 일별 확장 동기화 — 훈련 상태·일중 HR(안정시 HR)·레이스 예측·젖산역치.

CLI 경로(garmin.sync_daily_extensions)는 날짜당 9회 호출이라 웹에서는 핵심 4종만, 최근 EXT_RECENT_DAYS 일만 점진 활성화한다.
내부 sync 함수들이 예외를 삼키므로 client 를 가드로 감싸 429 를 감지해 즉시 전파한다.
"""
from __future__ import annotations

import logging
import sqlite3
import time
from datetime import date, timedelta

from src.sync.garmin_daily_extensions import sync_daily_heart_rates, sync_daily_training_status
from src.sync.garmin_ref_sync import sync_lactate_threshold, sync_race_predictions

log = logging.getLogger(__name__)
EXT_RECENT_DAYS = 30
CALL_PAUSE_SEC = 2.0


class _RateLimitGuard:
    """client 호출이 429 를 던지면 기록한다(예외는 그대로 다시 던져 내부 처리 유지)."""

    def __init__(self, client, exc_type: type) -> None:
        self._client = client
        self._exc = exc_type
        self.tripped: Exception | None = None

    def __getattr__(self, name: str):
        attr = getattr(self._client, name)
        if not callable(attr):
            return attr

        def call(*args, **kwargs):
            try:
                return attr(*args, **kwargs)
            except self._exc as exc:
                self.tripped = exc
                raise
        return call


def _429_type() -> type:
    try:
        from garminconnect import GarminConnectTooManyRequestsError
        return GarminConnectTooManyRequestsError
    except ImportError:
        return type(None)


def sync_bg_extensions(
    conn: sqlite3.Connection,
    client,
    win_from: str,
    win_to: str,
    today: date | None = None,
    sleep=time.sleep,
) -> int:
    """창 안의 최근 일자에 확장 4종 동기화. 반환: 시도한 API 호출 수. 429 는 예외로 전파."""
    today = today or date.today()
    guard = _RateLimitGuard(client, _429_type())
    calls = 0

    def step(fn, *args) -> None:
        nonlocal calls
        if calls:
            sleep(CALL_PAUSE_SEC)
        calls += 1
        fn(conn, guard, *args)
        if guard.tripped is not None:
            raise guard.tripped

    end = date.fromisoformat(win_to)
    if end >= today:  # 레이스 예측·LT 는 '최신 스냅샷' 이라 오늘을 포함한 창에서만
        step(sync_race_predictions, today.isoformat())
        step(sync_lactate_threshold, today.isoformat())

    cur = max(date.fromisoformat(win_from), today - timedelta(days=EXT_RECENT_DAYS))
    while cur <= end:
        day = cur.isoformat()
        step(sync_daily_training_status, day)
        step(sync_daily_heart_rates, day)
        cur += timedelta(days=1)
    log.info("[bg_sync] 확장 동기화 %s~%s: API %d회", win_from, win_to, calls)
    return calls

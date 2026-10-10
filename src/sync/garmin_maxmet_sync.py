"""Garmin maxmet/daily 수집 — 일별 VO2max 정밀값을 metric_store(daily/vo2max)에 저장."""
from __future__ import annotations

import logging
import sqlite3
import time
from datetime import date, timedelta

from src.sync.extractors.garmin_extractor import GarminExtractor
from src.sync.extractors.garmin_maxmet_fields import extract_vo2max_daily
from src.sync.garmin_helpers import _store_raw_payload
from src.sync._helpers import save_metrics
from src.utils.metric_priority import resolve_for_scope

log = logging.getLogger(__name__)

WINDOW_DAYS = 365


def _is_429(e: Exception) -> bool:
    s = str(e).lower()
    return "429" in s or "too many requests" in s


def sync_vo2max_range(conn: sqlite3.Connection, client, start: str, end: str) -> int:
    """get_max_metrics_range 1회(구간 ≤ 365일) → raw + metric 저장. 저장한 측정일 수 반환.

    실패해도 sync 를 중단하지 않는다(0 반환). 429 는 RateLimitError 로 올려 호출자가 중단하게 한다.
    """
    try:
        items = client.get_max_metrics_range(start, end)
    except Exception as e:
        if _is_429(e):
            raise
        log.warning("[garmin/maxmet] %s~%s 조회 실패: %s", start, end, e)
        return 0
    by_day = extract_vo2max_daily(GarminExtractor(), items)
    for item in items if isinstance(items, list) else []:
        day = str(((item or {}).get("generic") or {}).get("calendarDate") or "")[:10]
        if day in by_day:
            _store_raw_payload(conn, "maxmet_day", day, item)
    for day, records in by_day.items():
        save_metrics(conn, "daily", day, "garmin", records)
        resolve_for_scope(conn, "daily", day)
    conn.commit()
    return len(by_day)


def backfill_vo2max(conn: sqlite3.Connection, client, start: str, end: str,
                    *, sleep: float = 3.0) -> dict:
    """365일 창으로 나눠 반복. 429 면 중단하고 {'next_start': 재개 시작일} 반환(멱등)."""
    cur, last = date.fromisoformat(start), date.fromisoformat(end)
    saved = 0
    while cur <= last:
        win_end = min(cur + timedelta(days=WINDOW_DAYS - 1), last)
        try:
            saved += sync_vo2max_range(conn, client, cur.isoformat(), win_end.isoformat())
        except Exception as e:
            log.warning("[garmin/maxmet] 429 중단: %s", e)
            return {"saved": saved, "next_start": cur.isoformat()}
        cur = win_end + timedelta(days=1)
        if cur <= last and sleep:
            time.sleep(sleep)
    return {"saved": saved, "next_start": None}

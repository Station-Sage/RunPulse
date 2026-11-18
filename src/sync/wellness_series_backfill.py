"""저장된 Garmin wellness raw payload 로 wellness_series 과거분 채우기 (V2-REPAIR-BACKFILL, Garmin 호출 없음)."""
from __future__ import annotations

import json
import logging
import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from src.sync.wellness_series import RETENTION_DAYS, ingest_day

log = logging.getLogger(__name__)
_TYPES = ("wellness_hrv", "wellness_sleep", "wellness_body_battery", "wellness_stress")


def backfill_series(conn: sqlite3.Connection, days: int = RETENTION_DAYS) -> dict:
    """최근 days 일의 payload → wellness_series. 하루 단위 커밋. {days, rows, errors} 반환."""
    cutoff = (datetime.now(timezone.utc).date() - timedelta(days=days)).isoformat()
    marks = ",".join("?" * len(_TYPES))
    rows = conn.execute(
        f"SELECT entity_date, entity_type, payload FROM source_payloads "
        f"WHERE source='garmin' AND entity_type IN ({marks}) AND entity_date >= ? "
        f"ORDER BY entity_date", (*_TYPES, cutoff)).fetchall()
    by_day: dict[str, dict] = defaultdict(dict)
    for d, t, p in rows:
        by_day[d][t] = json.loads(p)
    stats = {"days": 0, "rows": 0, "errors": 0}
    for d, payloads in by_day.items():
        try:
            stats["rows"] += ingest_day(conn, d, payloads)
            conn.commit()
            stats["days"] += 1
        except Exception as e:  # 하루 실패가 전체를 막지 않음
            conn.rollback()
            log.error("wellness_series backfill %s: %s", d, e)
            stats["errors"] += 1
    return stats

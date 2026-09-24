"""Provider별 데이터 현황 조회 서비스 (읽기 전용).

activity_summaries.source 집계 + source_payloads.fetched_at 최댓값으로
4개 고정 Provider(garmin/strava/intervals/runalyze)의 활동 수·마지막 동기화를 반환한다.
자격증명 확인 없음 — 저장된 데이터 유무만 표기(P3 Provider Transparency, DECISIONS.md [P7-IMPL-PROVIDER-STATUS]).
"""
from __future__ import annotations

import sqlite3

_PROVIDERS = ("garmin", "strava", "intervals", "runalyze")


def get_provider_status(conn: sqlite3.Connection) -> list[dict]:
    """4개 provider별 데이터 현황.

    Returns list(4 items) in fixed order:
        provider      : str
        has_data      : bool  (활동 수 > 0 또는 동기화 기록 존재)
        last_synced_at: str | None  (SQLite UTC datetime 문자열)
        activity_count: int
    """
    try:
        counts: dict[str, int] = {
            r[0]: r[1]
            for r in conn.execute("SELECT source, COUNT(*) FROM activity_summaries GROUP BY source")
        }
        last_synced: dict[str, str | None] = {
            r[0]: r[1]
            for r in conn.execute("SELECT source, MAX(fetched_at) FROM source_payloads GROUP BY source")
        }
    except sqlite3.OperationalError:
        counts, last_synced = {}, {}

    return [
        {
            "provider": p,
            # 웰니스 payload만 있는 provider도 "데이터 있음" — 동기화 기록과 표시가 어긋나지 않게
            "has_data": counts.get(p, 0) > 0 or last_synced.get(p) is not None,
            "last_synced_at": last_synced.get(p),
            "activity_count": counts.get(p, 0),
        }
        for p in _PROVIDERS
    ]

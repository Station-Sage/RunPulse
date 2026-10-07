"""Provider별 데이터 현황 조회 서비스 (읽기 전용).

activity_summaries.source 집계 + source_payloads.fetched_at 최댓값으로
4개 고정 Provider(garmin/strava/intervals/runalyze)의 활동 수·마지막 동기화를 반환한다.
자격증명 확인 없음 — 저장된 데이터 유무만 표기(P3 Provider Transparency, DECISIONS.md [P7-IMPL-PROVIDER-STATUS]).
"""
from __future__ import annotations

import sqlite3

_PROVIDERS = ("garmin", "strava", "intervals", "runalyze")


def _to_iso_utc(value: str | None) -> str | None:
    """SQLite UTC 'YYYY-MM-DD HH:MM:SS' → 오프셋 ISO. 이미 오프셋이 있으면 그대로."""
    if not value:
        return None
    iso = value.replace(" ", "T", 1)
    return iso if ("+" in iso[10:] or iso.endswith("Z")) else iso + "+00:00"


def get_provider_status(conn: sqlite3.Connection) -> list[dict]:
    """4개 provider별 데이터 현황.

    Returns list(4 items) in fixed order:
        provider      : str
        has_data      : bool  (활동 수 > 0 또는 동기화 기록 존재)
        last_new_data_at: str | None  (마지막으로 새 payload가 들어온 시각, 오프셋 ISO `...+00:00`)
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
            "last_new_data_at": _to_iso_utc(last_synced.get(p)),
            "activity_count": counts.get(p, 0),
        }
        for p in _PROVIDERS
    ]


def get_provider_coverage(conn: sqlite3.Connection, start_month: str = "2023-10", today: str | None = None,
                          config: dict | None = None) -> dict:
    """소스별 월 단위 활동 커버리지 — Library 홈 타임라인용.

    반환: {"months": ["2023-10", ..., 이번 달], "providers": [{"provider", "counts": [월별 활동 수], "total", "sync_enabled"}]}
    sync_enabled 는 config.sync_sources 기준(config 없으면 전부 True) — 끈 소스는 화면에서 끊김 경고를 내지 않는다.
    months는 start_month부터 today가 속한 달까지(오름차순). 활동이 없어도 4개 provider 모두 포함(counts 전부 0).
    """
    from datetime import date as _date

    end = _date.fromisoformat(today) if today else _date.today()
    y, m = int(start_month[:4]), int(start_month[5:7])
    months: list[str] = []
    while (y, m) <= (end.year, end.month):
        months.append(f"{y:04d}-{m:02d}")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    idx = {mo: i for i, mo in enumerate(months)}
    from src.utils.config import enabled_sources
    on = enabled_sources(config or {})
    by_src: dict[str, list[int]] = {p: [0] * len(months) for p in _PROVIDERS}
    try:
        rows = conn.execute(
            "SELECT source, substr(start_time, 1, 7) AS mo, COUNT(*) FROM activity_summaries"
            " WHERE start_time IS NOT NULL GROUP BY source, mo"
        ).fetchall()
    except sqlite3.OperationalError:
        rows = []
    for src, mo, n in rows:
        if src in by_src and mo in idx:
            by_src[src][idx[mo]] = n
    return {
        "months": months,
        "providers": [{"provider": p, "counts": by_src[p], "total": sum(by_src[p]), "sync_enabled": p in on}
                      for p in _PROVIDERS],
    }

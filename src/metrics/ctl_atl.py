"""CTL/ATL/TSB 자체 계산 — DailyTRIMP 기반 지수 이동 평균.

Intervals.icu에서 CTL/ATL을 제공하지 않는 과거 데이터를 자체 계산.
기존 Intervals 값이 있으면 그대로 유지, 없는 날짜만 채움.

공식:
  CTL(n) = CTL(n-1) + (TRIMP(n) - CTL(n-1)) / 42
  ATL(n) = ATL(n-1) + (TRIMP(n) - ATL(n-1)) / 7
  TSB(n) = CTL(n) - ATL(n)

저장: daily_fitness (date, source='runpulse', ctl, atl, tsb)
"""
from __future__ import annotations

import logging
import sqlite3
from datetime import date, timedelta

log = logging.getLogger(__name__)


def calc_and_fill_ctl_atl(conn: sqlite3.Connection,
                           start_date: str | None = None,
                           end_date: str | None = None) -> int:
    """DailyTRIMP 기반 CTL/ATL/TSB 계산 → daily_fitness에 저장.

    Intervals.icu 값이 있는 날짜는 스킵.
    없는 날짜만 RunPulse 자체 계산으로 채움.

    Args:
        start_date: 시작일 (None이면 가장 오래된 활동부터).
        end_date: 종료일 (None이면 오늘).

    Returns:
        채운 레코드 수.
    """
    # 날짜 범위 결정
    if not start_date:
        row = conn.execute(
            "SELECT MIN(date) FROM computed_metrics "
            "WHERE metric_name='DailyTRIMP' AND metric_value IS NOT NULL"
        ).fetchone()
        start_date = row[0] if row and row[0] else None
    if not start_date:
        return 0
    if not end_date:
        end_date = date.today().isoformat()

    # 이미 Intervals 값이 있는 날짜
    existing = set()
    rows = conn.execute(
        "SELECT date FROM daily_fitness WHERE source='intervals' "
        "AND ctl IS NOT NULL AND date BETWEEN ? AND ?",
        (start_date, end_date),
    ).fetchall()
    for r in rows:
        existing.add(r[0])

    # DailyTRIMP 시계열 로드
    trimp_rows = conn.execute(
        "SELECT date, metric_value FROM computed_metrics "
        "WHERE metric_name='DailyTRIMP' AND date BETWEEN ? AND ? "
        "ORDER BY date",
        (start_date, end_date),
    ).fetchall()
    trimp_by_date = {r[0]: float(r[1]) if r[1] else 0.0 for r in trimp_rows}

    # 시작 전 CTL/ATL 초기값 (있으면 가져옴)
    prev_day = (date.fromisoformat(start_date) - timedelta(days=1)).isoformat()
    init = conn.execute(
        "SELECT ctl, atl FROM daily_fitness WHERE date=? ORDER BY source DESC LIMIT 1",
        (prev_day,),
    ).fetchone()
    ctl = float(init[0]) if init and init[0] else 0.0
    atl = float(init[1]) if init and init[1] else 0.0

    # 날짜별 순회
    count = 0
    d = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)

    while d <= end:
        d_str = d.isoformat()
        trimp = trimp_by_date.get(d_str, 0.0)

        # EMA 계산
        ctl = ctl + (trimp - ctl) / 42
        atl = atl + (trimp - atl) / 7
        tsb = round(ctl - atl, 2)

        # Intervals 값이 없는 날짜만 저장
        if d_str not in existing:
            try:
                conn.execute(
                    """INSERT INTO daily_fitness (date, source, ctl, atl, tsb)
                       VALUES (?, 'runpulse', ?, ?, ?)
                       ON CONFLICT(date, source) DO UPDATE SET
                           ctl=excluded.ctl, atl=excluded.atl, tsb=excluded.tsb,
                           updated_at=datetime('now')""",
                    (d_str, round(ctl, 2), round(atl, 2), tsb),
                )
                count += 1
            except Exception:
                pass

        d += timedelta(days=1)

    conn.commit()
    log.info("CTL/ATL 자체 계산: %d일 채움 (%s ~ %s)", count, start_date, end_date)
    return count

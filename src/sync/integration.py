"""Phase 3 → Phase 4 통합 지점 (보강 #12).

Sync 완료 후 메트릭 계산을 트리거하는 헬퍼 함수.
"""
from __future__ import annotations

import logging
import sqlite3

log = logging.getLogger(__name__)


def compute_metrics_after_sync(conn: sqlite3.Connection,
                               synced_activity_ids: list[int],
                               affected_dates: list[str] = None) -> dict:
    """
    Sync 완료 후 해당 활동/날짜에 대해 메트릭 계산 실행.

    Parameters:
        conn: DB connection
        synced_activity_ids: sync된 활동 ID 목록
        affected_dates: sync된 활동들의 날짜 목록 (None이면 자동 추출)

    Returns:
        {"activity_result": ComputeResult, "daily_result": ComputeResult}
    """
    from src.metrics.engine import compute_for_activities, compute_for_dates

    results = {}

    # 1. Activity-scope 메트릭
    if synced_activity_ids:
        log.info("Computing activity metrics for %d activities...",
                 len(synced_activity_ids))
        act_result = compute_for_activities(conn, synced_activity_ids)
        log.info("Activity metrics: %s", act_result.summary())
        results["activity_result"] = act_result

        # 2. 영향 받는 날짜 추출
        if affected_dates is None:
            rows = conn.execute(
                "SELECT DISTINCT substr(start_time, 1, 10) FROM activity_summaries "
                "WHERE id IN ({})".format(",".join("?" * len(synced_activity_ids))),
                synced_activity_ids,
            ).fetchall()
            affected_dates = sorted([r[0] for r in rows])

    # 3. Daily-scope 메트릭
    if affected_dates:
        log.info("Computing daily metrics for %d dates...", len(affected_dates))
        daily_result = compute_for_dates(conn, affected_dates)
        log.info("Daily metrics: %s", daily_result.summary())
        results["daily_result"] = daily_result

    return results

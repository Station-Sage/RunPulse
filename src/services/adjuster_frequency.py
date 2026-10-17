"""조정 제안 빈도·수락률 감시와 v2 자동 롤백 판정 (ADR-035 개정, ADJ §3.13).

임계값(주 3건·2주 연속, 최근 N=10, 최소 표본 20)은 제안값이며 구현 S0 에서 확정한다.
"""
from __future__ import annotations

import logging
import sqlite3
from datetime import date, timedelta

from src.services.plan_adjustment_rows import AUTO_SQL
from src.services.user_settings_service import get_setting, set_setting

log = logging.getLogger(__name__)
WEEKLY_MAX = 3
WEEKS_OVER = 2
RECENT_N = 10
MIN_SAMPLE = 20


def weekly_counts(conn: sqlite3.Connection, today: date, weeks: int = WEEKS_OVER) -> list[int]:
    """오래된 주부터 최근 weeks 주의 v3 자동 제안 건수(되돌려진 행 포함)."""
    out = []
    for i in range(weeks, 0, -1):
        end, start = today - timedelta(days=7 * (i - 1)), today - timedelta(days=7 * i - 1)
        out.append(conn.execute(
            f"SELECT COUNT(*) FROM plan_adjustments WHERE source IN ({AUTO_SQL}) AND rule_version='adjuster_v3'"
            " AND date BETWEEN ? AND ?", (start.isoformat(), end.isoformat())).fetchone()[0])
    return out


def _decided(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        f"SELECT decision FROM plan_adjustments WHERE source IN ({AUTO_SQL}) AND rule_version='adjuster_v3'"
        " AND decision IN ('accepted','reverted') ORDER BY date DESC, id DESC").fetchall()
    return [r[0] for r in rows]


def acceptance_drop(conn: sqlite3.Connection) -> bool:
    """최근 N건 수락률이 직전 N건의 절반 미만이면 True. 표본 부족·직전 수락률 0 은 판정하지 않는다."""
    d = _decided(conn)
    if len(d) < MIN_SAMPLE:
        return False
    rate = lambda xs: sum(1 for x in xs if x == "accepted") / len(xs)
    prev = rate(d[RECENT_N:2 * RECENT_N])
    return prev > 0 and rate(d[:RECENT_N]) < prev / 2


def should_rollback(conn: sqlite3.Connection, today: date) -> list[str]:
    """롤백 사유 목록(빈 리스트면 유지)."""
    why = []
    if all(n > WEEKLY_MAX for n in weekly_counts(conn, today)):
        why.append("weekly_over")
    if acceptance_drop(conn):
        why.append("acceptance_drop")
    return why


def check_and_rollback(conn: sqlite3.Connection, today: date) -> list[str]:
    """v3 사용 중일 때만 판정하고, 사유가 있으면 adjuster_version 을 v2 로 되돌린다."""
    if get_setting(conn, "adjuster_version", "v2") != "v3":
        return []
    why = should_rollback(conn, today)
    log.info("adjuster v3 weekly=%s rollback=%s", weekly_counts(conn, today), why)
    if why:
        set_setting(conn, "adjuster_version", "v2")
    return why

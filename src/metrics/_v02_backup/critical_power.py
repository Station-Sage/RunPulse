"""CP/W' (Critical Power / W Prime) — 임계 파워 및 무산소 용량.

2파라미터 모델: P(t) = W'/t + CP
선형 회귀: Work = W' + CP × t → coeffs = polyfit(durations, work, 1)

파워미터 데이터(activity_streams 또는 Intervals power_curve)가 필요.
데이터 없으면 None 반환.

저장: computed_metrics (date, 'CP', value=CP watts, extra_json={w_prime, ...})
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date, timedelta

from src.metrics.store import save_metric


def calc_cp_wprime(powers: list[float], durations: list[float]) -> tuple[float, float] | None:
    """CP와 W' 계산 (2파라미터 선형 회귀).

    Args:
        powers: 각 노력의 평균 파워 (watts).
        durations: 각 노력의 지속 시간 (초).

    Returns:
        (CP, W_prime) 또는 None.
    """
    if len(powers) < 2 or len(durations) < 2:
        return None
    if len(powers) != len(durations):
        return None

    # Work = P × t 계산
    work = [p * t for p, t in zip(powers, durations)]
    n = len(work)

    # 선형 회귀: work = W' + CP × t
    sx = sum(durations)
    sy = sum(work)
    sxx = sum(t * t for t in durations)
    sxy = sum(t * w for t, w in zip(durations, work))
    denom = n * sxx - sx * sx
    if abs(denom) < 1e-10:
        return None

    cp = (n * sxy - sx * sy) / denom
    w_prime = (sy - cp * sx) / n

    if cp <= 0 or w_prime < 0:
        return None

    return round(cp, 1), round(w_prime, 0)


def calc_and_save_cp(conn: sqlite3.Connection, target_date: str) -> float | None:
    """CP/W' 계산 후 저장.

    Intervals.icu power_curve 또는 활동별 파워 데이터에서 추정.

    Returns:
        CP (watts) 또는 None.
    """
    td = date.fromisoformat(target_date)
    start = (td - timedelta(weeks=12)).isoformat()

    # 1. Intervals power_curve에서 시도
    powers, durations = [], []
    rows = conn.execute(
        """SELECT m.metric_json FROM activity_detail_metrics m
           JOIN activity_summaries a ON a.id = m.activity_id
           WHERE m.metric_name='power_curve' AND m.metric_json IS NOT NULL
             AND a.start_time BETWEEN ? AND ?
           ORDER BY a.start_time DESC LIMIT 10""",
        (start, target_date + "T23:59:59"),
    ).fetchall()

    for row in rows:
        try:
            pc = json.loads(row[0]) if isinstance(row[0], str) else row[0]
            if isinstance(pc, dict):
                for t_str, p in pc.items():
                    t = int(t_str)
                    if t >= 120 and p and float(p) > 0:  # 2분 이상
                        durations.append(float(t))
                        powers.append(float(p))
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

    # 2. 활동별 avg_power + duration에서 시도
    if len(powers) < 3:
        act_rows = conn.execute(
            """SELECT avg_power, duration_sec FROM activity_summaries
               WHERE avg_power IS NOT NULL AND avg_power > 0
                 AND duration_sec >= 120
                 AND start_time BETWEEN ? AND ?
               ORDER BY start_time DESC LIMIT 20""",
            (start, target_date + "T23:59:59"),
        ).fetchall()
        for p, t in act_rows:
            powers.append(float(p))
            durations.append(float(t))

    if len(powers) < 3:
        return None

    result = calc_cp_wprime(powers, durations)
    if not result:
        return None

    cp, w_prime = result
    save_metric(conn, target_date, "CP", cp, extra_json={
        "w_prime": w_prime,
        "sample_count": len(powers),
    })
    return cp

"""DI (Durability Index) — 장거리 내구성 지수.

DI(t) = (pace_t / pace_0) / (HR_t / HR_0)
  DI >= 1.0: 후반에도 같은 HR에서 같은 페이스 유지 (이상적)
  DI < 1.0 : 같은 HR이어도 후반 페이스 저하 (내구성 부족)

요약: 최근 8주 90분+ 세션의 DI 평균
최소 데이터: 90분+ 세션 8주간 3회 이상 (미충족 시 None)

[비전-코드 공식 차이] (D-V2-08b 기준, PDF 우선 채택)
  - PDF 원본 (채택): pace/HR 비율법 — DI = (pace_t/pace_0) / (HR_t/HR_0)
    → HR 변화를 반영하여 진정한 내구성 측정 (동일 HR 대비 페이스 유지력)
  - Claude 연구: 페이스 저하율법 — DI = 100 - clamp(pace_drop_pct * 5, 0, 100)
    → HR 무시, 단순 페이스 하락만 측정. 스케일 0-100
  - 핵심 차이: Claude 버전은 HR 컨텍스트 없어 과도한 노력으로 페이스를 유지한 경우를
    내구성 양호로 오판할 수 있음
  비교: v0.2/.ai/metrics.md (PDF) vs v0.2/.ai/metrics_by_claude.md (Claude)
"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from src.metrics.store import save_metric

_MIN_DURATION_SEC = 90 * 60  # 90분
_MIN_SESSIONS = 3
_WEEKS = 8


def calc_di_from_laps(laps: list[dict]) -> float | None:
    """랩 데이터로 DI 계산 (전반 대비 후반 pace/HR 비율).

    Args:
        laps: [{'avg_pace_sec_km': ..., 'avg_hr': ...}, ...].

    Returns:
        DI 값 또는 None.
    """
    valid = [
        lap for lap in laps
        if lap.get("avg_pace_sec_km") and lap.get("avg_hr")
        and lap["avg_pace_sec_km"] > 0 and lap["avg_hr"] > 0
    ]
    if len(valid) < 2:
        return None

    mid = len(valid) // 2
    first = valid[:mid]
    second = valid[mid:]

    pace_0 = sum(lap["avg_pace_sec_km"] for lap in first) / len(first)
    hr_0 = sum(lap["avg_hr"] for lap in first) / len(first)
    pace_t = sum(lap["avg_pace_sec_km"] for lap in second) / len(second)
    hr_t = sum(lap["avg_hr"] for lap in second) / len(second)

    if pace_0 <= 0 or hr_0 <= 0 or hr_t <= 0:
        return None

    # DI = (pace_t/pace_0) / (HR_t/HR_0)
    # pace 증가 = 느려짐, HR 증가 = 더 힘듦
    # DI < 1: 같은 HR 대비 페이스가 더 느려짐 (내구성 부족)
    pace_ratio = pace_t / pace_0
    hr_ratio = hr_t / hr_0
    return pace_ratio / hr_ratio


def calc_di_summary(di_values: list[float]) -> float:
    """여러 세션의 DI 평균.

    Args:
        di_values: 각 세션의 DI 값 리스트.

    Returns:
        평균 DI.
    """
    valid = [v for v in di_values if v > 0]
    if not valid:
        return 0.0
    return sum(valid) / len(valid)


def calc_and_save_di(conn: sqlite3.Connection, target_date: str) -> float | None:
    """DI 계산 후 computed_metrics에 저장.

    최근 8주의 90분+ 세션에서 DI를 계산하고 평균.

    Args:
        conn: SQLite 커넥션.
        target_date: YYYY-MM-DD.

    Returns:
        DI 요약 값 또는 None (데이터 부족).
    """
    td = date.fromisoformat(target_date)
    start_date = (td - timedelta(weeks=_WEEKS)).isoformat()

    # 90분+ 세션 조회
    long_activities = conn.execute(
        """SELECT id FROM v_canonical_activities
           WHERE DATE(start_time) BETWEEN ? AND ?
             AND duration_sec >= ?
             AND activity_type = 'running'
           ORDER BY start_time ASC""",
        (start_date, target_date, _MIN_DURATION_SEC),
    ).fetchall()

    if len(long_activities) < _MIN_SESSIONS:
        return None  # 최소 3회 미충족

    di_values = []
    for (act_id,) in long_activities:
        laps = conn.execute(
            """SELECT avg_pace_sec_km, avg_hr FROM activity_laps
               WHERE activity_id=? ORDER BY lap_index ASC""",
            (act_id,),
        ).fetchall()

        if len(laps) >= 2:
            lap_dicts = [{"avg_pace_sec_km": r[0], "avg_hr": r[1]} for r in laps]
            di = calc_di_from_laps(lap_dicts)
            if di is not None:
                di_values.append(di)

    if len(di_values) < _MIN_SESSIONS:
        return None

    di_summary = calc_di_summary(di_values)
    save_metric(
        conn,
        date=target_date,
        metric_name="DI",
        value=di_summary,
        extra_json={
            "sessions_analyzed": len(di_values),
            "sessions_available": len(long_activities),
            "di_values": [round(v, 3) for v in di_values],
        },
    )
    return di_summary


def get_di(conn: sqlite3.Connection, target_date: str) -> float | None:
    """저장된 DI 값 조회."""
    row = conn.execute(
        """SELECT metric_value FROM computed_metrics
           WHERE metric_name='DI' AND activity_id IS NULL AND date <= ?
           ORDER BY date DESC LIMIT 1""",
        (target_date,),
    ).fetchone()
    return float(row[0]) if row and row[0] is not None else None

"""UTRS (Unified Training Readiness Score) — 통합 훈련 준비도.

UTRS = sleep_score      × 0.25   # Garmin sleep score (0-100)
     + hrv_status       × 0.25   # HRV 정규화 점수 (0-100)
     + tsb_normalized   × 0.20   # TSB 정규화 (TSB -30~+25 → 0~100)
     + resting_hr_score × 0.15   # 안정 심박 역정규화
     + sleep_consistency × 0.15  # 수면 일관성 (7일 편차 역수)

등급: 0-40(휴식), 41-60(경량), 61-80(보통), 81-100(최적)

데이터 없는 요소는 중립값(50)으로 대체 후 available_factors에 기록.
"""
from __future__ import annotations

import math
import sqlite3
from datetime import date, timedelta

from src.metrics.store import save_metric


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def calc_utrs(
    sleep_score: float | None,
    hrv_score: float | None,
    tsb: float | None,
    resting_hr: float | None,
    sleep_start_times_min: list[float] | None,
) -> dict:
    """UTRS 계산 (순수 함수).

    Args:
        sleep_score: Garmin sleep score (0-100). None이면 중립 50 사용.
        hrv_score: HRV 정규화 점수 (0-100). None이면 중립 50 사용.
        tsb: TSB 값 (-30~+25). None이면 중립 0 사용.
        resting_hr: 안정 심박수. None이면 중립 65 사용.
        sleep_start_times_min: 7일간 취침 시각(자정 기준 분). None/빈 리스트면 중립.

    Returns:
        {utrs, sleep, hrv, tsb_norm, rhr, consistency, available_factors}
    """
    available = []

    # sleep_score (0-100)
    if sleep_score is not None:
        s = _clamp(sleep_score, 0, 100)
        available.append("sleep")
    else:
        s = 50.0

    # hrv_status (0-100)
    if hrv_score is not None:
        h = _clamp(hrv_score, 0, 100)
        available.append("hrv")
    else:
        h = 50.0

    # tsb_normalized: TSB -30~+25 → 0~100
    if tsb is not None:
        t = _clamp((tsb + 30) / 55.0 * 100.0, 0, 100)
        available.append("tsb")
    else:
        t = _clamp((0 + 30) / 55.0 * 100.0, 0, 100)  # tsb=0 중립

    # resting_hr_score: 50~80bpm → 100~0
    if resting_hr is not None:
        r = _clamp((80.0 - resting_hr) / 30.0 * 100.0, 0, 100)
        available.append("rhr")
    else:
        r = 50.0

    # sleep_consistency: std(취침 시각) 역수
    if sleep_start_times_min and len(sleep_start_times_min) >= 3:
        n = len(sleep_start_times_min)
        mean_v = sum(sleep_start_times_min) / n
        std_v = math.sqrt(sum((x - mean_v) ** 2 for x in sleep_start_times_min) / n)
        c = _clamp(100.0 - std_v / 60.0 * 20.0, 0, 100)
        available.append("sleep_consistency")
    else:
        c = 50.0

    utrs = s * 0.25 + h * 0.25 + t * 0.20 + r * 0.15 + c * 0.15

    return {
        "utrs": round(utrs, 1),
        "sleep": round(s, 1),
        "hrv": round(h, 1),
        "tsb_norm": round(t, 1),
        "rhr": round(r, 1),
        "consistency": round(c, 1),
        "available_factors": available,
    }


def utrs_grade(utrs: float) -> str:
    """UTRS 등급 분류."""
    if utrs <= 40:
        return "rest"
    if utrs <= 60:
        return "light"
    if utrs <= 80:
        return "moderate"
    return "optimal"


def _get_tsb(conn: sqlite3.Connection, target_date: str) -> float | None:
    """daily_fitness에서 TSB 조회."""
    row = conn.execute(
        """SELECT tsb FROM daily_fitness
           WHERE tsb IS NOT NULL AND date <= ?
           ORDER BY date DESC LIMIT 1""",
        (target_date,),
    ).fetchone()
    return float(row[0]) if row and row[0] is not None else None


def _get_hrv_score(conn: sqlite3.Connection, target_date: str) -> float | None:
    """Garmin HRV 값을 0-100 점수로 정규화.

    hrv_value: 20-100ms 범위를 0-100점으로 변환.
    """
    row = conn.execute(
        """SELECT hrv_value FROM daily_wellness
           WHERE hrv_value IS NOT NULL AND date <= ?
           ORDER BY date DESC LIMIT 1""",
        (target_date,),
    ).fetchone()
    if row is None or row[0] is None:
        return None
    hrv_ms = float(row[0])
    # 20ms=0점, 100ms=100점 선형 정규화
    return _clamp((hrv_ms - 20.0) / 80.0 * 100.0, 0, 100)


def _get_sleep_start_times(conn: sqlite3.Connection, target_date: str) -> list[float]:
    """최근 7일 취침 시각 (분, 자정 기준). daily_wellness에 직접 저장 안 되므로 빈 리스트."""
    # TODO: Garmin sleep session 데이터에서 취침 시각 파싱 시 구현
    # 현재는 빈 리스트 반환 → sleep_consistency 중립값 사용
    return []


def calc_and_save_utrs(conn: sqlite3.Connection, target_date: str) -> float | None:
    """UTRS 계산 후 computed_metrics에 저장.

    Args:
        conn: SQLite 커넥션.
        target_date: YYYY-MM-DD.

    Returns:
        UTRS 값 또는 None.
    """
    # sleep_score
    row = conn.execute(
        """SELECT sleep_score FROM daily_wellness
           WHERE sleep_score IS NOT NULL AND date <= ?
           ORDER BY date DESC LIMIT 1""",
        (target_date,),
    ).fetchone()
    sleep_score = float(row[0]) if row and row[0] is not None else None

    hrv_score = _get_hrv_score(conn, target_date)
    tsb = _get_tsb(conn, target_date)

    row = conn.execute(
        """SELECT resting_hr FROM daily_wellness
           WHERE resting_hr IS NOT NULL AND date <= ?
           ORDER BY date DESC LIMIT 1""",
        (target_date,),
    ).fetchone()
    resting_hr = float(row[0]) if row and row[0] is not None else None

    sleep_starts = _get_sleep_start_times(conn, target_date)

    result = calc_utrs(sleep_score, hrv_score, tsb, resting_hr, sleep_starts)

    save_metric(
        conn,
        date=target_date,
        metric_name="UTRS",
        value=result["utrs"],
        extra_json={**result, "grade": utrs_grade(result["utrs"])},
    )
    return result["utrs"]

"""Garmin 웰니스 데이터 기반 회복 상태 평가."""

import sqlite3
from datetime import date, timedelta


def _score_stress(stress: float | None) -> float | None:
    """스트레스 지수를 0-100 점수로 변환 (낮을수록 좋음).

    25 이하 = 100점, 75 이상 = 0점, 선형 보간.
    """
    if stress is None:
        return None
    stress = max(0.0, min(100.0, float(stress)))
    if stress <= 25:
        return 100.0
    if stress >= 75:
        return 0.0
    return round((75.0 - stress) / 50.0 * 100.0, 1)


def _score_hrv_ratio(hrv: float | None, avg_7d: float | None) -> float | None:
    """HRV를 개인 7일 평균 대비 점수로 변환.

    비율 1.0 = 100점, 0.8 이하 = 0점, 1.2 이상 = 100점 (선형, 클램프).
    """
    if hrv is None or avg_7d is None or avg_7d <= 0:
        return None
    ratio = hrv / avg_7d
    score = (ratio - 0.8) / 0.4 * 100.0
    return round(max(0.0, min(100.0, score)), 1)


def _score_rhr_ratio(rhr: float | None, avg_7d: float | None) -> float | None:
    """안정 심박수를 개인 7일 평균 대비 점수로 변환 (낮을수록 좋음).

    비율 1.0 = 100점, 1.2 이상 = 0점 (선형, 클램프).
    """
    if rhr is None or avg_7d is None or avg_7d <= 0:
        return None
    ratio = rhr / avg_7d
    score = (1.2 - ratio) / 0.2 * 100.0
    return round(max(0.0, min(100.0, score)), 1)


def _get_7d_avg(conn: sqlite3.Connection, date_str: str, field: str) -> float | None:
    """대상 날짜 이전 7일 Garmin 웰니스 필드 평균."""
    end = date_str
    start = (date.fromisoformat(date_str) - timedelta(days=7)).isoformat()
    row = conn.execute(
        f"SELECT AVG({field}) FROM daily_wellness "
        "WHERE date >= ? AND date < ? AND source = 'garmin' AND " + f"{field} IS NOT NULL",
        (start, end),
    ).fetchone()
    return row[0]



def _get_daily_detail_metrics(conn: sqlite3.Connection, date_str: str, source: str = "garmin") -> dict:
    rows = conn.execute(
        "SELECT metric_name, metric_value, metric_json "
        "FROM daily_detail_metrics WHERE date = ? AND source = ?",
        (date_str, source),
    ).fetchall()
    result = {}
    for name, val, js in rows:
        result[name] = js if val is None else val
    return result

def _recovery_grade(score: float) -> str:
    """점수로 회복 등급 판정."""
    if score >= 80:
        return "excellent"
    elif score >= 60:
        return "good"
    elif score >= 40:
        return "moderate"
    else:
        return "poor"


def get_recovery_status(
    conn: sqlite3.Connection,
    date_str: str | None = None,
) -> dict:
    """Garmin 웰니스 기반 회복 상태 평가.

    Args:
        conn: SQLite 연결.
        date_str: 대상 날짜 (ISO 형식). None이면 오늘.

    Returns:
        {"date", "recovery_score" (0-100 or None), "grade", "components",
         "raw", "available"}
    """
    target = date_str or date.today().isoformat()

    row = conn.execute("""
        SELECT body_battery, sleep_score, hrv_value, stress_avg, resting_hr
        FROM daily_wellness
        WHERE date = ? AND source = 'garmin'
        LIMIT 1
    """, (target,)).fetchone()

    if row is None:
        return dict(date=target, recovery_score=None, grade=None,
                    components={}, raw={}, available=False)

    body_battery, sleep_score, hrv_value, stress_avg, resting_hr = row
    detail = _get_daily_detail_metrics(conn, target, source="garmin")

    # 개인 7일 평균 (HRV, RHR 정규화에 사용)
    avg_hrv_7d = _get_7d_avg(conn, target, "hrv_value")
    avg_rhr_7d = _get_7d_avg(conn, target, "resting_hr")

    # 각 지표 점수화
    bb_score = float(body_battery) if body_battery is not None else None
    sl_score = float(sleep_score) if sleep_score is not None else None
    hrv_score = _score_hrv_ratio(hrv_value, avg_hrv_7d)
    stress_score = _score_stress(stress_avg)
    rhr_score = _score_rhr_ratio(resting_hr, avg_rhr_7d)

    components = dict(
        body_battery=bb_score,
        sleep=sl_score,
        hrv=hrv_score,
        stress=stress_score,
        resting_hr=rhr_score,
    )

    # 가중 평균 (사용 가능한 지표만 포함, 가중치 재정규화)
    weights = dict(body_battery=0.30, sleep=0.25, hrv=0.25, stress=0.15, resting_hr=0.05)
    total_w = 0.0
    weighted_sum = 0.0
    for key, w in weights.items():
        val = components[key]
        if val is not None:
            weighted_sum += val * w
            total_w += w

    if total_w == 0:
        recovery_score = None
        grade = None
    else:
        recovery_score = round(weighted_sum / total_w, 1)
        grade = _recovery_grade(recovery_score)

    return dict(
        date=target,
        recovery_score=recovery_score,
        grade=grade,
        components=components,
        raw=dict(
            body_battery=body_battery,
            sleep_score=sleep_score,
            hrv_value=hrv_value,
            stress_avg=stress_avg,
            resting_hr=resting_hr,
        ),
        detail=dict(
            sleep_stage_deep_sec=detail.get("sleep_stage_deep_sec"),
            sleep_stage_rem_sec=detail.get("sleep_stage_rem_sec"),
            sleep_restless_moments=detail.get("sleep_restless_moments"),
            overnight_hrv_avg=detail.get("overnight_hrv_avg"),
            overnight_hrv_sdnn=detail.get("overnight_hrv_sdnn"),
            hrv_baseline_low=detail.get("hrv_baseline_low"),
            hrv_baseline_high=detail.get("hrv_baseline_high"),
            body_battery_delta=detail.get("body_battery_delta"),
            stress_high_duration=detail.get("stress_high_duration"),
            respiration_avg=detail.get("respiration_avg"),
            spo2_avg=detail.get("spo2_avg"),
            training_readiness_score=detail.get("training_readiness_score"),
        ),
        available=True,
    )


def recovery_trend(conn: sqlite3.Connection, days: int = 14) -> dict:
    """N일간 회복 점수 추세 및 방향성 판정.

    Args:
        conn: SQLite 연결.
        days: 조회 일수.

    Returns:
        {"scores": [...], "trend": "improving"|"declining"|"stable"|"unknown", "avg"}
    """
    today = date.today()
    scores = []
    for i in range(days - 1, -1, -1):
        d = (today - timedelta(days=i)).isoformat()
        status = get_recovery_status(conn, d)
        scores.append(dict(date=d, recovery_score=status["recovery_score"],
                           grade=status["grade"]))

    valid = [s["recovery_score"] for s in scores if s["recovery_score"] is not None]

    if len(valid) < 2:
        trend = "unknown"
        avg = valid[0] if valid else None
    else:
        avg = round(sum(valid) / len(valid), 1)
        mid = len(valid) // 2
        first_avg = sum(valid[:mid]) / mid
        second_avg = sum(valid[mid:]) / (len(valid) - mid)
        diff = second_avg - first_avg
        if diff > 5:
            trend = "improving"
        elif diff < -5:
            trend = "declining"
        else:
            trend = "stable"

    return dict(scores=scores, trend=trend, avg=avg)

"""Marathon Shape (Runalyze 방식) — 마라톤 훈련 완성도.

공식:
    target_weekly_km = vdot * 0.8
    target_long_km   = vdot * 0.35
    weekly_shape   = min(1.0, weekly_km_avg / target_weekly_km)
    long_run_shape = min(1.0, longest_run_km / target_long_km)
    shape_pct = (weekly_shape * 2/3 + long_run_shape * 1/3) * 100

기준:
    < 40%:  훈련 부족 (레이스 준비 안 됨)
    40-60%: 기초 훈련
    60-80%: 훈련 진행 중
    80-90%: 충분한 준비
    > 90%:  최적 준비
"""
from __future__ import annotations

import math
import sqlite3
from datetime import date, timedelta

from src.metrics.store import save_metric


def _get_race_targets(vdot: float, race_km: float) -> dict:
    """거리별 목표 — Daniels VDOT 테이블 + Pfitzinger 볼륨 기반."""
    from src.metrics.daniels_table import get_race_volume_targets
    return get_race_volume_targets(vdot, race_km)


def calc_marathon_shape(
    weekly_km_avg: float,
    longest_run_km: float,
    vdot: float,
    consistency_score: float = 0.0,
    race_distance_km: float = 42.195,
    long_run_count: int = 0,
    long_run_quality: float = 0.0,
) -> float | None:
    """Race Shape 계산 — 5요소 종합 준비도.

    Args:
        weekly_km_avg: 최근 N주 평균 주간 거리 (km).
        longest_run_km: 최근 N주 최장 거리 (km).
        vdot: VDOT 값.
        consistency_score: N주 일관성 점수 (0~1).
        race_distance_km: 목표 레이스 거리.
        long_run_count: 기간 내 장거리런 횟수 (threshold 이상).
        long_run_quality: 장거리런 페이스 품질 (0~1). 0이면 미사용.

    Returns:
        Shape 퍼센트 (0~100) 또는 None.
    """
    if not vdot or vdot <= 0:
        return None

    targets = _get_race_targets(vdot, race_distance_km)
    target_weekly = targets["weekly_target"]
    target_long = targets["long_max"]
    target_count = targets["long_count_target"]

    # 1~5 요소 점수 계산
    weekly_score = min(1.0, weekly_km_avg / target_weekly)
    long_score = min(1.0, longest_run_km / target_long)
    freq_score = min(1.0, long_run_count / target_count) if target_count > 0 else 0
    if consistency_score <= 0:
        consistency_score = min(1.0, weekly_km_avg / 4.0 / 8.0) if weekly_km_avg > 0 else 0
    quality = long_run_quality if long_run_quality > 0 else 0.5

    # 거리별 가중치 차등
    #              볼륨  최장  빈도  일관성 페이스품질
    # 10K:  스피드/일관성 중심, 장거리 비중 낮음
    # 하프:  균형
    # 마라톤: 장거리/볼륨 중심
    if race_distance_km <= 10.5:
        w = (0.30, 0.10, 0.10, 0.25, 0.25)  # 10K
    elif race_distance_km <= 21.5:
        w = (0.30, 0.20, 0.15, 0.20, 0.15)  # 하프
    else:
        w = (0.30, 0.25, 0.25, 0.10, 0.10)  # 마라톤

    shape_pct = (
        weekly_score * w[0]
        + long_score * w[1]
        + freq_score * w[2]
        + consistency_score * w[3]
        + quality * w[4]
    ) * 100

    return round(shape_pct, 1)


def marathon_shape_label(shape_pct: float) -> str:
    """Marathon Shape 상태 레이블.

    Returns:
        'insufficient' | 'base' | 'building' | 'ready' | 'peak'
    """
    if shape_pct < 40:
        return "insufficient"
    if shape_pct < 60:
        return "base"
    if shape_pct < 80:
        return "building"
    if shape_pct < 90:
        return "ready"
    return "peak"


def _get_recent_running_data(
    conn: sqlite3.Connection, target_date: str, weeks: int = 4
) -> tuple[float, float]:
    """최근 n주 평균 주간 거리 + 최장 거리 조회.

    Returns:
        (weekly_km_avg, longest_run_km)
    """
    td = date.fromisoformat(target_date)
    start_date = (td - timedelta(weeks=weeks)).isoformat()

    # 최장 거리
    row = conn.execute(
        """SELECT COALESCE(MAX(distance_km), 0)
           FROM v_canonical_activities
           WHERE DATE(start_time) BETWEEN ? AND ?
             AND activity_type = 'running'
             AND distance_km IS NOT NULL""",
        (start_date, target_date),
    ).fetchone()
    longest_km = float(row[0]) if row and row[0] else 0.0

    # 주별 총 거리 → 평균
    row = conn.execute(
        """SELECT COALESCE(SUM(distance_km), 0)
           FROM v_canonical_activities
           WHERE DATE(start_time) BETWEEN ? AND ?
             AND activity_type = 'running'
             AND distance_km IS NOT NULL""",
        (start_date, target_date),
    ).fetchone()
    total_km = float(row[0]) if row and row[0] else 0.0
    weekly_avg = total_km / weeks if weeks > 0 else 0.0

    return weekly_avg, longest_km


def _calc_long_run_stats(conn: sqlite3.Connection, target_date: str,
                         weeks: int = 12, threshold_km: float = 25.0,
                         vdot: float = 50.0) -> tuple[int, float]:
    """장거리런 빈도 + 페이스 품질.

    Args:
        threshold_km: 이 거리 이상이면 "장거리런".
        vdot: E-pace 계산용.

    Returns:
        (long_run_count, quality_score 0~1)
    """
    td = date.fromisoformat(target_date)
    start = (td - timedelta(weeks=weeks)).isoformat()

    rows = conn.execute(
        "SELECT distance_km, duration_sec, avg_pace_sec_km FROM v_canonical_activities "
        "WHERE activity_type='running' AND distance_km>=? "
        "AND DATE(start_time) BETWEEN ? AND ? ORDER BY start_time",
        (threshold_km, start, target_date),
    ).fetchall()

    count = len(rows)
    if count == 0:
        return 0, 0.0

    # 페이스 품질: Daniels E-pace 기준 ±15% 범위 내인지
    from src.metrics.daniels_table import get_training_paces
    paces = get_training_paces(vdot)
    e_pace = paces.get("E", 330)
    pace_low = e_pace * 0.85   # 빠른 한계
    pace_high = e_pace * 1.15  # 느린 한계

    quality_hits = 0
    for dist, dur, pace in rows:
        if pace and pace_low <= float(pace) <= pace_high:
            quality_hits += 1

    quality = quality_hits / count if count > 0 else 0.0
    return count, round(quality, 3)


def _calc_consistency(conn: sqlite3.Connection, target_date: str,
                      weeks: int = 12) -> float:
    """12주 훈련 일관성 점수 (0~1).

    주당 훈련 횟수의 변동계수(CV)가 낮을수록 일관적.
    - 매주 4회 → CV≈0 → 1.0
    - 어떤 주 0회, 어떤 주 7회 → CV 높음 → 0.3
    - 훈련 주 비율도 반영 (12주 중 10주 달림 → 0.83)
    """
    td = date.fromisoformat(target_date)

    weekly_counts: list[int] = []
    for w in range(weeks):
        ws = td - timedelta(weeks=w + 1)
        we = td - timedelta(weeks=w)
        row = conn.execute(
            "SELECT COUNT(*) FROM v_canonical_activities "
            "WHERE activity_type='running' AND DATE(start_time) BETWEEN ? AND ?",
            (ws.isoformat(), we.isoformat()),
        ).fetchone()
        weekly_counts.append(row[0] if row else 0)

    if not weekly_counts:
        return 0.0

    # 훈련 주 비율 (0주 제외)
    active_weeks = sum(1 for c in weekly_counts if c > 0)
    active_ratio = active_weeks / len(weekly_counts)

    # 평균 주당 횟수
    avg = sum(weekly_counts) / len(weekly_counts)
    if avg <= 0:
        return 0.0

    # 변동계수 (CV) — 낮을수록 일관적
    sd = (sum((c - avg) ** 2 for c in weekly_counts) / len(weekly_counts)) ** 0.5
    cv = sd / avg if avg > 0 else 1.0

    # CV → 점수 변환: CV 0=1.0, CV 0.5=0.7, CV 1.0=0.3
    cv_score = max(0.0, 1.0 - cv * 0.7)

    # 최종: 활성 주 비율 × CV 점수 × 주당 평균 횟수 달성도(4회 기준)
    freq_score = min(1.0, avg / 4.0)

    return round(active_ratio * cv_score * freq_score, 3)


def _get_vdot(conn: sqlite3.Connection, target_date: str) -> float | None:
    """해당 날짜의 VDOT 값 조회.

    우선순위: 자체 추정(Jack Daniels) > Runalyze > Garmin VO2Max.
    RunPulse 계산이 최우선. 외부 소스는 참고/fallback.
    """
    # 1. 자체 추정: 최근 best effort로 VDOT 추정
    estimated = _estimate_vdot_from_activities(conn, target_date)
    if estimated is not None:
        return estimated

    # 2. Runalyze VDOT 또는 Garmin VO2Max (fallback)
    row = conn.execute(
        """SELECT runalyze_vdot, garmin_vo2max FROM daily_fitness
           WHERE (runalyze_vdot IS NOT NULL OR garmin_vo2max IS NOT NULL)
           AND date <= ? ORDER BY date DESC LIMIT 1""",
        (target_date,),
    ).fetchone()
    if row:
        if row[0] is not None:
            return float(row[0])
        if row[1] is not None:
            return float(row[1])

    return None


def _vo2_from_velocity(v: float) -> float:
    """Jack Daniels VO2 공식 — 속도(m/min)에서 산소 소비량(ml/kg/min) 추정.

    VO2 = -4.60 + 0.182258·v + 0.000104·v²
    출처: Daniels' Running Formula, 3rd Edition.
    """
    return -4.60 + 0.182258 * v + 0.000104 * v * v


def _pct_vo2max_from_time(t_min: float) -> float:
    """Jack Daniels %VO2max 공식 — 레이스 시간(분)에서 지속 가능 %VO2max.

    %VO2max = 0.8 + 0.1894393·e^(-0.012778·t) + 0.2989558·e^(-0.1932605·t)
    출처: Daniels' Running Formula, 3rd Edition.
    """
    return (0.8
            + 0.1894393 * math.exp(-0.012778 * t_min)
            + 0.2989558 * math.exp(-0.1932605 * t_min))


def estimate_vdot(distance_km: float, duration_sec: float) -> float | None:
    """Jack Daniels VDOT 추정 (정확한 공식).

    VDOT = VO2(v) / %VO2max(t)
    - v = 레이스 속도 (m/min)
    - t = 레이스 시간 (min)

    Args:
        distance_km: 레이스 거리 (km).
        duration_sec: 완주 시간 (초).

    Returns:
        VDOT 추정값 또는 None.
    """
    if distance_km <= 0 or duration_sec <= 0:
        return None

    v = (distance_km * 1000) / (duration_sec / 60)  # m/min
    t_min = duration_sec / 60

    vo2 = _vo2_from_velocity(v)
    pct = _pct_vo2max_from_time(t_min)
    if pct <= 0:
        return None

    vdot = round(vo2 / pct, 1)
    if vdot < 15 or vdot > 90:
        return None
    return vdot


def _estimate_vdot_from_activities(conn: sqlite3.Connection, target_date: str) -> float | None:
    """최근 활동에서 VDOT 추정 — 가중 평균 + 이상치 제거 + HR 검증.

    전문 알고리즘:
    1. 12주 이내 적격 활동 수집 (5K+, 20분+)
    2. HR 검증: 최대심박 75%+ 노력 활동만 (이지런 제외)
    3. 이상치 제거: 중앙값 ±2SD 벗어난 값 제외
    4. 가중 평균: 최신 가중치 ↑ × 장거리 가중치 ↑
    """
    td = date.fromisoformat(target_date)
    start = (td - timedelta(weeks=12)).isoformat()

    # 적격 활동: 5K+ 거리, 20분+ 시간
    rows = conn.execute(
        """SELECT distance_km, duration_sec, avg_hr, max_hr, DATE(start_time)
           FROM v_canonical_activities
           WHERE activity_type='running'
             AND distance_km >= 4.5
             AND duration_sec >= 1200
             AND DATE(start_time) BETWEEN ? AND ?
           ORDER BY start_time DESC""",
        (start, target_date),
    ).fetchall()
    if not rows:
        return None

    # 사용자 최대심박 추정 (이상치 제거)
    from src.metrics.store import estimate_max_hr
    max_hr_est = estimate_max_hr(conn, target_date, weeks=12)

    # 각 활동의 VDOT 계산 + HR 검증
    candidates: list[tuple[float, float, float]] = []  # (vdot, recency_weight, distance_weight)
    for dist_km, dur_sec, avg_hr, max_hr_act, act_date in rows:
        v = estimate_vdot(float(dist_km), float(dur_sec))
        if v is None:
            continue

        # HR 검증: 평균심박이 최대심박의 75% 미만이면 이지런 → VDOT 추정 부적격
        if max_hr_est and avg_hr:
            effort_pct = float(avg_hr) / max_hr_est
            if effort_pct < 0.75:
                continue  # 이지런/회복런 제외

        # 최신 가중치: 12주=84일, 오늘=1.0 → 84일 전=0.3 (지수 감쇠)
        days_ago = (td - date.fromisoformat(act_date)).days
        recency_w = math.exp(-0.014 * days_ago)  # 반감기 ~50일

        # 거리 가중치: 장거리가 더 신뢰도 높음 (5K=1.0, 10K=1.3, 하프=1.5)
        dist_w = min(float(dist_km) / 5.0, 3.0) ** 0.3

        candidates.append((v, recency_w, dist_w))

    if not candidates:
        return None

    # 이상치 제거: 중앙값 ±2SD
    vdots = [c[0] for c in candidates]
    if len(vdots) >= 3:
        vdots_sorted = sorted(vdots)
        median = vdots_sorted[len(vdots_sorted) // 2]
        mean = sum(vdots) / len(vdots)
        sd = (sum((v - mean) ** 2 for v in vdots) / len(vdots)) ** 0.5
        if sd > 0:
            candidates = [c for c in candidates if abs(c[0] - median) <= 2 * sd]

    if not candidates:
        return None

    # 가중 평균
    total_weight = sum(c[1] * c[2] for c in candidates)
    if total_weight <= 0:
        return None
    weighted_vdot = sum(c[0] * c[1] * c[2] for c in candidates) / total_weight

    return round(weighted_vdot, 1)


def calc_and_save_vdot(conn: sqlite3.Connection, target_date: str) -> float | None:
    """VDOT 계산 후 저장. 외부 소스 우선, 없으면 Jack Daniels 추정.

    Returns:
        VDOT 값 또는 None.
    """
    vdot = _get_vdot(conn, target_date)
    if vdot is not None:
        # 소스 판별: 자체 추정이 가능했으면 estimated, 아니면 외부
        estimated = _estimate_vdot_from_activities(conn, target_date)
        if estimated is not None:
            source = "estimated"
        else:
            row = conn.execute(
                "SELECT runalyze_vdot, garmin_vo2max FROM daily_fitness "
                "WHERE (runalyze_vdot IS NOT NULL OR garmin_vo2max IS NOT NULL) "
                "AND date<=? ORDER BY date DESC LIMIT 1",
                (target_date,),
            ).fetchone()
            source = "runalyze" if row and row[0] is not None else (
                "garmin" if row and row[1] is not None else "unknown"
            )
        # 외부 소스 값도 참고로 저장
        ref_runalyze = None
        ref_garmin = None
        ref_row = conn.execute(
            "SELECT runalyze_vdot, garmin_vo2max FROM daily_fitness "
            "WHERE date<=? ORDER BY date DESC LIMIT 1",
            (target_date,),
        ).fetchone()
        if ref_row:
            ref_runalyze = float(ref_row[0]) if ref_row[0] else None
            ref_garmin = float(ref_row[1]) if ref_row[1] else None
        save_metric(
            conn, date=target_date, metric_name="VDOT", value=vdot,
            extra_json={
                "source": source, "vdot": vdot,
                "runalyze_vdot": ref_runalyze, "garmin_vo2max": ref_garmin,
            },
        )
    return vdot


def calc_and_save_marathon_shape(
    conn: sqlite3.Connection, target_date: str
) -> float | None:
    """Marathon Shape 계산 후 computed_metrics에 저장.

    Args:
        conn: SQLite 커넥션.
        target_date: YYYY-MM-DD.

    Returns:
        shape_pct 또는 None.
    """
    vdot = _get_vdot(conn, target_date)
    if vdot is None:
        return None

    # 목표 레이스 거리 (goals 테이블에서)
    race_km = 42.195
    try:
        from src.training.goals import get_active_goal
        goal = get_active_goal(conn)
        if goal and goal.get("distance_km"):
            race_km = float(goal["distance_km"])
    except Exception:
        pass

    targets = _get_race_targets(vdot, race_km)
    consistency_weeks = targets["consistency_weeks"]
    long_threshold = targets["long_threshold"]

    weekly_km_avg, longest_km = _get_recent_running_data(
        conn, target_date, weeks=min(consistency_weeks, 4))
    consistency = _calc_consistency(conn, target_date, weeks=consistency_weeks)

    # 장거리런 빈도: threshold 이상 달린 횟수
    long_count, long_quality = _calc_long_run_stats(
        conn, target_date, weeks=consistency_weeks,
        threshold_km=long_threshold, vdot=vdot)

    shape = calc_marathon_shape(
        weekly_km_avg, longest_km, vdot,
        consistency_score=consistency,
        race_distance_km=race_km,
        long_run_count=long_count,
        long_run_quality=long_quality,
    )
    if shape is not None:
        save_metric(
            conn,
            date=target_date,
            metric_name="MarathonShape",
            value=shape,
            extra_json={
                "label": marathon_shape_label(shape),
                "weekly_km_avg": round(weekly_km_avg, 1),
                "longest_run_km": round(longest_km, 1),
                "vdot": vdot,
                "race_distance_km": race_km,
                "consistency_weeks": consistency_weeks,
                "consistency_score": round(consistency, 3),
                "long_run_count": long_count,
                "long_run_quality": round(long_quality, 2),
                "long_threshold_km": long_threshold,
                "target_weekly_km": round(targets["weekly_target"], 1),
                "target_long_km": round(targets["long_max"], 1),
                "target_long_count": targets["long_count_target"],
            },
        )
    return shape

"""훈련 준비도 분석 + 목표 달성 가능성 예측.

설계 원칙:
  1. VDOT_ADJ 기반 목표 달성 필요 VDOT 역산 (Daniels 공식)
  2. VDOT 주당 향상률 모델 (지수 감소) → 훈련 완료 시 예상 VDOT
  3. DI/EF/FEARP/RTTI 보정 (±10~15%)
  4. 거리별 논문 기반 최솟값/추천 기간 규칙
  5. 기간 단축 시 달성률 페널티

향후 ML 전환 포인트:
  # TODO(v0.4-ML): session_outcomes 50회+ 축적 시 개인화 회귀 모델로 교체
  # - 입력: current_vdot, di, ef, fearp, rtti, weeks_trained
  # - 출력: projected_time_sec, achievability_pct
  # - ref: src/training/replanner.py session_outcomes 스키마 참조

논문 근거:
  - Daniels 2014: VDOT 공식, 훈련 단계
  - Pfitzinger & Douglas 2009: 주간 볼륨 테이블
  - Mujika & Padilla 2003: 테이퍼 기간
  - Foster 1998: 3:1 사이클 (Monotony 근거)
"""
from __future__ import annotations

import math
import sqlite3
from datetime import date, timedelta


# ── 거리별 훈련 기간 규칙 ──────────────────────────────────────────────────

# (min_weeks, optimal_min, optimal_max, taper_weeks)
_DISTANCE_PLAN_RULES: dict[str, tuple[int, int, int, int]] = {
    "1.5k":   (4,  6,  8, 1),
    "3k":     (5,  6,  8, 1),
    "5k":     (6,  8, 10, 1),
    "10k":    (8, 10, 12, 1),
    "half":   (12, 14, 16, 2),
    "full":   (16, 18, 20, 3),
    "custom": (6, 10, 14, 2),
}

# 거리 레이블 → km 변환
_LABEL_TO_KM: dict[str, float] = {
    "1.5k": 1.5,
    "3k":   3.0,
    "5k":   5.0,
    "10k":  10.0,
    "half": 21.097,
    "full": 42.195,
}

# 최솟값 미만 기간 선택 시 달성률 최대값
_BELOW_MIN_PENALTY_CAP = 0.70

# Pfitzinger 주간 볼륨 기준 (거리 레이블 × VDOT 구간 → 기준 주간 km)
# VDOT 구간: [<35, 35~45, 45~55, >55]
_WEEKLY_KM_BASE: dict[str, list[float]] = {
    "1.5k":   [15, 20, 25, 30],
    "3k":     [18, 24, 30, 35],
    "5k":     [25, 35, 45, 55],
    "10k":    [30, 45, 55, 65],
    "half":   [40, 55, 65, 75],
    "full":   [55, 70, 85, 95],
    "custom": [25, 40, 50, 60],
}

# 훈련 단계별 볼륨 배율 (Daniels)
_PHASE_VOLUME_FACTOR: dict[str, float] = {
    "base":  0.85,
    "build": 1.00,
    "peak":  1.05,
    "taper": 0.55,
}


# ── Daniels VDOT 공식 ────────────────────────────────────────────────────

def _vo2_from_velocity(v: float) -> float:
    """속도(m/min) → VO2 (ml/kg/min)."""
    return -4.60 + 0.182258 * v + 0.000104 * v ** 2


def _pct_vo2max(t_min: float) -> float:
    """%VO2max (레이스 지속시간 t분 기준, Daniels 공식)."""
    return (0.8
            + 0.1894393 * math.exp(-0.012778 * t_min)
            + 0.2989558 * math.exp(-0.1932605 * t_min))


def _vdot_from_race(distance_m: float, time_sec: float) -> float | None:
    """거리(m) + 시간(초) → VDOT."""
    if distance_m <= 0 or time_sec <= 0:
        return None
    t_min = time_sec / 60.0
    v = distance_m / t_min
    vo2 = _vo2_from_velocity(v)
    pct = _pct_vo2max(t_min)
    if pct <= 0:
        return None
    return vo2 / pct


def vdot_to_time(vdot: float, distance_m: float,
                 tol_sec: float = 0.5, max_iter: int = 60) -> int | None:
    """VDOT + 거리(m) → 예상 완주 시간(초). 이분탐색."""
    if vdot <= 0 or distance_m <= 0:
        return None
    lo, hi = 60.0, 86400.0  # 1분 ~ 24시간
    for _ in range(max_iter):
        mid = (lo + hi) / 2.0
        est = _vdot_from_race(distance_m, mid)
        if est is None:
            return None
        if abs(est - vdot) < tol_sec / 60.0:
            break
        if est > vdot:
            lo = mid
        else:
            hi = mid
    return int((lo + hi) / 2.0)


# ── 메트릭 로드 헬퍼 ─────────────────────────────────────────────────────

def _get_recent_metric(conn: sqlite3.Connection, name: str,
                       days_back: int = 14) -> float | None:
    """computed_metrics에서 최근 N일 내 가장 최근 값 조회."""
    since = (date.today() - timedelta(days=days_back)).isoformat()
    today = date.today().isoformat()
    row = conn.execute(
        "SELECT metric_value FROM computed_metrics "
        "WHERE metric_name=? AND date<=? AND date>=? AND metric_value IS NOT NULL "
        "AND activity_id IS NULL "
        "ORDER BY date DESC LIMIT 1",
        (name, today, since),
    ).fetchone()
    return row[0] if row else None


def _get_recent_activity_metric(conn: sqlite3.Connection, name: str,
                                 days_back: int = 30) -> float | None:
    """활동 레벨 메트릭의 최근 N일 평균."""
    since = (date.today() - timedelta(days=days_back)).isoformat()
    today = date.today().isoformat()
    row = conn.execute(
        "SELECT AVG(metric_value) FROM computed_metrics "
        "WHERE metric_name=? AND date<=? AND date>=? AND metric_value IS NOT NULL "
        "AND activity_id IS NOT NULL",
        (name, today, since),
    ).fetchone()
    return row[0] if (row and row[0] is not None) else None


# ── 거리별 규칙 헬퍼 ─────────────────────────────────────────────────────

def _label_from_km(distance_km: float) -> str:
    """거리(km) → 가장 가까운 레이블."""
    if distance_km <= 2.0:   return "1.5k"
    if distance_km <= 4.0:   return "3k"
    if distance_km <= 7.5:   return "5k"
    if distance_km <= 15.0:  return "10k"
    if distance_km <= 30.0:  return "half"
    if distance_km <= 50.0:  return "full"
    return "custom"


def get_taper_weeks(distance_km: float) -> int:
    """거리 기반 테이퍼 기간(주) 반환.

    Args:
        distance_km: 목표 레이스 거리 (km).

    Returns:
        테이퍼 기간 (주). 5K/10K=1, Half=2, Full=3.
    """
    label = _label_from_km(distance_km)
    return _DISTANCE_PLAN_RULES.get(label, (6, 10, 14, 2))[3]


def get_recommended_weeks(distance_km: float) -> dict[str, int]:
    """거리 기반 추천 훈련 기간 반환.

    Args:
        distance_km: 목표 레이스 거리 (km).

    Returns:
        {"min": int, "optimal_min": int, "optimal_max": int, "taper": int}
    """
    label = _label_from_km(distance_km)
    mn, opt_min, opt_max, taper = _DISTANCE_PLAN_RULES.get(label, (6, 10, 14, 2))
    return {"min": mn, "optimal_min": opt_min, "optimal_max": opt_max, "taper": taper}


# ── 주간 km 추천 ─────────────────────────────────────────────────────────

def recommend_weekly_km(
    current_vdot: float,
    distance_label: str,
    phase: str,
    week_index: int,
    total_weeks: int,
) -> float:
    """Pfitzinger 볼륨 테이블 + VDOT 보정 주간 km 추천.

    Args:
        current_vdot: 현재 VDOT_ADJ.
        distance_label: 목표 거리 레이블.
        phase: 'base' | 'build' | 'peak' | 'taper'.
        week_index: 0-based 현재 주차.
        total_weeks: 전체 훈련 기간 (주).

    Returns:
        추천 주간 km.
    """
    bases = _WEEKLY_KM_BASE.get(distance_label, _WEEKLY_KM_BASE["custom"])

    if current_vdot < 35:   base_km = bases[0]
    elif current_vdot < 45: base_km = bases[1]
    elif current_vdot < 55: base_km = bases[2]
    else:                    base_km = bases[3]

    phase_factor = _PHASE_VOLUME_FACTOR.get(phase, 1.0)

    # 3:1 사이클 (Foster 1998): 4주 주기에서 4번째 주는 -20% 회복주
    cycle_pos = week_index % 4
    cycle_factor = 0.80 if cycle_pos == 3 else 1.0

    return round(base_km * phase_factor * cycle_factor, 1)


def get_phase_for_week(week_index: int, total_weeks: int,
                       taper_weeks: int) -> str:
    """주차 인덱스 → 훈련 단계.

    Args:
        week_index: 0-based.
        total_weeks: 전체 훈련 기간.
        taper_weeks: 테이퍼 기간.

    Returns:
        'base' | 'build' | 'peak' | 'taper'
    """
    training_weeks = total_weeks - taper_weeks
    if week_index >= total_weeks - taper_weeks:
        return "taper"
    base_end = int(training_weeks * 0.40)
    build_end = int(training_weeks * 0.75)
    if week_index < base_end:
        return "base"
    if week_index < build_end:
        return "build"
    return "peak"


# ── 핵심 분석 함수 ──────────────────────────────────────────────────────

def analyze_readiness(
    conn: sqlite3.Connection,
    goal_distance_km: float,
    goal_time_sec: int,
    target_weeks: int,
) -> dict:
    """현재 훈련 상태를 분석하여 목표 달성 가능성 추정.

    Args:
        conn: SQLite 연결.
        goal_distance_km: 목표 레이스 거리 (km).
        goal_time_sec: 목표 완주 시간 (초).
        target_weeks: 사용자 선택 훈련 기간 (주).

    Returns:
        dict with keys:
          achievability_pct  : float (0~100)
          recommended_weeks  : dict {min, optimal_min, optimal_max, taper}
          projected_time_now : int | None  (현재 페이스 유지 시 예상 기록, 초)
          projected_time_end : int | None  (훈련 완료 시 예상 기록, 초)
          required_vdot      : float | None
          current_vdot       : float | None
          vdot_gap           : float | None
          weekly_vdot_gain   : float
          status_summary     : str
          warnings           : list[str]
    """
    warnings: list[str] = []
    rec = get_recommended_weeks(goal_distance_km)
    distance_m = goal_distance_km * 1000.0

    # ── 1. 필요 VDOT 계산 ──────────────────────────────────────────────
    required_vdot = _vdot_from_race(distance_m, goal_time_sec)

    # ── 2. 현재 VDOT_ADJ 로드 ──────────────────────────────────────────
    current_vdot = _get_recent_metric(conn, "VDOT_ADJ", days_back=30)

    # ── 3. 보조 메트릭 로드 ────────────────────────────────────────────
    di_val   = _get_recent_metric(conn, "DI",   days_back=14)
    rtti_val = _get_recent_metric(conn, "RTTI", days_back=7)
    ef_val   = _get_recent_activity_metric(conn, "EF",    days_back=30)
    fearp_val = _get_recent_activity_metric(conn, "FEARP", days_back=30)

    # ── 4. 현재 기준 예상 기록 ─────────────────────────────────────────
    projected_time_now: int | None = None
    if current_vdot and current_vdot > 0:
        projected_time_now = vdot_to_time(current_vdot, distance_m)

    # ── 5. VDOT 성장 모델 ──────────────────────────────────────────────
    # VDOT는 레이스 퍼포먼스 기반 → VO2max 향상만이 아님:
    #   VO2max 향상 + 러닝 경제성(RE) + 젖산역치(LT) 향상을 모두 반영
    #   - Saunders et al. 2004: 훈련된 러너 RE 2~8% 향상 가능
    #   - Coyle et al. 1988: LT는 VO2max 독립적으로 향상
    #   - Daniels 코칭 관찰: 적절한 훈련 사이클 3~5 VDOT 향상
    #
    # [역산 근거 sum(e^(-0.05w), w=0..15) ≈ 11.28]:
    #   VDOT < 30:  VO2max 15% + RE 5% + LT 3% ≈ 23% → 16주 ~7 VDOT → 0.65
    #   VDOT 30~40: VO2max 10% + RE 4% + LT 3% ≈ 17% → 16주 ~4 VDOT → 0.40
    #   VDOT 40~50: VO2max  7% + RE 3% + LT 3% ≈ 13% → 16주 ~3 VDOT → 0.27
    #   VDOT 50~60: VO2max  3% + RE 2% + LT 2% ≈  7% → 16주 ~1.5 VDOT → 0.14
    #   VDOT 60+:   VO2max 1.5%+ RE 1% + LT 1% ≈ 3.5%→ 16주 ~0.8 VDOT → 0.07
    # TODO(v0.4-ML): session_outcomes 50회+ 축적 시 개인화 회귀 모델로 교체
    _cv = current_vdot or 40.0
    if _cv < 30:       base_gain = 0.65
    elif _cv < 40:     base_gain = 0.40
    elif _cv < 50:     base_gain = 0.27   # ≈ 3.0 VDOT/16주 (VO2max+RE+LT 합산)
    elif _cv < 60:     base_gain = 0.14
    else:              base_gain = 0.07

    decay_k = 0.05  # 주별 적응 감소율 (지수 모델)
    total_gain = sum(
        base_gain * math.exp(-decay_k * w)
        for w in range(target_weeks)
    )
    weekly_vdot_gain = total_gain / target_weeks if target_weeks > 0 else base_gain

    # ── 6. 보조 메트릭 보정계수 ────────────────────────────────────────
    correction = 1.0

    if di_val is not None:
        # DI < 40 → 지구력 부족, 성장률 -10%
        if di_val < 40:
            correction -= 0.10
            warnings.append("DI 지수가 낮습니다 — 롱런 비중을 늘리세요.")
        elif di_val >= 70:
            correction += 0.05

    if rtti_val is not None:
        # RTTI > 110 → 과훈련 위험, 성장률 -10%
        if rtti_val > 110:
            correction -= 0.10
            warnings.append("훈련 강도가 높습니다 (RTTI > 110) — 회복주를 고려하세요.")
        elif rtti_val < 60:
            correction -= 0.05
            warnings.append("훈련 부하가 낮습니다 (RTTI < 60) — 볼륨을 점진적으로 늘리세요.")

    if ef_val is not None and ef_val < 1.0:
        # EF 낮음 → 효율성 부족
        correction -= 0.05

    if fearp_val is not None and fearp_val > 0:
        # FEARP는 sec/km, 낮을수록 빠름 — 현재 vdot과 비교해 개선 여부 확인
        # 단순 보정: FEARP가 목표 페이스보다 크게 느리면 -5%
        goal_pace = goal_time_sec / goal_distance_km if goal_distance_km > 0 else 0
        if goal_pace > 0 and fearp_val > goal_pace * 1.15:
            correction -= 0.05

    correction = max(0.70, min(1.20, correction))  # 0.7~1.2 범위 클램프

    # ── 7. 기간 단축 페널티 ────────────────────────────────────────────
    below_min = target_weeks < rec["min"]
    shortfall_ratio = 1.0
    if below_min:
        shortfall_ratio = target_weeks / rec["min"]
        warnings.append(
            f"선택 기간({target_weeks}주)이 {goal_distance_km:.0f}km 권장 최솟값"
            f"({rec['min']}주)보다 짧습니다."
        )

    # ── 8. 훈련 완료 시 예상 VDOT ─────────────────────────────────────
    projected_time_end: int | None = None
    achievability_pct: float = 0.0

    if current_vdot and required_vdot:
        projected_vdot = current_vdot + total_gain * correction * shortfall_ratio
        projected_time_end = vdot_to_time(projected_vdot, distance_m)

        if projected_vdot >= required_vdot:
            achievability_pct = 100.0
        else:
            ratio = projected_vdot / required_vdot
            achievability_pct = min(100.0, 100.0 * (ratio ** 2))

        if below_min:
            achievability_pct = min(achievability_pct, _BELOW_MIN_PENALTY_CAP * 100)
    elif current_vdot is None:
        warnings.append("VDOT 데이터가 없습니다. 먼저 동기화하세요.")

    # ── 9. 상태 해설 ──────────────────────────────────────────────────
    vdot_gap = (required_vdot - current_vdot) if (required_vdot and current_vdot) else None
    status_summary = _build_status_summary(
        achievability_pct, vdot_gap, di_val, rtti_val, ef_val, target_weeks, rec
    )

    return {
        "achievability_pct":  round(achievability_pct, 1),
        "recommended_weeks":  rec,
        "projected_time_now": projected_time_now,
        "projected_time_end": projected_time_end,
        "required_vdot":      round(required_vdot, 1) if required_vdot else None,
        "current_vdot":       round(current_vdot, 1) if current_vdot else None,
        "vdot_gap":           round(vdot_gap, 1) if vdot_gap else None,
        "weekly_vdot_gain":   round(weekly_vdot_gain, 2),
        "status_summary":     status_summary,
        "warnings":           warnings,
    }


def _build_status_summary(
    achievability_pct: float,
    vdot_gap: float | None,
    di_val: float | None,
    rtti_val: float | None,
    ef_val: float | None,
    target_weeks: int,
    rec: dict,
) -> str:
    """달성 가능률 + 보조 지표를 한국어 해설로 변환."""
    lines: list[str] = []

    if achievability_pct >= 85:
        lines.append("현재 상태로 목표 달성 가능성이 높습니다.")
    elif achievability_pct >= 60:
        lines.append("꾸준히 훈련하면 목표에 근접할 수 있습니다.")
    elif achievability_pct >= 40:
        lines.append("목표가 도전적입니다. 훈련 기간 연장 또는 목표 조정을 권장합니다.")
    else:
        lines.append("현재 상태에서 목표 달성은 어렵습니다. 기간 연장이나 목표 하향을 고려하세요.")

    if vdot_gap is not None:
        if vdot_gap <= 0:
            lines.append("VDOT 기준으로 이미 목표 수준에 도달했습니다.")
        elif vdot_gap <= 2:
            lines.append(f"VDOT {vdot_gap:.1f} 향상이 필요합니다 — 충분히 달성 가능한 범위입니다.")
        elif vdot_gap <= 5:
            lines.append(f"VDOT {vdot_gap:.1f} 향상이 필요합니다 — 집중 훈련이 필요합니다.")
        else:
            lines.append(f"VDOT {vdot_gap:.1f} 향상이 필요합니다 — 장기적 플랜을 권장합니다.")

    if di_val is not None and di_val < 40:
        lines.append("지구력(DI)이 낮습니다 — 주간 롱런 비중을 늘려야 합니다.")

    if rtti_val is not None and rtti_val > 110:
        lines.append("현재 훈련 부하가 높습니다 — 충분한 회복을 취하세요.")

    if target_weeks < rec["optimal_min"]:
        lines.append(
            f"훈련 기간이 최적값({rec['optimal_min']}~{rec['optimal_max']}주)보다 짧습니다."
        )

    return " ".join(lines)

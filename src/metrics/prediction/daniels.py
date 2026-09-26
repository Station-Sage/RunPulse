"""Daniels–Gilbert VDOT 공식과 강도 구간(E/M/T/I/R) 역산 — 표가 아니라 공식으로 계산한다(순수 함수).

근거(REVIEW-09 §2):
  산소 비용  VO2(v) = −4.60 + 0.182258·v + 0.000104·v²          (v: m/min)
  지속 비율  %VO2max(t) = 0.8 + 0.1894393·e^(−0.012778·t) + 0.2989558·e^(−0.1932605·t)   (t: 분)
  VDOT = VO2(d/t) / %VO2max(t)  — 저장소 `src/utils/daniels_table.get_race_predictions`·`training/readiness.py` 와 같은 식.
강도 구간(식으로 정의, 원표 대조는 P7-PRED-99 TODO):
  M = 마라톤 레이스 속도, T = 60분 레이스 속도(%VO2max 0.888), I = VO2max 속도(%VO2max 1.0 ≈ 11.0분 레이스),
  R = 1마일 레이스 속도, E = %VO2max 0.59~0.74 [가정].
세트 등가 지속시간(REVIEW-09 §3): 휴식/작업 비 ρ 가 T 처방(0.2) 이하면 60분, I 처방(1.0) 이상이면 11.03분,
  그 사이는 ln ρ 에 대해 로그-선형 보간. 짧은 반복(≤150초)에 ρ ≥ 1.5 면 R(마일), 40분 이상 연속이면 M.
"""
from __future__ import annotations

import math

MILE_M = 1609.344
MARATHON_M = 42195.0
T_MIN = 60.0                 # T = 60분 레이스 강도
I_MIN = 11.03                # %VO2max(t) = 1.0 이 되는 t(분) — i_minutes() 로 검증
RHO_T = 0.2                  # T 크루즈 처방 휴식/작업 비(5분 작업당 1분 휴식) [가정: 원문 확인 필요]
RHO_I = 1.0                  # I 처방 휴식/작업 비(작업 시간과 같거나 짧게) [가정: 원문 확인 필요]
R_MAX_REP_S = 150.0          # R 반복 길이 상한(초)
R_MIN_RHO = 1.5              # R 휴식/작업 비 하한(원문 2~3배 [가정]의 하단보다 낮춰 오차 흡수)
CONT_MIN_S = 480.0           # 연속 작업 T 최소(8분)
M_MIN_S = 2400.0             # 연속 작업 M 최소(40분)
E_PCT = (0.59, 0.74)         # E 강도 %VO2max 범위 [가정: 원문 확인 필요]


def vo2_cost(v_m_min: float) -> float:
    return -4.60 + 0.182258 * v_m_min + 0.000104 * v_m_min * v_m_min


def pct_vo2max(t_min: float) -> float:
    return 0.8 + 0.1894393 * math.exp(-0.012778 * t_min) + 0.2989558 * math.exp(-0.1932605 * t_min)


def speed_for_vo2(vo2: float) -> float:
    """VO2(ml/kg/min) → 속도(m/s). vo2_cost 의 역함수."""
    a, b, c = 0.000104, 0.182258, -4.60 - vo2
    return (-b + math.sqrt(b * b - 4 * a * c)) / (2 * a) / 60.0


def vdot(dist_m: float, time_s: float) -> float:
    tm = time_s / 60.0
    return vo2_cost(dist_m / tm) / pct_vo2max(tm)


def time_for_vdot(vd: float, dist_m: float) -> float:
    """VDOT·거리 → 레이스 시간(s). 이분법."""
    lo, hi = 60.0, 60000.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if vdot(dist_m, mid) > vd:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def i_minutes() -> float:
    """%VO2max(t) = 1 인 t(분). 상수 I_MIN 검증용."""
    lo, hi = 5.0, 20.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if pct_vo2max(mid) > 1.0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def zone_speeds(vd: float) -> dict[str, float]:
    """VDOT → 구간 속도(m/s). E 는 (느린, 빠른) 범위."""
    return {"E": (speed_for_vo2(vd * E_PCT[0]), speed_for_vo2(vd * E_PCT[1])),
            "M": MARATHON_M / time_for_vdot(vd, MARATHON_M),
            "T": speed_for_vo2(vd * pct_vo2max(T_MIN)),
            "I": speed_for_vo2(vd),
            "R": MILE_M / time_for_vdot(vd, MILE_M)}


def threshold_speed(vd: float) -> float:
    """VDOT → T 속도(m/s) = 60분 레이스 속도."""
    return speed_for_vo2(vd * pct_vo2max(T_MIN))


def equivalent_minutes(n_reps: int, rho: float) -> float:
    """세트 등가 지속시간(분). 연속(1회)이면 T 60분, ρ≤0.2 → 60, ρ≥1.0 → 11.03, 사이는 ln ρ 로그-선형."""
    if n_reps <= 1 or rho <= RHO_T:
        return T_MIN
    if rho >= RHO_I:
        return I_MIN
    s = math.log(rho / RHO_T) / math.log(RHO_I / RHO_T)
    return math.exp(math.log(T_MIN) + (math.log(I_MIN) - math.log(T_MIN)) * s)


def set_zone(n_reps: int, rep_s: float, rho: float, work_s: float) -> str | None:
    """세트 구조 → 구간(R/I/T/M) — 평균 HR·목표 페이스 없이 구조만 본다. 해당 없으면 None."""
    if n_reps <= 1:
        if work_s >= M_MIN_S:
            return "M"
        return "T" if work_s >= CONT_MIN_S else None
    if rep_s <= R_MAX_REP_S and rho >= R_MIN_RHO:
        return "R"
    if work_s < CONT_MIN_S:
        return None
    return "I" if rho >= math.sqrt(RHO_T * RHO_I) else "T"     # 라벨 경계 = 두 처방의 기하 중간(0.447)


def set_vdot(zone: str, speed_ms: float, n_reps: int, rho: float) -> float:
    """구간별 속도 → VDOT. T/I 는 등가 지속시간, R 은 1마일 레이스, M 은 마라톤 레이스로 역산."""
    if zone == "R":
        return vdot(MILE_M, MILE_M / speed_ms)
    if zone == "M":
        return vdot(MARATHON_M, MARATHON_M / speed_ms)
    return vo2_cost(speed_ms * 60.0) / pct_vo2max(equivalent_minutes(n_reps, rho))

"""레이스 예측 r4 순수 계산 — 기온 환산, 개인 지구력 지수 k, 거리 외삽, 칼만 결합 결과의 범위·신뢰도, 마라톤 Tanda 결합.

DB·CalcContext 무의존. 속도 m/s, 시간 s, 거리 m. 상수 근거 등급은 REVIEW-09 §5~7((a) 문헌 (b) 데이터 (c) 휴리스틱).
"""
from __future__ import annotations

import math

from src.metrics.prediction.daniels import threshold_speed, time_for_vdot, vdot  # noqa: F401  (재노출)

Q_PER_DAY = 0.01         # (c) 체력 랜덤워크 하루 분산(VDOT²). 데이터로 식별 안 됨(0.001~0.1), 민감도 REVIEW-07 §R4-3
SIGMA_RACE = 1.0         # (b) 전력 대회 관측 SD(VDOT) — 전 관측 MLE
SIGMA_SET = 1.75         # (b) 품질 세트 관측 SD — 전 관측 MLE, 최근접 대회 잔차 SD 1.90
SIGMA_H = 1.25           # (b) 심박-속도 H 관측 SD — D-0 잔차 1.58² − 1.0²
HR_REACH_REF = 0.92      # (c) 세트 후반 최대 HR/HRmax 기준. 미달분 1%p당 분산 배율 e^0.36
HR_REACH_SLOPE = 0.36    # (b, 약함) 로그-분산 회귀 0.36 ± 0.20 (n=39)
RIEGEL_K0 = 1.06         # (a) Riegel
RIEGEL_TAU = 0.03        # (c) 개인 k 사전 SD
TANDA_SIGMA = 0.04       # (c) Tanda 식의 ln 시간 SD
ASYM_LOW_MULT = {"race": 4.0, "set": 4.0}   # (c) 섀도 변형: 현재 추정보다 낮은 관측의 분산 배율
MAINT_ALPHA = 0.14       # (a 가정) 유지 조건부 앵커: Daniels 휴식 표 4주 ≈ VDOT 93% ↔ CTL 51% → 0.07/0.49
CONF_BAND = 0.03         # 신뢰도 정의: 실제 기록이 예측 ±3% 안에 들 확률
Z80 = 1.2816             # (a) 정규 80% 구간


def temp_factor(temp_c: float | None, heat_pct_per_c: float, cold_pct_per_c: float) -> float:
    """기온 T에서의 속도 배율(15℃=1). heat/cold 는 음수 %/℃."""
    if temp_c is None:
        return 1.0
    return 1.0 + (heat_pct_per_c * max(0.0, temp_c - 15.0) + cold_pct_per_c * max(0.0, 5.0 - temp_c)) / 100.0


def vdot_at_15c(dist_m: float, time_s: float, temp_c: float | None, heat: float, cold: float) -> float:
    return vdot(dist_m, time_s * temp_factor(temp_c, heat, cold))


def time_at_temp(vd15: float, dist_m: float, temp_c: float | None, heat: float, cold: float) -> float:
    return time_for_vdot(vd15, dist_m) / temp_factor(temp_c, heat, cold)


def dlnt_dvdot(vd: float, dist_m: float) -> float:
    """VDOT 1 증가당 ln(시간) 감소량(양수)."""
    return math.log(time_for_vdot(vd - 0.5, dist_m) / time_for_vdot(vd + 0.5, dist_m))


def k_personal(races: list[dict], q: float = Q_PER_DAY) -> tuple[float, float, int]:
    """races: [{"nominal_m","vdot15","day"(정수 일)}] 전력 대회. 거리가 다른 겹치지 않는 쌍(간격 가까운 순)으로
    사전 N(1.06, 0.03²)을 역분산 갱신. 반환 (k, sd, 사용 쌍 수)."""
    cand = sorted((abs(a["day"] - b["day"]), i, j) for i, a in enumerate(races) for j, b in enumerate(races)
                  if i < j and a["nominal_m"] != b["nominal_m"])
    num, den, used, taken = RIEGEL_K0 / RIEGEL_TAU ** 2, 1.0 / RIEGEL_TAU ** 2, 0, set()
    for gap, i, j in cand:
        if i in taken or j in taken:
            continue
        s, l = sorted((races[i], races[j]), key=lambda r: r["nominal_m"])
        lr = math.log(l["nominal_m"] / s["nominal_m"])
        k = math.log(time_for_vdot(l["vdot15"], l["nominal_m"]) / time_for_vdot(s["vdot15"], s["nominal_m"])) / lr
        if not 0.95 <= k <= 1.25:
            continue
        e = dlnt_dvdot((s["vdot15"] + l["vdot15"]) / 2, l["nominal_m"])
        sk = e * math.sqrt(2 * SIGMA_RACE ** 2 + q * gap) / lr
        num += k / sk ** 2
        den += 1.0 / sk ** 2
        used += 1
        taken |= {i, j}
    return num / den, (1.0 / den) ** 0.5, used


def to_target(y: float, d_native: float, d: float, k: float, k_sd: float) -> tuple[float, float]:
    """고유 거리 d_native 의 VDOT y → 목표 거리 d 의 VDOT 와 외삽 추가 분산(k 불확실성)."""
    t = time_for_vdot(y, d) * (d / d_native) ** (k - RIEGEL_K0)
    yt = vdot(d, t)
    return yt, (k_sd * abs(math.log(d / d_native)) / dlnt_dvdot(yt, d)) ** 2


def longrun_k_sd(k_sd: float, d: float, d_native: float, longest_m: float | None) -> float:
    """목표 거리가 최근 최장 러닝보다 길면 그 외삽분에 사전 SD 를 더한 k SD(REVIEW-09 §7)."""
    if not longest_m or d <= longest_m or d <= d_native:
        return k_sd
    frac = math.log(d / longest_m) / math.log(d / d_native)
    return math.sqrt(k_sd ** 2 + (RIEGEL_TAU * frac) ** 2)


def hr_reach_mult(peak_ratio: float | None) -> float:
    """세트 후반 최대 HR/HRmax 가 기준 미달이면 관측 분산 배율(>1). HR 없으면 1."""
    if not peak_ratio:
        return 1.0
    return math.exp(HR_REACH_SLOPE * max(0.0, HR_REACH_REF - peak_ratio) * 100.0)


def summarize(x: float, var: float, d: float) -> dict:
    """칼만 상태 → 중앙값·80% 범위·예측 SD(ln 시간)·신뢰도. 대회 날 변동 SIGMA_RACE 포함."""
    sd = math.sqrt(var + SIGMA_RACE ** 2)
    e = dlnt_dvdot(x, d)
    return {"median_s": time_for_vdot(x, d), "low_s": time_for_vdot(x + Z80 * sd, d),
            "high_s": time_for_vdot(x - Z80 * sd, d), "sd_ln": e * sd, "state_sd_ln": e * math.sqrt(var),
            "confidence": round(math.erf(CONF_BAND / (e * sd * math.sqrt(2))), 2)}


def tanda_marathon(weekly_km_8w: float, train_pace_sec_km: float) -> float:
    """(a) Tanda(2011): Pm = 17.1 + 140·exp(−0.0053·K) + 0.55·P (s/km). 반환 마라톤 시간(s)."""
    return (17.1 + 140.0 * math.exp(-0.0053 * weekly_km_8w) + 0.55 * train_pace_sec_km) * 42.195


def combine_marathon(s: dict, tanda_s: float) -> dict:
    """칼만 마라톤(상태 분산)과 Tanda 를 ln 시간 역분산 결합. 대회 날 변동은 결합 후 더한다."""
    w1, w2 = 1 / s["state_sd_ln"] ** 2, 1 / TANDA_SIGMA ** 2
    mu = (w1 * math.log(s["median_s"]) + w2 * math.log(tanda_s)) / (w1 + w2)
    race_ln = math.sqrt(max(0.0, s["sd_ln"] ** 2 - s["state_sd_ln"] ** 2))
    sd = math.sqrt(1 / (w1 + w2) + race_ln ** 2)
    return {"median_s": math.exp(mu), "low_s": math.exp(mu - Z80 * sd), "high_s": math.exp(mu + Z80 * sd),
            "sd_ln": sd, "confidence": round(math.erf(CONF_BAND / (sd * math.sqrt(2))), 2),
            "tanda_weight": round(w2 / (w1 + w2), 3)}

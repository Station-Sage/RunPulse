"""레이스 예측 v2 순수 계산 — Daniels VDOT, 앵커 감쇠, 블록 신호, 결합, 개인 내구성 지수, 마라톤(Daniels·Tanda), 범위·신뢰도.

DB·CalcContext 무의존. 모든 속도 m/s, 시간 s, 거리 m.
"""
from __future__ import annotations

import math

DECAY_PER_WEEK = 0.08    # 앵커 감쇠 VDOT/주 (6주 유예 후) — 문헌 기반 가정, 튜닝하지 않음
DECAY_GRACE_WEEKS = 6.0
K_DOWN = 0.25            # 작업구간 < 앵커일 때 하향 반영 비율
H_WEIGHT = 0.20          # HR@LTHR 신호 가중
RIEGEL_K0 = 1.06         # 개인 내구성 사전 평균
RIEGEL_TAU = 0.03        # 사전 표준편차
PAIR_SIGMA0 = 0.04       # 대회 쌍 1개의 k 관측 오차(간격 0일)
SIGMA_RACE = 0.035       # 5K~하프 중앙값 상대오차 SD (백테스트 잔차 SD 3.3~3.6%)
Z80 = 1.2816


def vdot(dist_m: float, time_s: float) -> float:
    """Daniels/Gilbert VDOT."""
    v = dist_m / (time_s / 60.0)
    tm = time_s / 60.0
    vo2 = -4.60 + 0.182258 * v + 0.000104 * v * v
    pct = 0.8 + 0.1894393 * math.exp(-0.012778 * tm) + 0.2989558 * math.exp(-0.1932605 * tm)
    return vo2 / pct


def time_for_vdot(vd: float, dist_m: float) -> float:
    """VDOT·거리 → 예상 시간(s). 이분법."""
    lo, hi = 60.0, 60000.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if vdot(dist_m, mid) > vd:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def threshold_speed(vd: float) -> float:
    """VDOT → 60분 레이스 속도(m/s) = 역치 속도 근사."""
    lo, hi = 1000.0, 30000.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if vdot(mid, 3600.0) < vd:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2 / 3600.0


def temp_factor(temp_c: float | None, heat_pct_per_c: float, cold_pct_per_c: float) -> float:
    """기온 T에서의 속도 배율(15℃ 기준=1). heat/cold 는 음수 %/℃ (예: -0.62, -0.84)."""
    if temp_c is None:
        return 1.0
    return 1.0 + (heat_pct_per_c * max(0.0, temp_c - 15.0) + cold_pct_per_c * max(0.0, 5.0 - temp_c)) / 100.0


def vdot_at_15c(dist_m: float, time_s: float, temp_c: float | None, heat: float, cold: float) -> float:
    """기온 T에서 낸 기록을 15℃ 등가 VDOT로."""
    return vdot(dist_m, time_s * temp_factor(temp_c, heat, cold))


def time_at_temp(vd15: float, dist_m: float, temp_c: float | None, heat: float, cold: float) -> float:
    """15℃ VDOT → 기온 T에서의 예상 시간."""
    return time_for_vdot(vd15, dist_m) / temp_factor(temp_c, heat, cold)


def anchor(races: list[dict], weeks_ago_key: str = "weeks") -> dict | None:
    """races: [{"vdot15": float, "weeks": float, "activity_id": int, ...}] (전력 대회, 365일 이내).
    감쇠 적용 후 최대인 대회를 반환(원본 dict + "value")."""
    best = None
    for r in races:
        v = r["vdot15"] - max(0.0, r[weeks_ago_key] - DECAY_GRACE_WEEKS) * DECAY_PER_WEEK
        if best is None or v > best["value"]:
            best = dict(r, value=v)
    return best


def best_block(laps: list[dict], lthr: float | None, v_t: float | None, is_race: bool,
               min_d: float = 2000.0, min_t: float = 480.0) -> float | None:
    """연속 랩 블록(≥2km, ≥8분) 중 GAP-VDOT 최대. 자격: 대회이거나, 블록 평균 HR ≥ 0.92·LTHR,
    또는 블록 GAP 속도 ≥ 0.90·v_t. laps: [{"dist_m","dur_s","speed_ms","hr"}] (speed_ms=GAP 우선)."""
    best = None
    n = len(laps)
    for i in range(n):
        d = tg = tt = hrs = 0.0
        for j in range(i, n):
            lap = laps[j]
            v = lap["speed_ms"]
            if not v or v <= 0:
                break
            d += lap["dist_m"]
            tg += lap["dist_m"] / v
            tt += lap["dur_s"]
            hrs += (lap.get("hr") or 0.0) * lap["dur_s"]
            if d < min_d or tt < min_t:
                continue
            ok = is_race
            if not ok and lthr and hrs / tt >= 0.92 * lthr:
                ok = True
            if not ok and v_t and d / tg >= 0.90 * v_t:
                ok = True
            if ok:
                vd = vdot(d, tg)
                if best is None or vd > best:
                    best = vd
    return best


def combine(a: float | None, w: float | None, h: float | None) -> tuple[float | None, dict]:
    """결합 VDOT와 실제 적용 가중치. 반환 (vdot, {"race","work","hr"})."""
    if a is None and w is None:
        return (h, {"race": 0.0, "work": 0.0, "hr": 1.0}) if h is not None else (None, {})
    if a is None:
        if h is None:
            return w, {"race": 0.0, "work": 1.0, "hr": 0.0}
        return 0.6 * w + 0.4 * h, {"race": 0.0, "work": 0.6, "hr": 0.4}
    if w is None:
        core, wr, ww = a, 1.0, 0.0
    elif w >= a:
        core, wr, ww = w, 0.0, 1.0
    else:
        core, wr, ww = a + K_DOWN * (w - a), 1.0 - K_DOWN, K_DOWN
    if h is None:
        return core, {"race": wr, "work": ww, "hr": 0.0}
    return (1 - H_WEIGHT) * core + H_WEIGHT * h, {"race": round((1 - H_WEIGHT) * wr, 3),
                                                  "work": round((1 - H_WEIGHT) * ww, 3), "hr": H_WEIGHT}


def k_personal(pairs: list[dict]) -> tuple[float, float, int]:
    """개인 내구성(Riegel) 지수. pairs: [{"d1","t1","d2","t2","gap_days"}] 전력 대회 쌍(d2 ≥ 1.6·d1, 90일 이내,
    시간은 15℃ 등가). 사전 N(1.06, 0.03²)에 역분산 가중으로 수축. 반환 (k, sd, 사용 쌍 수)."""
    num = RIEGEL_K0 / RIEGEL_TAU ** 2
    den = 1.0 / RIEGEL_TAU ** 2
    used = 0
    for p in pairs:
        if p["d2"] < 1.6 * p["d1"] or p["gap_days"] > 90:
            continue
        k = math.log(p["t2"] / p["t1"]) / math.log(p["d2"] / p["d1"])
        if not 0.95 <= k <= 1.25:
            continue
        s2 = (PAIR_SIGMA0 * (1 + p["gap_days"] / 30.0)) ** 2
        num += k / s2
        den += 1.0 / s2
        used += 1
    return num / den, (1.0 / den) ** 0.5, used


def convert(vd: float, d_anchor: float, d_target: float, k: float) -> float:
    """Daniels 환산 × 개인 지수 보정: T = Daniels(vd, d_target) × (d_target/d_anchor)^(k − 1.06)."""
    return time_for_vdot(vd, d_target) * (d_target / d_anchor) ** (k - RIEGEL_K0)


def tanda_marathon(weekly_km_8w: float, train_pace_sec_km: float) -> float:
    """Tanda(2011): 마라톤 페이스 Pm = 17.1 + 140·exp(-0.0053·K) + 0.55·P (s/km). 반환 마라톤 시간(s)."""
    pm = 17.1 + 140.0 * math.exp(-0.0053 * weekly_km_8w) + 0.55 * train_pace_sec_km
    return pm * 42.195


def marathon_estimate(daniels_s: float, tanda_s: float, long_runs_28k_12w: int) -> dict:
    """중앙값 = 두 모델의 기하평균. 범위 = [min×0.98, max×1.03×(1.02 if 12주 28km+ 롱런 0회)]."""
    med = math.sqrt(daniels_s * tanda_s)
    low = min(daniels_s, tanda_s) * 0.98
    high = max(daniels_s, tanda_s) * 1.03 * (1.02 if long_runs_28k_12w == 0 else 1.0)
    return {"median_s": med, "low_s": low, "high_s": high, "model_gap_pct": abs(daniels_s - tanda_s) / med * 100}


def f_linear(x: float, x_good: float, x_bad: float, y_good: float, y_bad: float) -> float:
    if x <= x_good:
        return y_good
    if x >= x_bad:
        return y_bad
    return y_good + (y_bad - y_good) * (x - x_good) / (x_bad - x_good)


def confidence(anchor_weeks: float | None, spread_pct: float, dist_ratio: float, n_signals: int,
               model_gap_pct: float | None = None) -> tuple[float, list[str]]:
    """신뢰도(0~1)와 이유. 상한을 임의로 두지 않고 근거(앵커 최근성·신호 일치·신호 수·거리 외삽·모델 차)로만 계산."""
    reasons = []
    f_rec = 0.45 if anchor_weeks is None else f_linear(anchor_weeks, 8, 52, 1.0, 0.5)
    if anchor_weeks is None:
        reasons.append("최근 1년 전력 대회 기록 없음")
    elif anchor_weeks > 8:
        reasons.append(f"기준 대회가 {anchor_weeks:.0f}주 전")
    f_agree = f_linear(spread_pct, 3, 10, 1.0, 0.6)
    if spread_pct > 3:
        reasons.append(f"신호 간 차이 {spread_pct:.1f}%")
    f_n = {0: 0.3, 1: 0.7, 2: 0.9}.get(n_signals, 1.0)
    if n_signals < 3:
        reasons.append(f"근거 신호 {n_signals}개")
    r = max(dist_ratio, 1 / dist_ratio) if dist_ratio > 0 else 1.0
    f_dist = f_linear(r, 1.0, 4.2, 1.0, 0.75)
    if r > 1.5:
        reasons.append(f"거리 외삽 ×{r:.1f}")
    f_model = 1.0 if model_gap_pct is None else f_linear(model_gap_pct, 3, 12, 1.0, 0.5)
    if model_gap_pct is not None and model_gap_pct > 3:
        reasons.append(f"마라톤 모델 간 차이 {model_gap_pct:.1f}%")
    return round(0.9 * f_rec * f_agree * f_n * f_dist * f_model, 2), reasons


def race_range(median_s: float, conf: float, slow_extra_pct: float = 0.0) -> tuple[float, float]:
    """5K~하프 80% 범위. slow_extra_pct: 느린 쪽에만 더하는 %p(볼륨 급감·이행률 저조 등)."""
    s = SIGMA_RACE * (1 + 0.5 * (1 - conf))
    return median_s * (1 - Z80 * s), median_s * (1 + Z80 * s + slow_extra_pct / 100.0)

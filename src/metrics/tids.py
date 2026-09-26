"""TIDS (Training Intensity Distribution Score) — 8주 러닝 시간의 3구간 분포(P7-PRED-88, REVIEW-08 §R4).

세션 수가 아니라 랩 시간으로 센다(세션 수 기준은 품질 세션의 70%가 이지 시간이어도 "고강도 1회"로 세어 포화 → mixed 94.5%).
구간 경계(기기 불필요, Daniels 식): Z1 < M 속도 ≤ Z2 < T 속도 ≤ Z3. M·T 는 최신 race_pred_vdot 에서 계산한다
(Seiler 3구간의 LT1·LT2 를 M·T 로 근사 [가정]). 패턴: Z2 최대 → threshold, Z1 > Z3 > Z2 이고 극화 지수
PI = log10(Z1/Z2 × Z3 × 100) > 2 → polarized(Treff 2019 [가정: 원문 확인]), Z1 ≥ Z2 ≥ Z3 → pyramidal, 그 외 mixed.
"""
from __future__ import annotations

import math

from src.metrics.base import CalcContext, CalcResult, MetricCalculator
from src.metrics.prediction.daniels import zone_speeds

EXCLUDE_TYPES = ("treadmill", "indoor_running", "virtual_running")
MIN_RUNS = 5


def distribution(runs: list[dict], v_m: float, v_t: float) -> dict | None:
    """runs(get_runs with_laps) → {"z1","z2","z3"} 시간 %. 랩 없는 활동은 활동 평균 속도 1블록."""
    t = [0.0, 0.0, 0.0]
    for r in runs:
        if r["activity_type"] in EXCLUDE_TYPES:
            continue
        blocks = r.get("laps") or ([{"dur_s": r["moving_s"], "speed_ms": r["distance_m"] / r["moving_s"]}] if r["moving_s"] else [])
        for b in blocks:
            v = b["speed_ms"] or 0.0
            t[0 if v < v_m else (1 if v < v_t else 2)] += b["dur_s"] or 0.0
    tot = sum(t)
    if not tot:
        return None
    return {"z1": round(t[0] / tot * 100, 1), "z2": round(t[1] / tot * 100, 1), "z3": round(t[2] / tot * 100, 1)}


def pattern(d: dict) -> tuple[str, float | None]:
    z1, z2, z3 = d["z1"], d["z2"], d["z3"]
    pi = round(math.log10(z1 / 100 / max(z2 / 100, 1e-3) * z3 / 100 * 100), 2) if z3 > 0 else None
    if z2 >= z1 and z2 >= z3:
        return "threshold", pi
    if z1 > z3 > z2 and pi is not None and pi > 2.0:
        return "polarized", pi
    if z1 >= z2 >= z3:
        return "pyramidal", pi
    return "mixed", pi


class TIDSCalculator(MetricCalculator):
    name = "tids"
    provider = "runpulse:formula_v1"
    version = "2.0"
    scope_type = "daily"
    category = "load"

    display_name = "강도 분포 (TIDS)"
    description = "8주 러닝 시간의 3구간(마라톤 페이스 미만·마라톤~역치·역치 이상) 분포와 패턴(polarized/threshold/pyramidal/mixed)."
    format_type = "json"
    requires = ["race_pred_vdot"]

    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        vd = ctx.get_latest_daily_metric("race_pred_vdot", ctx.scope_id, provider="runpulse:formula_v1")
        runs = ctx.get_runs(56, with_laps=True)
        if not vd or len(runs) < MIN_RUNS:
            return []
        z = zone_speeds(vd)
        d = distribution(runs, z["M"], z["T"])
        if d is None:
            return []
        pat, pi = pattern(d)
        return [self._result(
            json_val={"basis": "time", "low_pct": d["z1"], "mid_pct": d["z2"], "high_pct": d["z3"], "pattern": pat,
                      "polarization_index": pi, "vdot": round(vd, 2),
                      "m_pace_sec_km": round(1000 / z["M"]), "t_pace_sec_km": round(1000 / z["T"])},
            text=pat,
        )]

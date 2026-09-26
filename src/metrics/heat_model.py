"""개인 기온 영향 모델(일별) — 정상 주행 랩의 HR·속도·외기 기온 회귀로 더위/추위 계수(%/℃)를 추정해 기본값으로 수축(P7-PRED-33).

speed = a + b·HR + h·max(0, T−15) + c·max(0, 5−T)  →  heat = h/v160·100, cold = c/v160·100 (v160 = a + 160b)
수축: 가중 n/(n+400) (n = 적합 점 수), 기본값 heat −0.62 / cold −0.84 %/℃ (2025-05~12 학습 구간 적합값).
"""
from __future__ import annotations

from src.metrics.base import CalcContext, CalcResult, MetricCalculator
from src.metrics.prediction.signals import steady_points

DEFAULT_HEAT, DEFAULT_COLD = -0.62, -0.84
SHRINK_N = 400
MIN_POINTS = 60


def ols(X: list[list[float]], y: list[float]) -> list[float] | None:
    """정규방정식 가우스-조던. 특이행렬이면 None."""
    k = len(X[0])
    A = [[sum(r[i] * r[j] for r in X) for j in range(k)] for i in range(k)]
    b = [sum(r[i] * v for r, v in zip(X, y)) for i in range(k)]
    for i in range(k):
        pv = A[i][i]
        if abs(pv) < 1e-12:
            return None
        A[i] = [v / pv for v in A[i]]
        b[i] /= pv
        for j in range(k):
            if j != i:
                f = A[j][i]
                A[j] = [v - f * w for v, w in zip(A[j], A[i])]
                b[j] -= f * b[i]
    return b


def fit_heat(points: list[tuple[float, float, float]]) -> dict:
    """points: [(hr, speed_ms, ambient_c)] → {"heat","cold","n","raw_heat","raw_cold"} (수축 후)."""
    n = len(points)
    raw_h = raw_c = None
    if n >= MIN_POINTS:
        co = ols([[1.0, h, max(0.0, t - 15), max(0.0, 5 - t)] for h, _, t in points], [v for _, v, _ in points])
        if co:
            v160 = co[0] + co[1] * 160
            if v160 > 0:
                raw_h, raw_c = co[2] / v160 * 100, co[3] / v160 * 100
    w = n / (n + SHRINK_N) if raw_h is not None else 0.0
    heat = DEFAULT_HEAT + w * ((raw_h or 0.0) - DEFAULT_HEAT)
    cold = DEFAULT_COLD + w * ((raw_c or 0.0) - DEFAULT_COLD)
    return {"heat": round(min(0.0, heat), 3), "cold": round(min(0.0, cold), 3), "n": n,
            "raw_heat": raw_h and round(raw_h, 3), "raw_cold": raw_c and round(raw_c, 3), "weight": round(w, 3)}


class HeatModelCalculator(MetricCalculator):
    name = "heat_model"
    provider = "runpulse:formula_v1"
    version = "1.0"
    scope_type = "daily"
    category = "weather"
    display_name = "기온 영향 계수"
    description = "15℃ 대비 기온 1℃당 속도 변화(%). 더위(15℃ 초과)·추위(5℃ 미만) 각각, 개인 데이터로 기본값을 보정."
    unit = "%/℃"
    format_type = "json"
    requires = []
    produces = ["heat_model"]

    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        runs = ctx.get_runs(365, with_laps=True, include_end=False)
        for r in runs:
            r["ambient_c"] = ctx.get_activity_metric(r["id"], "weather_temp_c")
        fit = fit_heat([p for r in runs for p in steady_points(r)])
        return [self._result(value=fit["heat"], json_val=fit, confidence=round(0.3 + 0.6 * fit["weight"], 2))]

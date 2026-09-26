"""DI (Durability Index) v2 — 90분 이상 러닝에서 후반 효율 유지율(P7-PRED-89).

효율 = 랩 GAP 속도 ÷ 랩 평균 HR. 워밍업(처음 10분)을 뺀 나머지 시간의 앞 25% 대 뒤 25% 효율 비 × 100.
HR 이 없는 활동은 속도 비만 쓴다(json basis). 상한 없음 — 후반이 더 효율적이면 100을 넘는다(네거티브 스플릿).
v1(스트림 절반 속도 비, 0~100 절단)은 100이 87%로 포화였다(REVIEW-08 #7). 더위·탈수에 따른 HR 드리프트가 섞인다.
"""
from __future__ import annotations

from statistics import mean

from src.metrics.base import CalcContext, CalcResult, MetricCalculator

MIN_DURATION_SEC = 5400      # 90분
WARMUP_SEC = 600             # 앞 10분 제외
QUARTER = 0.25
WINDOW_DAYS = 56


def _quarter_eff(laps: list[dict], use_hr: bool) -> tuple[float, float] | None:
    """워밍업 뒤 앞 25%·뒤 25% 시간 구간의 효율(시간 가중). 랩 경계는 시간 비율로 나눠 넣는다."""
    t0, pts = 0.0, []
    for b in laps:
        if not b["dur_s"] or not b["speed_ms"] or (use_hr and not b["hr"]):
            t0 += b["dur_s"] or 0
            continue
        pts.append((t0, t0 + b["dur_s"], b["speed_ms"] / b["hr"] if use_hr else b["speed_ms"]))
        t0 += b["dur_s"]
    body = t0 - WARMUP_SEC
    if body <= 0 or not pts:
        return None

    def win(a: float, z: float) -> float | None:
        w = s = 0.0
        for x0, x1, e in pts:
            ov = min(x1, z) - max(x0, a)
            if ov > 0:
                w += ov
                s += ov * e
        return s / w if w >= 0.5 * (z - a) else None

    first = win(WARMUP_SEC, WARMUP_SEC + QUARTER * body)
    last = win(t0 - QUARTER * body, t0)
    return (first, last) if first and last else None


class DICalculator(MetricCalculator):
    name = "di"
    provider = "runpulse:formula_v1"
    version = "2.0"
    scope_type = "daily"
    category = "capacity"
    display_name = "내구성 지수 (DI)"
    description = "90분 이상 러닝에서 워밍업 뒤 앞 25% 대비 뒤 25%의 효율(GAP 속도/HR) 유지율. 100 = 유지, 상한 없음."
    unit = "점"
    higher_is_better = True
    decimal_places = 1
    requires = []

    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        runs = [r for r in ctx.get_runs(WINDOW_DAYS, with_laps=True)
                if (r["moving_s"] or 0) >= MIN_DURATION_SEC and len(r.get("laps") or []) >= 4]
        per = []
        for r in runs:
            use_hr = all(b["hr"] for b in r["laps"])
            q = _quarter_eff(r["laps"], use_hr)
            if q:
                per.append({"date": r["date"], "ratio": round(q[1] / q[0] * 100, 1), "basis": "ef" if use_hr else "pace"})
        if not per:
            return []
        return [self._result(value=round(mean(p["ratio"] for p in per), 1),
                             json_val={"runs": per[-8:], "n": len(per), "window_days": WINDOW_DAYS})]

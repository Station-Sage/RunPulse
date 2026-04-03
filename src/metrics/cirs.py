"""CIRS (Composite Injury Risk Score) — 설계서 4-4 기준.

ACWR×0.4 + LSI×0.3 + consecutive_training_days×0.2 + fatigue(CTL-TSB)×0.1 → 0~100.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from src.metrics.base import CalcContext, CalcResult, MetricCalculator
from src.metrics.lsi import LSICalculator


class CIRSCalculator(MetricCalculator):
    name = "cirs"
    provider = "runpulse:formula_v1"
    version = "1.0"
    scope_type = "daily"
    category = "rp_risk"
    display_name = "부상 위험 지수 (CIRS)"
    description = "ACWR, LSI, 연속훈련일, 피로도를 종합한 부상 위험도."
    unit = "점"
    ranges = {"low": [0, 30], "moderate": [30, 50], "high": [50, 70], "critical": [70, 100]}
    higher_is_better = False
    decimal_places = 0
    display_name = "부상 위험 지수 (CIRS)"
    description = "ACWR, LSI, 연속훈련일, 피로도를 종합한 부상 위험도."
    unit = "점"
    ranges = {"low": [0, 30], "moderate": [30, 50], "high": [50, 70], "critical": [70, 100]}
    higher_is_better = False
    decimal_places = 0
    requires = ["acwr", "lsi", "ctl", "tsb"]

    WEIGHTS = {
        "acwr": 0.40,
        "lsi": 0.30,
        "consecutive": 0.20,
        "fatigue": 0.10,
    }

    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        components = {}
        total_weight = 0.0

        # ── ACWR 편차 (1.0이 이상적, 벗어날수록 위험) ──
        acwr = ctx.get_metric("acwr", provider="runpulse:formula_v1")
        if acwr is not None:
            acwr_risk = abs(acwr - 1.0) * 100  # 0.5→50, 1.5→50
            acwr_risk = min(acwr_risk, 100)
            components["acwr"] = acwr_risk
            total_weight += self.WEIGHTS["acwr"]

        # ── LSI (>1.5 위험) ──
        lsi = ctx.get_metric("lsi", provider="runpulse:formula_v1")
        if lsi is not None:
            lsi_risk = min(max(lsi - 1.0, 0) * 100, 100)
            components["lsi"] = lsi_risk
            total_weight += self.WEIGHTS["lsi"]

        # ── 연속 훈련일 (rest day 없이 연속) ──
        consec = self._consecutive_days(ctx)
        if consec is not None and consec > 0:
            # 7일 연속 → 100점
            consec_risk = min(consec / 7.0 * 100, 100)
            components["consecutive"] = consec_risk
            total_weight += self.WEIGHTS["consecutive"]

        # ── Fatigue = CTL - TSB (높을수록 피로) ──
        ctl = ctx.get_metric("ctl", provider="runpulse:formula_v1")
        tsb = ctx.get_metric("tsb", provider="runpulse:formula_v1")
        if ctl is not None and tsb is not None:
            fatigue = ctl - tsb  # ATL과 동일
            fatigue_risk = min(max(fatigue / 80.0 * 100, 0), 100)
            components["fatigue"] = fatigue_risk
            total_weight += self.WEIGHTS["fatigue"]

        if not components or total_weight == 0:
            return []

        score = sum(
            components[k] * self.WEIGHTS[k] for k in components
        ) / total_weight
        confidence = round(min(total_weight / sum(self.WEIGHTS.values()), 1.0), 2)

        return [self._result(
            value=round(score, 1),
            confidence=confidence,
            json_val={"components": {k: round(v, 1) for k, v in components.items()}},
        )]

    def _consecutive_days(self, ctx: CalcContext) -> int | None:
        """현재 날짜부터 역추적하여 연속 훈련일 수 계산."""
        date_str = ctx.scope_id
        try:
            target = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return None

        count = 0
        for i in range(14):  # 최대 14일 역추적
            d = (target - timedelta(days=i)).strftime("%Y-%m-%d")
            load = LSICalculator._get_day_load(ctx, d)
            if load > 0:
                count += 1
            else:
                break
        return count

"""WLEI (Weather-Loaded Effort Index) — 날씨 가중 노력 지수.

TRIMP에 날씨 스트레스 계수를 곱해 실제 신체 부담을 반영.

공식:
    temp_stress    = 1 + max(0, temp_c - 20) * 0.025 + max(0, 5 - temp_c) * 0.015
    humidity_stress = 1 + max(0, humidity_pct - 60) * 0.008
    WLEI = TRIMP * temp_stress * humidity_stress

v0.3 포팅: _v02_backup/wlei.py → MetricCalculator 형식
"""
from __future__ import annotations

from src.metrics.base import MetricCalculator, CalcResult, CalcContext


class WLEICalculator(MetricCalculator):
    name = "wlei"
    provider = "runpulse:formula_v1"
    version = "1.0"
    scope_type = "activity"
    category = "rp_load"
    requires = ["trimp"]
    produces = ["wlei"]

    display_name = "WLEI (날씨 가중 노력)"
    description = "TRIMP에 기온/습도 스트레스 계수를 적용한 실제 신체 부담 지수"
    unit = "AU"
    ranges = {"low": 50, "moderate": 100, "high": 200, "very_high": 300}
    higher_is_better = None
    format_type = "number"
    decimal_places = 1

    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        trimp = ctx.get_metric("trimp", provider="runpulse:formula_v1")
        if trimp is None:
            return []

        act = ctx.activity
        # 기온: activity avg_temperature 또는 metric_store
        temp_c = 20.0
        if act:
            t = act.get("avg_temperature")
            if t is not None:
                temp_c = float(t)
            else:
                t_metric = ctx.get_metric("weather_temp_c")
                if t_metric is not None:
                    temp_c = float(t_metric)

        # 습도
        humidity_pct = 60.0
        h = ctx.get_metric("weather_humidity_pct")
        if h is not None:
            humidity_pct = float(h)

        temp_stress = (
            1.0
            + max(0.0, temp_c - 20.0) * 0.025
            + max(0.0, 5.0 - temp_c) * 0.015
        )
        humidity_stress = 1.0 + max(0.0, humidity_pct - 60.0) * 0.008

        wlei = round(float(trimp) * temp_stress * humidity_stress, 2)

        conf = 0.7
        if act and act.get("avg_temperature") is not None:
            conf = 0.9

        return [self._result(
            value=wlei,
            confidence=conf,
            json_value={
                "trimp": round(float(trimp), 1),
                "temp_c": temp_c,
                "humidity_pct": humidity_pct,
                "temp_stress": round(temp_stress, 4),
                "humidity_stress": round(humidity_stress, 4),
            },
        )]

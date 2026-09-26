"""FEARP (Fitness & Environment Adjusted Running Pace) v2 — 외기 기온·이슬점·고도로 보정한 환경 보정 페이스(P7-PRED-90).

더위: 외기(weather_temp_c) + 이슬점(weather_dew_point_c)의 화씨 합으로 보정률을 정한다(러너 실무 표, (c) 휴리스틱:
합 100°F 이하 0%, 110 0.5%, 120 1%, 130 2%, 140 3%, 150 4.5%, 160 6%, 170 8%, 180+ 10% — 사이는 선형).
이슬점이 없으면 외기만으로 15℃ 초과 1℃당 0.5%. 외기가 없으면 기기 온도(손목, 체온 영향)는 쓰지 않고 더위 보정 생략.
추위: 5℃ 미만 1℃당 0.3% (c). 오르막: 평균 경사 1%당 2% (c).
"""
from __future__ import annotations

from src.metrics.base import CalcContext, CalcResult, MetricCalculator


_HEAT_TABLE = ((100, 0.0), (110, 0.5), (120, 1.0), (130, 2.0), (140, 3.0), (150, 4.5), (160, 6.0), (170, 8.0), (180, 10.0))


def heat_penalty(temp_c: float | None, dew_c: float | None) -> float:
    """외기·이슬점 → 더위 보정률(%). 이슬점 없으면 15℃ 초과 1℃당 0.5%."""
    if temp_c is None:
        return 0.0
    if dew_c is None:
        return max(0.0, temp_c - 15) * 0.5
    s = (temp_c * 9 / 5 + 32) + (dew_c * 9 / 5 + 32)
    if s <= _HEAT_TABLE[0][0]:
        return 0.0
    for (x0, y0), (x1, y1) in zip(_HEAT_TABLE, _HEAT_TABLE[1:]):
        if s <= x1:
            return y0 + (y1 - y0) * (s - x0) / (x1 - x0)
    return _HEAT_TABLE[-1][1]


class FEARPCalculator(MetricCalculator):
    name = "fearp"
    provider = "runpulse:formula_v1"
    version = "2.0"
    scope_type = "activity"
    category = "capacity"
    display_name = "FEARP (환경 보정 페이스)"
    description = "기온, 습도, 고도를 보정한 환경 보정 페이스."
    unit = "sec/km"
    format_type = "pace"
    higher_is_better = False
    display_name = "FEARP (환경 보정 페이스)"
    description = "기온, 습도, 고도를 보정한 환경 보정 페이스."
    unit = "sec/km"
    format_type = "pace"
    higher_is_better = False
    requires = []

    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        act = ctx.activity
        if act.get("activity_type") not in ("running", "trail_running", "treadmill"):
            return []

        pace = act.get("avg_pace_sec_km")
        if not pace or pace <= 0:
            speed = act.get("avg_speed_ms")
            if speed and speed > 0:
                pace = 1000.0 / speed
            else:
                return []

        temp = ctx.get_metric("weather_temp_c")          # 외기(P7-PRED-32). 기기 온도는 쓰지 않는다
        dew = ctx.get_metric("weather_dew_point_c")
        elevation = act.get("elevation_gain") or 0
        distance_m = act.get("distance_m") or 0

        adjustment = 1.0 + heat_penalty(temp, dew) / 100.0
        if temp is not None and temp < 5:
            adjustment += (5 - temp) * 0.003
        if distance_m > 0 and elevation > 0:
            adjustment += (elevation / distance_m) * 100 * 0.02
        fearp = pace / adjustment

        conf = 0.6 + (0.15 if temp is not None else 0) + (0.1 if dew is not None else 0) + (0.15 if elevation > 0 else 0)
        return [self._result(value=round(fearp, 1), confidence=min(conf, 1.0),
                             json_val={"temp_c": temp, "dew_point_c": dew, "adjust_pct": round((adjustment - 1) * 100, 2)})]

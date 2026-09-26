"""Marathon Shape v2 — 마라톤 볼륨·롱런 구조(P7-PRED-52, REVIEW-09 §7). 기기 불필요(GPS·시간).

numeric = 볼륨 충족률(%) = 최근 8주 주평균 km ÷ Tanda(2011) 역산 필요 주간 km × 100 (상한 없음).
  필요 km: 목표 마라톤(활성 goal, 42km 이상)이 있으면 목표 페이스, 없으면 현재 race_pred_vdot 의 Daniels 마라톤 페이스를
  현재 평균 훈련 페이스로 Tanda 식 Pm = 17.1 + 140·e^(−0.0053K) + 0.55·P 에 넣어 K 로 푼다. 달성 불가(해 없음)면 None.
json: 주간 km(8주)·평균 페이스·주당 품질 세션·거리별 롱런 수(12주: ≥21km, ≥30km)·최장·롱런 속 MP km(8주)·필요 km.
예측 반영은 darp 가 따로 한다(중앙값 = Tanda, 최장 초과 외삽 = 범위 확대). 이 메트릭은 설명·계획용이다.
v1 의 점수식(검증 안 된 표 기반 목표 볼륨 × 2/3 + 롱런 × 1/3, 100 절단)은 쓰지 않는다.
"""
from __future__ import annotations

import math
from datetime import date

from src.metrics.base import CalcContext, CalcResult, MetricCalculator
from src.metrics.prediction import response as rs
from src.metrics.prediction.daniels import time_for_vdot
from src.metrics.prediction.signals_r4 import longest_run_m, tanda_inputs

MARATHON_M = 42195.0
LONG_KM = (21.0, 30.0)


def tanda_required_km(goal_pace_s_km: float, train_pace_s_km: float) -> float | None:
    """Tanda 식을 주간 km 로 역산. (Pm − 17.1 − 0.55·P)/140 이 (0, 1) 밖이면 None(볼륨만으로 도달 불가/이미 충분)."""
    x = (goal_pace_s_km - 17.1 - 0.55 * train_pace_s_km) / 140.0
    if x >= 1.0:
        return 0.0
    if x <= 0.0:
        return None
    return -math.log(x) / 0.0053


class MarathonShapeCalculator(MetricCalculator):
    name = "marathon_shape"
    provider = "runpulse:formula_v1"
    version = "2.0"
    scope_type = "daily"
    category = "capacity"
    requires = ["race_pred_vdot"]
    produces = ["marathon_shape"]

    display_name = "Marathon Shape"
    description = "마라톤 볼륨 충족률(%) = 8주 주평균 km ÷ Tanda 역산 필요 km. json 에 롱런·MP·품질 세션 구조."
    unit = "%"
    ranges = {"low": [0, 60], "building": [60, 85], "adequate": [85, 110], "high": [110, 300]}
    higher_is_better = True
    format_type = "number"
    decimal_places = 1

    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        day = ctx.scope_id
        vd = ctx.get_latest_daily_metric("race_pred_vdot", day, provider="runpulse:formula_v1")
        runs = ctx.get_runs(112, with_laps=True, include_end=False)
        if vd is None or not runs:
            return []
        km_w, pace, _ = tanda_inputs(runs, day)
        mp_speed = MARATHON_M / time_for_vdot(float(vd), MARATHON_M)
        goal = ctx.get_active_goal(day)
        if goal and (goal.get("distance_km") or 0) >= 42.0 and goal.get("target_time_sec"):
            goal_pace, basis = goal["target_time_sec"] / goal["distance_km"], "goal"
        else:
            goal_pace, basis = 1000.0 / mp_speed, "current_vdot"
        need = tanda_required_km(goal_pace, pace) if pace else None
        weekly = rs.weekly_zone_minutes(runs, day, weeks=8)
        longs = [r for r in runs if r["date"] < day and not r["is_race"] and (date.fromisoformat(day) - date.fromisoformat(r["date"])).days <= 84]
        js = {
            "weekly_km_8w": round(km_w, 1), "train_pace_s_km": round(pace) if pace else None,
            "quality_sessions_per_week_8w": round(sum(weekly["sessions"]) / 8, 2),
            "long_runs_12w": {f"ge_{int(k)}km": sum(1 for r in longs if r["distance_m"] >= k * 1000) for k in LONG_KM},
            "longest_12w_km": round((longest_run_m(runs, day) or 0) / 1000, 1),
            "mp_km_in_long_8w": round(rs.long_mp_km(runs, day, mp_speed), 1),
            "mp_pace_s_km": round(1000 / mp_speed), "target_pace_s_km": round(goal_pace), "basis": basis,
            "tanda_required_km": round(need, 1) if need is not None else None,
        }
        if need is None:                      # 볼륨만으로 목표 페이스 도달 불가 — 수치 없이 구조만
            return [self._result(value=None, json_val=js)]
        pct = round(km_w / need * 100, 1) if need > 0 else 100.0
        js["label"] = next(k for k, (lo, hi) in self.ranges.items() if pct < hi or k == "high")
        return [self._result(value=pct, json_val=js)]

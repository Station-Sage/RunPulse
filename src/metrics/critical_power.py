"""CP/W' (Critical Power / W Prime) — 임계 파워 및 무산소 용량.

2파라미터 모델: Work = W' + CP × t (선형 회귀)
파워미터 데이터 필요. 없으면 빈 결과.

v0.3 포팅: _v02_backup/critical_power.py → MetricCalculator 형식
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from src.metrics.base import MetricCalculator, CalcResult, CalcContext


class CriticalPowerCalculator(MetricCalculator):
    name = "critical_power"
    provider = "runpulse:formula_v1"
    version = "1.0"
    scope_type = "daily"
    category = "rp_performance"
    requires = ["power_curve"]  # 소스 메트릭 (intervals 등)
    produces = ["critical_power"]

    display_name = "Critical Power (CP)"
    description = "임계 파워 (W). 2파라미터 선형 회귀 모델."
    unit = "W"
    ranges = {"low": [0, 200], "moderate": [200, 280], "high": [280, 500]}
    higher_is_better = True
    format_type = "number"
    decimal_places = 1

    @staticmethod
    def _calc_cp_wprime(powers: list[float], durations: list[float]):
        if len(powers) < 2 or len(powers) != len(durations):
            return None
        work = [p * t for p, t in zip(powers, durations)]
        n = len(work)
        sx = sum(durations)
        sy = sum(work)
        sxx = sum(t * t for t in durations)
        sxy = sum(t * w for t, w in zip(durations, work))
        denom = n * sxx - sx * sx
        if abs(denom) < 1e-10:
            return None
        cp = (n * sxy - sx * sy) / denom
        w_prime = (sy - cp * sx) / n
        if cp <= 0 or w_prime < 0:
            return None
        return round(cp, 1), round(w_prime, 0)

    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        # NOTE: raw SQL 사용 — CalcContext API가 activity_type별 metric JOIN을 미지원
        target = ctx.scope_id
        td = date.fromisoformat(target)
        start = (td - timedelta(weeks=12)).isoformat()

        powers, durations = [], []

        # 1. power_curve JSON에서 — CalcContext API
        pc_data = ctx.get_activity_metric_series("power_curve", days=84, include_json=True)
        for entry in pc_data:
            try:
                raw_json = entry.get("json")
                if not raw_json:
                    continue
                pc = json.loads(raw_json) if isinstance(raw_json, str) else raw_json
                if isinstance(pc, dict):
                    for t_str, p in pc.items():
                        t = int(t_str)
                        if t >= 120 and p and float(p) > 0:
                            durations.append(float(t))
                            powers.append(float(p))
            except (json.JSONDecodeError, TypeError, ValueError):
                pass

        # 2. 활동별 avg_power + duration
        if len(powers) < 3:
            activities = ctx.get_activities_in_range(days=90)
            for a in activities:
                p, t = a.get("avg_power"), a.get("moving_time_sec")
                if p and p > 0 and t and t >= 120:
                    powers.append(float(p))
                    durations.append(float(t))

        if len(powers) < 3:
            return []

        result = self._calc_cp_wprime(powers, durations)
        if not result:
            return []

        cp, w_prime = result
        return [self._result(
            value=cp,
            json_val={"w_prime": w_prime, "sample_count": len(powers)},
        
            confidence=0.8,
        )]

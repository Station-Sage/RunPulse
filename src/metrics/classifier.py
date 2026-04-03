"""Workout Classifier — 설계서 4-2 기준.

규칙 기반 운동 유형 분류:
easy | tempo | threshold | interval | long_run | recovery | race | unknown
"""
from __future__ import annotations

from src.metrics.base import CalcContext, CalcResult, MetricCalculator
from src.metrics.trimp import TRIMPCalculator


class WorkoutClassifier(MetricCalculator):
    name = "workout_type"
    provider = "runpulse:rule_v1"
    version = "1.0"
    scope_type = "activity"
    category = "rp_classification"
    requires = []

    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        act = ctx.activity
        if act.get("activity_type") not in ("running", "trail_running", "treadmill"):
            return []

        distance_m = act.get("distance_m") or 0
        duration_sec = act.get("moving_time_sec") or act.get("duration_sec") or 0
        avg_hr = act.get("avg_hr")
        max_hr_athlete = TRIMPCalculator()._get_max_hr(ctx)
        hr_zone_pcts = self._get_hr_zone_pcts(ctx)

        classification = self._classify(
            distance_m, duration_sec, avg_hr, max_hr_athlete, hr_zone_pcts, act
        )

        return [self._result(
            json_val={
                "type": classification["type"],
                "confidence": classification["confidence"],
                "reasons": classification["reasons"],
            },
            text=classification["type"],
            confidence=classification["confidence"],
        )]

    def _classify(self, distance_m, duration_sec, avg_hr, max_hr,
                  hr_zones, act) -> dict:
        reasons = []
        scores = {
            "easy": 0, "recovery": 0, "long_run": 0,
            "tempo": 0, "threshold": 0, "interval": 0, "race": 0,
        }
        distance_km = distance_m / 1000 if distance_m else 0
        duration_min = duration_sec / 60 if duration_sec else 0

        if distance_km >= 18:
            scores["long_run"] += 3
            reasons.append(f"distance {distance_km:.1f}km >= 18km")
        elif distance_km >= 14:
            scores["long_run"] += 2

        if distance_km < 6 and duration_min < 40:
            scores["recovery"] += 2
            scores["easy"] += 1

        if avg_hr and max_hr and max_hr > 0:
            hr_pct = avg_hr / max_hr * 100
            if hr_pct < 70:
                scores["easy"] += 2; scores["recovery"] += 2
                reasons.append(f"avg HR {hr_pct:.0f}% < 70%")
            elif hr_pct < 80:
                scores["easy"] += 1; scores["tempo"] += 1
            elif hr_pct < 88:
                scores["tempo"] += 2; scores["threshold"] += 1
                reasons.append(f"avg HR {hr_pct:.0f}% -> tempo zone")
            elif hr_pct < 95:
                scores["threshold"] += 2; scores["interval"] += 1
                reasons.append(f"avg HR {hr_pct:.0f}% -> threshold zone")
            else:
                scores["race"] += 2; scores["interval"] += 1

        if hr_zones:
            z12 = hr_zones.get("z1", 0) + hr_zones.get("z2", 0)
            z45 = hr_zones.get("z4", 0) + hr_zones.get("z5", 0)
            if z12 > 80:
                scores["easy"] += 2
            if z45 > 30:
                scores["interval"] += 2
                reasons.append(f"Z4+Z5 = {z45:.0f}%")
            if z45 > 15 and z12 > 40:
                scores["interval"] += 1

        if act.get("event_type") in ("race", "race_running"):
            scores["race"] += 5
            reasons.append("event_type=race")

        best_type = max(scores, key=scores.get)
        best_score = scores[best_type]
        total = sum(scores.values()) or 1
        confidence = min(best_score / total, 1.0)
        if best_score == 0:
            best_type = "unknown"; confidence = 0.0

        return {"type": best_type, "confidence": round(confidence, 2), "reasons": reasons}

    def _get_hr_zone_pcts(self, ctx) -> dict:
        total = 0
        zones = {}
        for i in range(1, 6):
            val = ctx.get_metric(f"hr_zone_{i}_sec") or 0
            zones[f"z{i}"] = val
            total += val
        if total == 0:
            return {}
        return {k: v / total * 100 for k, v in zones.items()}

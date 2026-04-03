"""eFTP (Estimated Functional Threshold Pace) — 기능적 역치 페이스 추정.

1차: VDOT → Daniels T-pace
2차: 최근 12주 고강도 활동에서 역치 페이스 추정

단위: sec/km (낮을수록 빠름)

v0.3 포팅: _v02_backup/eftp.py → MetricCalculator 형식
"""
from __future__ import annotations

from datetime import date, timedelta
from src.metrics.base import MetricCalculator, CalcResult, CalcContext


class EFTPCalculator(MetricCalculator):
    name = "eftp"
    provider = "runpulse:formula_v1"
    version = "1.0"
    scope_type = "daily"
    category = "rp_performance"
    requires = ["runpulse_vdot"]
    produces = ["eftp"]

    display_name = "eFTP (역치 페이스)"
    description = "기능적 역치 페이스 추정 (sec/km). 낮을수록 빠름."
    unit = "sec/km"
    ranges = {"elite": [150, 210], "advanced": [210, 260], "intermediate": [260, 320], "beginner": [320, 600]}
    higher_is_better = False
    format_type = "pace"
    decimal_places = 0

    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        # NOTE: raw SQL 사용 — CalcContext API가 activity_type별 metric JOIN을 미지원
        # 1차: VDOT → Daniels T-pace
        vdot = ctx.get_metric("runpulse_vdot", provider="runpulse:formula_v1")
        if vdot is not None:
            from src.utils.daniels_table import vdot_to_t_pace
            t_pace = vdot_to_t_pace(float(vdot))
            if t_pace and t_pace > 120:
                return [self._result(
                    value=round(t_pace),
                    confidence=0.85,
                    json_val={
                        "source": "daniels_t_pace",
                        "vdot": round(float(vdot), 1),
                        "pace_sec_km": round(t_pace),
                    },
                )]

        # 2차: 최근 12주 고강도 활동에서 추정
        activities = ctx.get_activities_in_range(days=84, activity_type="running")

        # 엄격 필터: 30~70분, pace>180, HR비율>=0.82
        strict = [
            a for a in activities
            if a.get("moving_time_sec") and 1800 <= a["moving_time_sec"] <= 4200
            and a.get("avg_pace_sec_km") and a["avg_pace_sec_km"] > 180
            and a.get("avg_hr") and a.get("max_hr") and a["max_hr"] > 0
            and float(a["avg_hr"]) / float(a["max_hr"]) >= 0.82
        ]
        strict.sort(key=lambda a: a["avg_pace_sec_km"])
        rows = strict[:5]

        if not rows:
            # 완화 필터: 20~90분, HR비율>=0.75
            relaxed = [
                a for a in activities
                if a.get("moving_time_sec") and 1200 <= a["moving_time_sec"] <= 5400
                and a.get("avg_pace_sec_km") and a["avg_pace_sec_km"] > 180
                and a.get("avg_hr") and a.get("max_hr") and a["max_hr"] > 0
                and float(a["avg_hr"]) / float(a["max_hr"]) >= 0.75
            ]
            relaxed.sort(key=lambda a: a["avg_pace_sec_km"])
            rows = relaxed[:5]

        if not rows:
            return []

        # 상위 3개 가중 평균
        top = rows[:3]
        total_weight = 0.0
        weighted_pace = 0.0
        for a in top:
            pace = float(a["avg_pace_sec_km"])
            dur = float(a["moving_time_sec"])
            time_weight = max(0.3, 1.0 - abs(dur - 3600) / 3600 * 0.5)
            weighted_pace += pace * time_weight
            total_weight += time_weight

        if total_weight <= 0:
            return []

        eftp = round(weighted_pace / total_weight)
        return [self._result(
            value=eftp,
            confidence=0.65,
            json_val={
                "source": "estimated",
                "pace_sec_km": eftp,
                "sample_count": len(top),
            },
        )]

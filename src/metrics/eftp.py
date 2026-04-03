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
    ranges = {"elite": 210, "advanced": 260, "intermediate": 320, "beginner": 400}
    higher_is_better = False
    format_type = "pace"
    decimal_places = 0

    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        # 1차: VDOT → Daniels T-pace
        vdot = ctx.get_metric("runpulse_vdot", provider="runpulse:formula_v1")
        if vdot is not None:
            from src.utils.daniels_table import vdot_to_t_pace
            t_pace = vdot_to_t_pace(float(vdot))
            if t_pace and t_pace > 120:
                return [self._result(
                    value=round(t_pace),
                    confidence=0.85,
                    json_value={
                        "source": "daniels_t_pace",
                        "vdot": round(float(vdot), 1),
                        "pace_sec_km": round(t_pace),
                    },
                )]

        # 2차: 최근 12주 고강도 활동에서 추정
        target = ctx.scope_id
        td = date.fromisoformat(target)
        start = (td - timedelta(weeks=12)).isoformat()

        rows = ctx.conn.execute(
            "SELECT avg_pace_sec_km, moving_time_sec, avg_hr, max_hr "
            "FROM activity_summaries "
            "WHERE activity_type='running' "
            "AND moving_time_sec BETWEEN 1800 AND 4200 "
            "AND avg_pace_sec_km IS NOT NULL AND avg_pace_sec_km > 180 "
            "AND avg_hr IS NOT NULL AND max_hr IS NOT NULL AND max_hr > 0 "
            "AND CAST(avg_hr AS REAL) / CAST(max_hr AS REAL) >= 0.82 "
            "AND DATE(start_time) BETWEEN ? AND ? "
            "ORDER BY avg_pace_sec_km ASC LIMIT 5",
            (start, target),
        ).fetchall()

        if not rows:
            # 더 넓은 범위
            rows = ctx.conn.execute(
                "SELECT avg_pace_sec_km, moving_time_sec, avg_hr, max_hr "
                "FROM activity_summaries "
                "WHERE activity_type='running' "
                "AND moving_time_sec BETWEEN 1200 AND 5400 "
                "AND avg_pace_sec_km IS NOT NULL AND avg_pace_sec_km > 180 "
                "AND avg_hr IS NOT NULL AND max_hr IS NOT NULL AND max_hr > 0 "
                "AND CAST(avg_hr AS REAL) / CAST(max_hr AS REAL) >= 0.75 "
                "AND DATE(start_time) BETWEEN ? AND ? "
                "ORDER BY avg_pace_sec_km ASC LIMIT 5",
                (start, target),
            ).fetchall()

        if not rows:
            return []

        # 상위 3개 가중 평균
        top = rows[:3]
        total_weight = 0.0
        weighted_pace = 0.0
        for pace, dur, hr, max_hr in top:
            time_weight = max(0.3, 1.0 - abs(float(dur) - 3600) / 3600 * 0.5)
            weighted_pace += float(pace) * time_weight
            total_weight += time_weight

        if total_weight <= 0:
            return []

        eftp = round(weighted_pace / total_weight)
        return [self._result(
            value=eftp,
            confidence=0.65,
            json_value={
                "source": "estimated",
                "pace_sec_km": eftp,
                "sample_count": len(top),
            },
        )]

"""VDOT_ADJ — 현재 체력 기반 VDOT 보정.

A: 최근 역치런(avg_hr 85~92%) 활동 페이스 → T-pace 역산 → VDOT
B: HR-페이스 회귀 → HR 88%에서 예측 (fallback)
기본 VDOT 대비 ±7% 이내 클램핑.

v0.3 포팅: _v02_backup/vdot_adj.py → MetricCalculator 형식
"""
from __future__ import annotations

import math
from datetime import date, timedelta
from src.metrics.base import MetricCalculator, CalcResult, CalcContext


class VDOTAdjCalculator(MetricCalculator):
    name = "vdot_adj"
    provider = "runpulse:formula_v1"
    version = "1.0"
    scope_type = "daily"
    category = "rp_performance"
    requires = ["runpulse_vdot"]
    produces = ["vdot_adj"]

    display_name = "VDOT 보정"
    description = "역치 페이스 기반 현재 체력 VDOT 보정값"
    unit = ""
    ranges = {"beginner": 35, "intermediate": 45, "advanced": 55, "elite": 65}
    higher_is_better = True
    format_type = "number"
    decimal_places = 1

    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        vdot_base_val = ctx.get_metric("runpulse_vdot", provider="runpulse:formula_v1")
        if vdot_base_val is None:
            return []
        vdot_base = float(vdot_base_val)

        target = ctx.scope_id
        td = date.fromisoformat(target)
        start = (td - timedelta(weeks=12)).isoformat()

        # max_hr 추정
        hr_row = ctx.conn.execute(
            "SELECT MAX(max_hr) FROM activity_summaries "
            "WHERE max_hr IS NOT NULL AND max_hr > 100 "
            "AND DATE(start_time) BETWEEN ? AND ?",
            (start, target),
        ).fetchone()
        hr_max = float(hr_row[0]) if hr_row and hr_row[0] else 190.0

        # resting_hr
        wellness = ctx.get_wellness()
        resting_hr = float(wellness.get("resting_hr", 60)) if wellness else 60.0

        # HR 역치 범위 (Karvonen)
        if resting_hr > 30:
            hrr = hr_max - resting_hr
            hr_lo = resting_hr + hrr * 0.75
            hr_hi = resting_hr + hrr * 0.88
        else:
            hr_lo = hr_max * 0.85
            hr_hi = hr_max * 0.92

        # A: 역치런 활동 페이스
        threshold_pace = self._from_activities(ctx.conn, target, start, hr_lo, hr_hi)
        method = "threshold_activities" if threshold_pace else None

        # B: HR-페이스 회귀 fallback
        if threshold_pace is None:
            threshold_pace = self._from_regression(ctx.conn, target, start, hr_max)
            if threshold_pace:
                method = "hr_regression"

        if threshold_pace is None or threshold_pace < 120:
            return [self._result(
                value=vdot_base,
                confidence=0.5,
                json_val={"vdot_base": vdot_base, "method": "passthrough"},
            )]

        # T-pace → VDOT 역산
        from src.utils.daniels_table import t_pace_to_vdot
        vdot_adj = t_pace_to_vdot(threshold_pace)
        if vdot_adj is None:
            vdot_adj = vdot_base

        # ±7% 클램핑
        if vdot_base > 0:
            ratio = vdot_adj / vdot_base
            ratio = max(0.93, min(1.07, ratio))
            vdot_adj = round(vdot_base * ratio, 1)

        if vdot_adj < 15 or vdot_adj > 90:
            vdot_adj = vdot_base

        return [self._result(
            value=round(vdot_adj, 1),
            confidence=0.75 if method == "threshold_activities" else 0.55,
            json_val={
                "vdot_base": vdot_base,
                "threshold_pace": round(threshold_pace, 1),
                "method": method,
                "hr_range": f"{hr_lo:.0f}-{hr_hi:.0f}",
            },
        )]

    @staticmethod
    def _from_activities(conn, target, start, hr_lo, hr_hi):
        rows = conn.execute(
            "SELECT avg_pace_sec_km FROM activity_summaries "
            "WHERE activity_type='running' "
            "AND avg_hr BETWEEN ? AND ? "
            "AND moving_time_sec BETWEEN 1200 AND 3600 "
            "AND avg_pace_sec_km IS NOT NULL AND avg_pace_sec_km > 180 "
            "AND DATE(start_time) BETWEEN ? AND ?",
            (hr_lo, hr_hi, start, target),
        ).fetchall()
        if len(rows) < 3:
            return None
        paces = sorted([float(r[0]) for r in rows])
        q1 = len(paces) // 4
        q3 = len(paces) * 3 // 4
        trimmed = paces[q1:q3 + 1] if q3 > q1 else paces
        return sum(trimmed) / len(trimmed) if trimmed else None

    @staticmethod
    def _from_regression(conn, target, start, hr_max):
        rows = conn.execute(
            "SELECT avg_hr, avg_pace_sec_km FROM activity_summaries "
            "WHERE activity_type='running' AND avg_hr IS NOT NULL AND avg_hr > 100 "
            "AND avg_pace_sec_km IS NOT NULL AND avg_pace_sec_km > 180 "
            "AND distance_m >= 3000 AND DATE(start_time) BETWEEN ? AND ?",
            (start, target),
        ).fetchall()
        if len(rows) < 5:
            return None
        hrs = [float(r[0]) for r in rows]
        paces = [float(r[1]) for r in rows]
        n = len(hrs)
        sx, sy = sum(hrs), sum(paces)
        sxx = sum(h * h for h in hrs)
        sxy = sum(h * p for h, p in zip(hrs, paces))
        denom = n * sxx - sx * sx
        if abs(denom) < 1e-10:
            return None
        slope = (n * sxy - sx * sy) / denom
        intercept = (sy - slope * sx) / n
        predicted = slope * (hr_max * 0.88) + intercept
        return predicted if predicted > 120 else None

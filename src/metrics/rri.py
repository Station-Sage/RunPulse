"""RRI (Race Readiness Index) — 레이스 준비도 종합 지수.

공식: RRI = VDOT진행률 × CTL충족률 × DI계수 × 안전계수 × 100
0~100 스케일. 80+ 준비 완료, 60~80 보통, <60 부족.

v0.3 포팅: _v02_backup/rri.py → MetricCalculator 형식
"""
from __future__ import annotations

from src.metrics.base import MetricCalculator, CalcResult, CalcContext

_TARGET_CTL = {"5k": 25, "10k": 35, "half": 45, "full": 55}


class RRICalculator(MetricCalculator):
    name = "rri"
    provider = "runpulse:formula_v1"
    version = "1.0"
    scope_type = "daily"
    category = "rp_performance"
    requires = ["runpulse_vdot", "ctl", "di", "cirs"]
    produces = ["rri"]

    display_name = "RRI (레이스 준비도)"
    description = "VDOT/CTL/DI/CIRS 기반 레이스 준비도 종합 지수 (0~100)"
    unit = ""
    ranges = {"insufficient": 40, "building": 60, "ready": 80, "peak": 95}
    higher_is_better = True
    format_type = "number"
    decimal_places = 1

    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        vdot = ctx.get_metric("runpulse_vdot", provider="runpulse:formula_v1")
        ctl = ctx.get_metric("ctl", provider="runpulse:formula_v1")
        if vdot is None or ctl is None:
            return []

        vdot = float(vdot)
        ctl = float(ctl)

        # 목표: 현재 VDOT 대비 5% 향상, 하프마라톤 기준 CTL
        vdot_target = vdot * 1.05
        target_ctl = _TARGET_CTL["half"]

        # DI
        di_val = ctx.get_metric("di", provider="runpulse:formula_v1")
        di = float(di_val) if di_val is not None else None

        # CIRS
        cirs_val = ctx.get_metric("cirs", provider="runpulse:formula_v1")
        cirs = float(cirs_val) if cirs_val is not None else None

        # 계산
        vdot_pct = min(1.0, vdot / vdot_target) if vdot_target > 0 else 0.5
        ctl_pct = min(1.0, ctl / target_ctl) if target_ctl > 0 else 0.5
        di_factor = min(1.0, (di or 50) / 70)
        safety = (100 - min(100, cirs or 0)) / 100

        rri = vdot_pct * ctl_pct * di_factor * safety * 100
        rri = round(min(100, max(0, rri)), 1)

        return [self._result(
            value=rri,
            json_value={
                "vdot": round(vdot, 1),
                "vdot_target": round(vdot_target, 1),
                "ctl": round(ctl, 1),
                "target_ctl": target_ctl,
                "di": round(di, 1) if di else None,
                "cirs": round(cirs, 1) if cirs else None,
            },
        )]

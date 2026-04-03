"""SAPI (Seasonal-Adjusted Performance Index) — 계절·날씨 성과 비교.

기온 구간별 FEARP 평균을 비교하여 계절 영향을 정량화.
SAPI = (기준 FEARP / 현재 FEARP) × 100
- 100 = 기준과 동일, 100+ = 더 좋음, <100 = 저하

v0.3 포팅: _v02_backup/sapi.py → MetricCalculator 형식
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from src.metrics.base import MetricCalculator, CalcResult, CalcContext

_TEMP_BINS = [
    ("극한 추위", -20, 0),
    ("추움", 0, 10),
    ("적정 (기준)", 10, 15),
    ("따뜻함", 15, 25),
    ("더움", 25, 35),
    ("극한 더위", 35, 50),
]


class SAPICalculator(MetricCalculator):
    name = "sapi"
    provider = "runpulse:formula_v1"
    version = "1.0"
    scope_type = "daily"
    category = "rp_performance"
    requires = ["fearp"]
    produces = ["sapi"]

    display_name = "SAPI (계절 성과 지수)"
    description = "기온 구간별 FEARP 비교. 100=기준 동일, >100 더 빠름."
    unit = ""
    ranges = {"poor": [0, 85], "normal": [85, 100], "good": [100, 150]}
    higher_is_better = True
    format_type = "number"
    decimal_places = 1

    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        # NOTE: raw SQL 사용 — CalcContext API가 activity_type별 metric JOIN을 미지원
        target = ctx.scope_id
        td = date.fromisoformat(target)
        start = (td - timedelta(days=90)).isoformat()

        # FEARP + json (기온 정보 포함) — CalcContext API
        all_fearp = ctx.get_activity_metric_series("fearp", days=90, include_json=True)
        if len(all_fearp) < 3:
            return []
        rows = [(d["numeric"], d.get("json"), d["date"]) for d in all_fearp]

        # 기온 구간별 집계
        bin_data: dict[str, list[float]] = {b[0]: [] for b in _TEMP_BINS}
        for fearp_val, mj_raw, dt in rows:
            temp = self._extract_temp(mj_raw, ctx.conn, dt)
            if temp is None:
                continue
            for label, lo, hi in _TEMP_BINS:
                if lo <= temp < hi:
                    bin_data[label].append(float(fearp_val))
                    break

        # 기준 구간 평균
        ref_vals = bin_data.get("적정 (기준)", [])
        if not ref_vals:
            all_vals = [v for vals in bin_data.values() for v in vals]
            if not all_vals:
                return []
            ref_avg = sum(all_vals) / len(all_vals)
        else:
            ref_avg = sum(ref_vals) / len(ref_vals)

        if ref_avg <= 0:
            return []

        # 최근 7일 평균 FEARP
        recent_fearp = ctx.get_activity_metric_series("fearp", days=7)
        if not recent_fearp:
            return []
        current_avg = sum(d["numeric"] for d in recent_fearp) / len(recent_fearp)
        if current_avg <= 0:
            return []

        sapi = round(ref_avg / current_avg * 100, 1)

        bin_stats = {}
        for label, vals in bin_data.items():
            if vals:
                bin_stats[label] = {
                    "avg_fearp": round(sum(vals) / len(vals), 1),
                    "count": len(vals),
                }

        return [self._result(
            value=sapi,
            json_val={
                "ref_avg_fearp": round(ref_avg, 1),
                "current_avg_fearp": round(current_avg, 1),
                "bins": bin_stats,
            },
        
            confidence=1.0,
        )]

    @staticmethod
    def _extract_temp(mj_raw, conn, dt) -> float | None:
        if mj_raw:
            try:
                mj = json.loads(mj_raw) if isinstance(mj_raw, str) else mj_raw
                temp = mj.get("temperature") or mj.get("temp_c")
                if temp is not None:
                    return float(temp)
            except (json.JSONDecodeError, TypeError):
                pass
        try:
            row = conn.execute(
                "SELECT temperature FROM weather_cache "
                "WHERE date=? LIMIT 1", (dt,),
            ).fetchone()
            if row and row[0] is not None:
                return float(row[0])
        except Exception:
            pass
        return None

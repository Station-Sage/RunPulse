"""Jack Daniels VDOT 유틸 — 훈련 페이스·레이스 시간은 Daniels–Gilbert 공식(`metrics/prediction/daniels.py`)으로 계산,
권장 볼륨만 표 보간.

P7-PRED-85: 이전 페이스 표(VDOT_PACE_TABLE)는 공식과 불일치했다(표 T의 %VO2max가 VDOT 30→85에서 0.997→0.861로 변동,
공식은 60분 레이스 강도 고정). E = %VO2max 0.59~0.74 범위의 중간 속도, M = 마라톤 레이스, T = 60분 레이스,
I = vVO2max(%VO2max 1.0), R = 1마일 레이스 속도(400m 시간으로 반환).

v0.3 포팅: src/metrics/_v02_backup/daniels_table.py → src/utils/daniels_table.py
"""
from __future__ import annotations

import math
from typing import Any

from src.metrics.prediction.daniels import threshold_speed, zone_speeds
from src.metrics.prediction.daniels import vdot as _race_vdot

# ── VDOT → 권장 주간 볼륨 ────────────────────────────────────────────

VDOT_VOLUME_TABLE: list[dict[str, float]] = [
    {"vdot": 30, "weekly_min": 30, "weekly_max": 50, "long_max": 25, "long_threshold": 18},
    {"vdot": 35, "weekly_min": 35, "weekly_max": 60, "long_max": 28, "long_threshold": 20},
    {"vdot": 40, "weekly_min": 45, "weekly_max": 75, "long_max": 30, "long_threshold": 22},
    {"vdot": 45, "weekly_min": 55, "weekly_max": 85, "long_max": 32, "long_threshold": 25},
    {"vdot": 50, "weekly_min": 60, "weekly_max": 95, "long_max": 34, "long_threshold": 25},
    {"vdot": 55, "weekly_min": 70, "weekly_max": 110, "long_max": 35, "long_threshold": 28},
    {"vdot": 60, "weekly_min": 80, "weekly_max": 120, "long_max": 37, "long_threshold": 30},
    {"vdot": 65, "weekly_min": 90, "weekly_max": 130, "long_max": 38, "long_threshold": 32},
    {"vdot": 70, "weekly_min": 100, "weekly_max": 145, "long_max": 40, "long_threshold": 32},
]


# ── 보간 함수 ──────────────────────────────────────────────────────────

def _interpolate(table: list[dict], vdot: float, key: str) -> float | None:
    if not table:
        return None
    if vdot <= table[0]["vdot"]:
        return table[0].get(key)
    if vdot >= table[-1]["vdot"]:
        return table[-1].get(key)
    for i in range(len(table) - 1):
        lo, hi = table[i], table[i + 1]
        if lo["vdot"] <= vdot <= hi["vdot"]:
            v_lo, v_hi = lo.get(key), hi.get(key)
            if v_lo is None or v_hi is None:
                return v_lo or v_hi
            ratio = (vdot - lo["vdot"]) / (hi["vdot"] - lo["vdot"])
            return v_lo + (v_hi - v_lo) * ratio
    return None


# ── 공개 API ───────────────────────────────────────────────────────────

def get_training_paces(vdot: float) -> dict[str, int]:
    """VDOT → 훈련 페이스 (sec/km, R 은 400m 초). 예: VDOT 50 → {"E": 324, "M": 258, "T": 252, "I": 227, "R_400m": 86}"""
    if not vdot or vdot <= 0:
        return {}
    z = zone_speeds(vdot)
    e_speed = (z["E"][0] + z["E"][1]) / 2.0
    return {"E": round(1000 / e_speed), "M": round(1000 / z["M"]), "T": round(1000 / z["T"]),
            "I": round(1000 / z["I"]), "R_400m": round(400 / z["R"])}


def get_race_predictions(vdot: float) -> dict[str, int]:
    """VDOT → 레이스 예측 시간 (초). Daniels-Gilbert 공식으로 정확 계산."""
    _DISTANCES_M = {"5k": 5000, "10k": 10000, "half": 21097.5, "full": 42195}

    def _solve_time(vdot_val: float, dist_m: float) -> int | None:
        if vdot_val <= 0 or dist_m <= 0:
            return None
        lo, hi = 600.0, 21600.0
        for _ in range(50):
            mid = (lo + hi) / 2.0
            t_min = mid / 60.0
            v = dist_m / t_min
            vo2 = -4.60 + 0.182258 * v + 0.000104 * v * v
            pct = (0.8
                   + 0.1894393 * math.exp(-0.012778 * t_min)
                   + 0.2989558 * math.exp(-0.1932605 * t_min))
            calc_vdot = vo2 / pct if pct > 0 else 0
            if calc_vdot > vdot_val:
                lo = mid
            else:
                hi = mid
        return round((lo + hi) / 2.0)

    result = {}
    for key, dist in _DISTANCES_M.items():
        t = _solve_time(vdot, dist)
        if t:
            result[key] = t
    return result


def get_marathon_volume_targets(vdot: float) -> dict[str, float]:
    """VDOT → 마라톤 권장 볼륨."""
    result = {}
    for key in ("weekly_min", "weekly_max", "long_max", "long_threshold"):
        val = _interpolate(VDOT_VOLUME_TABLE, vdot, key)
        if val is not None:
            result[key] = round(val, 1)
    wmin = result.get("weekly_min", 50)
    wmax = result.get("weekly_max", 80)
    result["weekly_target"] = round((wmin + wmax) / 2, 1)
    return result


def get_race_volume_targets(vdot: float, race_km: float) -> dict[str, float]:
    """거리별 권장 볼륨 — 마라톤 기준에서 비례 축소."""
    base = get_marathon_volume_targets(vdot)
    if race_km <= 10.5:
        return {
            "weekly_target": round(base["weekly_target"] * 0.55, 1),
            "long_max": min(20.0, round(base["long_max"] * 0.55, 1)),
            "long_threshold": min(15.0, round(base.get("long_threshold", 20) * 0.6, 1)),
            "long_count_target": 4, "consistency_weeks": 6,
        }
    elif race_km <= 21.5:
        return {
            "weekly_target": round(base["weekly_target"] * 0.70, 1),
            "long_max": min(28.0, round(base["long_max"] * 0.72, 1)),
            "long_threshold": min(20.0, round(base.get("long_threshold", 22) * 0.75, 1)),
            "long_count_target": 5, "consistency_weeks": 8,
        }
    else:
        return {
            "weekly_target": base["weekly_target"],
            "long_max": base["long_max"],
            "long_threshold": base.get("long_threshold", 25),
            "long_count_target": 6, "consistency_weeks": 12,
        }


def vdot_to_t_pace(vdot: float) -> float | None:
    """VDOT → Daniels T-pace (sec/km) = 60분 레이스 페이스."""
    if not vdot or vdot <= 0:
        return None
    return round(1000 / threshold_speed(vdot), 1)


def t_pace_to_vdot(t_pace_sec_km: float) -> float | None:
    """Daniels T-pace(sec/km) → VDOT (60분 레이스 역산)."""
    if not t_pace_sec_km or t_pace_sec_km <= 0:
        return None
    return round(_race_vdot(1000 / t_pace_sec_km * 3600, 3600), 1)

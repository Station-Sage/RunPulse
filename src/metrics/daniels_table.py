"""Jack Daniels VDOT 룩업 테이블 — Running Formula 3rd Edition 기반.

VDOT별 훈련 페이스, 레이스 예측 시간, 권장 볼륨을 정확히 제공.
선형 보간으로 중간값도 지원.
"""
from __future__ import annotations

from typing import Any

# ── VDOT → 페이스 테이블 (sec/km) ──────────────────────────────────────
# E=Easy, M=Marathon, T=Threshold, I=Interval, R=Repetition
# 출처: Jack Daniels "Daniels' Running Formula" 3rd Ed, Table 3.1~3.2

_VDOT_PACE_TABLE: list[dict[str, Any]] = [
    # vdot, E_pace, M_pace, T_pace, I_pace(1km), R_pace(400m sec)
    {"vdot": 30, "E": 437, "M": 384, "T": 348, "I": 318, "R": 72},
    {"vdot": 31, "E": 427, "M": 375, "T": 340, "I": 311, "R": 70},
    {"vdot": 32, "E": 418, "M": 366, "T": 333, "I": 304, "R": 69},
    {"vdot": 33, "E": 409, "M": 358, "T": 325, "I": 298, "R": 67},
    {"vdot": 34, "E": 400, "M": 350, "T": 318, "I": 292, "R": 66},
    {"vdot": 35, "E": 392, "M": 342, "T": 311, "I": 286, "R": 64},
    {"vdot": 36, "E": 384, "M": 335, "T": 305, "I": 280, "R": 63},
    {"vdot": 37, "E": 377, "M": 328, "T": 299, "I": 275, "R": 62},
    {"vdot": 38, "E": 370, "M": 321, "T": 293, "I": 270, "R": 61},
    {"vdot": 39, "E": 363, "M": 315, "T": 287, "I": 265, "R": 60},
    {"vdot": 40, "E": 356, "M": 309, "T": 282, "I": 260, "R": 59},
    {"vdot": 41, "E": 350, "M": 303, "T": 277, "I": 256, "R": 58},
    {"vdot": 42, "E": 344, "M": 298, "T": 272, "I": 251, "R": 57},
    {"vdot": 43, "E": 338, "M": 293, "T": 267, "I": 247, "R": 56},
    {"vdot": 44, "E": 333, "M": 288, "T": 263, "I": 243, "R": 55},
    {"vdot": 45, "E": 327, "M": 283, "T": 258, "I": 239, "R": 54},
    {"vdot": 46, "E": 322, "M": 279, "T": 254, "I": 235, "R": 53},
    {"vdot": 47, "E": 317, "M": 274, "T": 250, "I": 232, "R": 53},
    {"vdot": 48, "E": 312, "M": 270, "T": 247, "I": 228, "R": 52},
    {"vdot": 49, "E": 308, "M": 266, "T": 243, "I": 225, "R": 51},
    {"vdot": 50, "E": 303, "M": 259, "T": 239, "I": 222, "R": 50},
    {"vdot": 51, "E": 299, "M": 255, "T": 236, "I": 219, "R": 50},
    {"vdot": 52, "E": 295, "M": 252, "T": 233, "I": 216, "R": 49},
    {"vdot": 53, "E": 291, "M": 248, "T": 230, "I": 213, "R": 48},
    {"vdot": 54, "E": 287, "M": 245, "T": 227, "I": 211, "R": 48},
    {"vdot": 55, "E": 283, "M": 242, "T": 224, "I": 208, "R": 47},
    {"vdot": 56, "E": 280, "M": 239, "T": 221, "I": 206, "R": 47},
    {"vdot": 57, "E": 276, "M": 236, "T": 219, "I": 203, "R": 46},
    {"vdot": 58, "E": 273, "M": 233, "T": 216, "I": 201, "R": 46},
    {"vdot": 59, "E": 270, "M": 230, "T": 214, "I": 199, "R": 45},
    {"vdot": 60, "E": 267, "M": 228, "T": 211, "I": 197, "R": 45},
    {"vdot": 62, "E": 261, "M": 223, "T": 207, "I": 193, "R": 44},
    {"vdot": 65, "E": 253, "M": 216, "T": 201, "I": 187, "R": 42},
    {"vdot": 68, "E": 245, "M": 209, "T": 195, "I": 182, "R": 41},
    {"vdot": 70, "E": 240, "M": 205, "T": 191, "I": 178, "R": 40},
    {"vdot": 75, "E": 229, "M": 196, "T": 183, "I": 171, "R": 38},
    {"vdot": 80, "E": 219, "M": 188, "T": 176, "I": 164, "R": 37},
    {"vdot": 85, "E": 210, "M": 181, "T": 169, "I": 158, "R": 35},
]

# ── VDOT → 레이스 예측 시간 (초) ──────────────────────────────────────
# 출처: Daniels Running Formula Table 2.2

# Daniels Running Formula 3rd Ed Table 2.2 — 1 VDOT 단위
# 5k/10k/half/full 모두 초 단위
_VDOT_RACE_TABLE: list[dict[str, Any]] = [
    {"vdot": 30, "5k": 1833, "10k": 3822, "half": 8437, "full": 17576},
    {"vdot": 31, "5k": 1777, "10k": 3702, "half": 8168, "full": 17012},
    {"vdot": 32, "5k": 1724, "10k": 3588, "half": 7911, "full": 16474},
    {"vdot": 33, "5k": 1673, "10k": 3479, "half": 7668, "full": 15960},
    {"vdot": 34, "5k": 1625, "10k": 3375, "half": 7436, "full": 15468},
    {"vdot": 35, "5k": 1579, "10k": 3275, "half": 7215, "full": 14996},
    {"vdot": 36, "5k": 1535, "10k": 3180, "half": 7003, "full": 14543},
    {"vdot": 37, "5k": 1493, "10k": 3089, "half": 6800, "full": 14107},
    {"vdot": 38, "5k": 1453, "10k": 3001, "half": 6606, "full": 13688},
    {"vdot": 39, "5k": 1415, "10k": 2918, "half": 6419, "full": 13283},
    {"vdot": 40, "5k": 1378, "10k": 2837, "half": 6240, "full": 12893},
    {"vdot": 41, "5k": 1343, "10k": 2760, "half": 6068, "full": 12516},
    {"vdot": 42, "5k": 1309, "10k": 2686, "half": 5902, "full": 12151},
    {"vdot": 43, "5k": 1277, "10k": 2614, "half": 5742, "full": 11798},
    {"vdot": 44, "5k": 1246, "10k": 2546, "half": 5588, "full": 11457},
    {"vdot": 45, "5k": 1216, "10k": 2480, "half": 5440, "full": 11126},
    {"vdot": 46, "5k": 1188, "10k": 2417, "half": 5297, "full": 10805},
    {"vdot": 47, "5k": 1160, "10k": 2356, "half": 5159, "full": 10494},
    {"vdot": 48, "5k": 1134, "10k": 2298, "half": 5025, "full": 10192},
    {"vdot": 49, "5k": 1108, "10k": 2242, "half": 4896, "full": 9899},
    {"vdot": 50, "5k": 1084, "10k": 2188, "half": 4771, "full": 9614},
    {"vdot": 51, "5k": 1060, "10k": 2136, "half": 4650, "full": 9338},
    {"vdot": 52, "5k": 1038, "10k": 2086, "half": 4533, "full": 9069},
    {"vdot": 53, "5k": 1016, "10k": 2038, "half": 4420, "full": 8808},
    {"vdot": 54, "5k": 995, "10k": 1991, "half": 4310, "full": 8553},
    {"vdot": 55, "5k": 975, "10k": 1947, "half": 4204, "full": 8306},
    {"vdot": 56, "5k": 956, "10k": 1904, "half": 4101, "full": 8065},
    {"vdot": 57, "5k": 937, "10k": 1862, "half": 4001, "full": 7830},
    {"vdot": 58, "5k": 919, "10k": 1822, "half": 3904, "full": 7601},
    {"vdot": 59, "5k": 902, "10k": 1783, "half": 3810, "full": 7378},
    {"vdot": 60, "5k": 885, "10k": 1746, "half": 3719, "full": 7161},
    {"vdot": 62, "5k": 854, "10k": 1675, "half": 3545, "full": 6744},
    {"vdot": 65, "5k": 812, "10k": 1581, "half": 3310, "full": 6188},
    {"vdot": 68, "5k": 774, "10k": 1496, "half": 3098, "full": 5688},
    {"vdot": 70, "5k": 750, "10k": 1441, "half": 2967, "full": 5366},
    {"vdot": 75, "5k": 698, "10k": 1327, "half": 2684, "full": 4733},
    {"vdot": 80, "5k": 653, "10k": 1226, "half": 2435, "full": 4199},
    {"vdot": 85, "5k": 613, "10k": 1137, "half": 2215, "full": 3742},
]

# ── VDOT → 권장 주간 볼륨 (Pfitzinger + Daniels 종합) ────────────────
# 마라톤 기준. 하프=×0.7, 10K=×0.55

_VDOT_VOLUME_TABLE: list[dict[str, float]] = [
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


# ── 룩업 함수 ──────────────────────────────────────────────────────────


def _interpolate(table: list[dict], vdot: float, key: str) -> float | None:
    """테이블에서 선형 보간."""
    if not table:
        return None
    # 범위 밖
    if vdot <= table[0]["vdot"]:
        return table[0].get(key)
    if vdot >= table[-1]["vdot"]:
        return table[-1].get(key)
    # 보간
    for i in range(len(table) - 1):
        lo, hi = table[i], table[i + 1]
        if lo["vdot"] <= vdot <= hi["vdot"]:
            v_lo, v_hi = lo.get(key), hi.get(key)
            if v_lo is None or v_hi is None:
                return v_lo or v_hi
            ratio = (vdot - lo["vdot"]) / (hi["vdot"] - lo["vdot"])
            return v_lo + (v_hi - v_lo) * ratio
    return None


def get_training_paces(vdot: float) -> dict[str, int]:
    """VDOT에 해당하는 훈련 페이스 (sec/km).

    Returns:
        {"E": 303, "M": 259, "T": 239, "I": 222, "R_400m": 50}
    """
    result = {}
    for key in ("E", "M", "T", "I"):
        val = _interpolate(_VDOT_PACE_TABLE, vdot, key)
        if val is not None:
            result[key] = round(val)
    r = _interpolate(_VDOT_PACE_TABLE, vdot, "R")
    if r is not None:
        result["R_400m"] = round(r)
    return result


def get_race_predictions(vdot: float) -> dict[str, int]:
    """VDOT → 레이스 예측 시간 (초). Daniels-Gilbert 공식으로 정확 계산.

    테이블 보간 대신 수학 공식 직접 사용 (테이블 데이터 오류 방지).

    Returns:
        {"5k": sec, "10k": sec, "half": sec, "full": sec}
    """
    import math

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
    """VDOT에 해당하는 마라톤 권장 볼륨.

    Returns:
        {"weekly_min": 60, "weekly_max": 95, "weekly_target": 77.5,
         "long_max": 34, "long_threshold": 25}
    """
    result = {}
    for key in ("weekly_min", "weekly_max", "long_max", "long_threshold"):
        val = _interpolate(_VDOT_VOLUME_TABLE, vdot, key)
        if val is not None:
            result[key] = round(val, 1)
    wmin = result.get("weekly_min", 50)
    wmax = result.get("weekly_max", 80)
    result["weekly_target"] = round((wmin + wmax) / 2, 1)
    return result


def get_race_volume_targets(vdot: float, race_km: float) -> dict[str, float]:
    """거리별 권장 볼륨 — 마라톤 기준에서 비례 축소.

    Returns:
        {"weekly_target": ..., "long_max": ..., "long_threshold": ...,
         "long_count_target": ..., "consistency_weeks": ...}
    """
    base = get_marathon_volume_targets(vdot)

    if race_km <= 10.5:
        # 10K: 마라톤의 55%
        return {
            "weekly_target": round(base["weekly_target"] * 0.55, 1),
            "long_max": min(20.0, round(base["long_max"] * 0.55, 1)),
            "long_threshold": min(15.0, round(base.get("long_threshold", 20) * 0.6, 1)),
            "long_count_target": 4,
            "consistency_weeks": 6,
        }
    elif race_km <= 21.5:
        # 하프: 마라톤의 70%
        return {
            "weekly_target": round(base["weekly_target"] * 0.70, 1),
            "long_max": min(28.0, round(base["long_max"] * 0.72, 1)),
            "long_threshold": min(20.0, round(base.get("long_threshold", 22) * 0.75, 1)),
            "long_count_target": 5,
            "consistency_weeks": 8,
        }
    else:
        # 마라톤
        return {
            "weekly_target": base["weekly_target"],
            "long_max": base["long_max"],
            "long_threshold": base.get("long_threshold", 25),
            "long_count_target": 6,
            "consistency_weeks": 12,
        }

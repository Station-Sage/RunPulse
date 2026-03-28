"""인터벌 트레이닝 처방 계산.

논문 근거:
  - Billat 2001 (Sports Medicine 31:13-31)
    · vVO2max 강도: 휴식 비율 1:1, 반복당 60초 이상 권장
    · 회복 조깅: vVO2max의 60% 속도 (능동 회복이 수동보다 우수)
    · 세션 총 볼륨: tmax(최대 지속 시간)의 80%
  - Buchheit & Laursen 2013 (Sports Medicine 43:313-338, 43:927-954)
    · 반복 거리별 총 볼륨 권장치 및 강도(%vVO2max) 범위
    · 200m(30초): 10~20세트, 총 2~4km
    · 400m(60초): 6~10세트, 총 2.4~4km
    · 600~1000m(2~3분): 4~6세트, 총 2.4~6km
    · 1200~2000m(4~5분): 3~5세트, 총 3.6~10km
  - Daniels Running Formula 3rd Ed: I-pace 처방

표준 반복 거리 (m): 200, 300, 320, 400, 600, 800, 1000, 1200, 1600, 2000
사용자 임의 입력 가능 (예: 320m 등 비표준 거리).

반환 구조:
    {
        "rep_m": int,          # 반복 거리 (m)
        "sets": int,           # 세트 수
        "rest_sec": int,       # 세트 간 휴식 (초)
        "interval_pace": int,  # 반복 페이스 (sec/km, Daniels I-pace)
        "recovery_pace": int,  # 회복 조깅 페이스 (sec/km, Billat: I-pace * 1/0.6)
        "rep_duration_sec": int,   # 반복 예상 시간 (초)
        "total_volume_m": int,     # 총 인터벌 거리 (m)
        "session_duration_min": int, # 전체 세션 예상 시간 (분)
        "rationale": str,          # 처방 근거 설명
        "warning": str | None,     # 사용자 입력이 비표준인 경우 안내
    }
"""
from __future__ import annotations

import math


# ── 표준 거리별 Buchheit & Laursen 2013 처방 기준표 ──────────────────────

# (min_rep_m, max_rep_m): (min_sets, max_sets, intensity_pct_vVO2max, total_vol_km_min, total_vol_km_max)
_BUCHHEIT_ZONES: list[tuple] = [
    # rep_m 범위, 세트 범위, vVO2max%, 총 거리 범위(km)
    (150,  250, 10, 20, 120, 2.0, 4.0),   # ~30초, SIT/짧은 HIIT
    (251,  500,  6, 10, 110, 2.4, 4.0),   # ~60초, 400m 표준
    (501, 1100,  4,  6, 102, 2.4, 6.0),   # ~2~3분, 600~1000m
    (1101, 2100, 3,  5,  97, 3.6, 10.0),  # ~4~5분, 1200~2000m
]

# 최소 반복당 지속시간 (Billat 2001: 60초 이상이어야 VO2max 자극)
_MIN_REP_DURATION_SEC = 60

# 표준 거리 목록 (참고용, 비표준 입력 시 경고만)
_STANDARD_DISTANCES_M = {200, 300, 400, 600, 800, 1000, 1200, 1600, 2000}


def _find_buchheit_zone(rep_m: int) -> tuple[int, int, int, float, float]:
    """반복 거리에 해당하는 Buchheit 처방 구간 반환.

    Returns:
        (min_sets, max_sets, intensity_pct, total_km_min, total_km_max)
    """
    for zone_min, zone_max, s_min, s_max, intensity, vol_min, vol_max in _BUCHHEIT_ZONES:
        if zone_min <= rep_m <= zone_max:
            return s_min, s_max, intensity, vol_min, vol_max
    # 범위 초과: 가장 가까운 구간 fallback
    if rep_m < 150:
        return 12, 20, 120, 1.5, 3.0
    return 2, 4, 95, 2.0, 8.0


def _calc_rep_duration(rep_m: int, interval_pace_sec_km: int) -> int:
    """반복 거리 + I-pace → 반복 예상 시간 (초)."""
    return round(rep_m / 1000 * interval_pace_sec_km)


def _calc_rest_sec(rep_duration_sec: int, rep_m: int) -> int:
    """휴식 시간 계산.

    근거:
    - Billat 2001: vVO2max 강도에서 1:1 비율 (운동=휴식)
    - Buchheit & Laursen 2013 Part 2: 짧은 반복(<400m)은 휴식 30~45초,
      긴 반복(>800m)은 운동 시간의 50~100%

    구간별 적용:
    - rep_m <= 400: max(45, rep_duration * 0.75)  # 짧은 인터벌, 약간 짧게
    - rep_m <= 800: rep_duration * 0.85            # 중간
    - rep_m > 800 : rep_duration * 1.0             # Billat 1:1 기준
    """
    if rep_m <= 400:
        rest = max(45, round(rep_duration_sec * 0.75))
    elif rep_m <= 800:
        rest = round(rep_duration_sec * 0.85)
    else:
        rest = round(rep_duration_sec * 1.0)  # Billat 1:1
    return rest


def _calc_recovery_pace(interval_pace_sec_km: int) -> int:
    """회복 조깅 페이스 계산.

    Billat 2001: 회복 속도 = vVO2max의 60%.
    속도는 역수이므로: recovery_pace = interval_pace / 0.6
    """
    return round(interval_pace_sec_km / 0.6)


def _calc_sets(rep_m: int, min_sets: int, max_sets: int,
               total_km_min: float, total_km_max: float,
               rep_duration_sec: int) -> int:
    """세트 수 결정.

    우선: 총 볼륨 목표 중간값 달성 최적 세트 수.
    Billat 2001: 세션 볼륨은 tmax의 80% — tmax 데이터 없으므로
    Buchheit 총 거리 중간값으로 근사.
    """
    target_km = (total_km_min + total_km_max) / 2
    target_m = target_km * 1000
    ideal_sets = round(target_m / rep_m)
    # Buchheit 권장 세트 범위 내로 클리핑
    sets = max(min_sets, min(max_sets, ideal_sets))

    # Billat 2001: 반복당 60초 미만이면 세트 수 늘려 총 시간 보완
    if rep_duration_sec < _MIN_REP_DURATION_SEC:
        extra = math.ceil(_MIN_REP_DURATION_SEC / max(1, rep_duration_sec))
        sets = max(sets, extra * 2)

    return sets


def prescribe_interval(
    rep_m: int,
    interval_pace_sec_km: int,
    eftp_sec_km: int | None = None,
) -> dict:
    """인터벌 처방 계산.

    Args:
        rep_m: 반복 거리 (m). 200~2000 권장, 비표준(예:320m)도 허용.
        interval_pace_sec_km: Daniels I-pace (sec/km). VDOT_ADJ 기반 권장.
        eftp_sec_km: eFTP (sec/km). 페이스 검증용 (I-pace는 eFTP*0.9 근방).

    Returns:
        처방 딕셔너리 (모듈 docstring 참조).
    """
    rep_m = max(100, int(rep_m))

    min_sets, max_sets, intensity_pct, vol_min, vol_max = _find_buchheit_zone(rep_m)
    rep_duration_sec = _calc_rep_duration(rep_m, interval_pace_sec_km)
    rest_sec = _calc_rest_sec(rep_duration_sec, rep_m)
    recovery_pace = _calc_recovery_pace(interval_pace_sec_km)
    sets = _calc_sets(rep_m, min_sets, max_sets, vol_min, vol_max, rep_duration_sec)
    total_volume_m = rep_m * sets

    # 웜업(10분) + 쿨다운(10분) + 인터벌 세션
    interval_block_sec = sets * (rep_duration_sec + rest_sec) - rest_sec
    session_duration_min = round((600 + interval_block_sec + 600) / 60)

    # 근거 문자열
    rep_min = rep_duration_sec // 60
    rep_sec = rep_duration_sec % 60
    rest_min = rest_sec // 60
    rest_s = rest_sec % 60
    rationale = (
        f"{rep_m}m x {sets}세트 (총 {total_volume_m/1000:.1f}km). "
        f"반복 예상 시간 {rep_min}:{rep_sec:02d}, "
        f"세트 간 휴식 {rest_min}:{rest_s:02d} (회복 조깅). "
        f"강도 ~{intensity_pct}% vVO2max. "
        f"출처: Buchheit & Laursen 2013 총 볼륨 {vol_min}~{vol_max}km 기준, "
        f"Billat 2001 휴식 비율."
    )

    # 비표준 거리 경고
    warning: str | None = None
    if rep_m not in _STANDARD_DISTANCES_M:
        nearest = min(_STANDARD_DISTANCES_M, key=lambda d: abs(d - rep_m))
        warning = (
            f"{rep_m}m는 비표준 거리입니다. "
            f"트랙에서는 가장 가까운 {nearest}m 사용을 권장합니다."
        )

    # eFTP 페이스 검증 (I-pace ≈ eFTP * 0.88~0.93, Daniels 기준)
    if eftp_sec_km and interval_pace_sec_km:
        ratio = interval_pace_sec_km / eftp_sec_km
        if ratio > 0.95:  # I-pace가 eFTP보다 너무 느림
            warning = (warning or "") + (
                f" 설정 I-pace({interval_pace_sec_km}s/km)가 eFTP({eftp_sec_km}s/km)보다 "
                f"느립니다. VDOT_ADJ 기반 I-pace 재확인을 권장합니다."
            )

    return {
        "rep_m": rep_m,
        "sets": sets,
        "rest_sec": rest_sec,
        "interval_pace": interval_pace_sec_km,
        "recovery_pace": recovery_pace,
        "rep_duration_sec": rep_duration_sec,
        "total_volume_m": total_volume_m,
        "session_duration_min": session_duration_min,
        "rationale": rationale,
        "warning": warning,
        "buchheit_range": {"vol_min_km": vol_min, "vol_max_km": vol_max,
                           "intensity_pct": intensity_pct},
    }


def prescribe_from_vdot(
    rep_m: int,
    vdot: float,
    eftp_sec_km: int | None = None,
) -> dict:
    """VDOT 기반 I-pace 자동 조회 후 처방.

    Args:
        rep_m: 반복 거리 (m).
        vdot: VDOT_ADJ 값.
        eftp_sec_km: eFTP (검증용).
    """
    from src.metrics.daniels_table import get_training_paces
    paces = get_training_paces(vdot)
    i_pace = paces.get("I", 240)  # fallback 4:00/km
    return prescribe_interval(rep_m, int(i_pace), eftp_sec_km)

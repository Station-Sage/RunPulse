"""HR 프로필 자체 추정 + 기상 보조 계산(순수 함수)."""
from __future__ import annotations

import math


def hrmax_self(activity_max_hrs: list[float]) -> float | None:
    """최근 365일 활동별 최대 HR 목록 → 두 번째로 큰 값(단일 스파이크 배제). 120 초과 205 이하만."""
    v = sorted((x for x in activity_max_hrs if x and 120 < x <= 205), reverse=True)
    if not v:
        return None
    return float(v[1] if len(v) >= 2 else v[0])


def lthr_self(race_second_part_hrs: list[tuple[float, float]]) -> float | None:
    """[(대회 공칭거리 m, 후반 2/3 평균 HR)] (최근 180일 전력 10K~하프) → 보정 후 중앙값.
    10K: ×0.98, 하프: ×1.00. 없으면 None."""
    c = []
    for dist, hr in race_second_part_hrs:
        if abs(dist - 10000) < 1:
            c.append(hr * 0.98)
        elif abs(dist - 21097.5) < 1:
            c.append(hr * 1.00)
    if not c:
        return None
    c.sort()
    m = len(c) // 2
    return c[m] if len(c) % 2 else (c[m - 1] + c[m]) / 2


def lthr_fallback(hrmax: float | None) -> float | None:
    return round(0.917 * hrmax, 1) if hrmax else None


def zones_hrr(hrmax: float, rhr: float) -> list[tuple[float, float]]:
    """Karvonen 5존 경계(bpm): 50-60, 60-70, 70-80, 80-90, 90-100 %HRR."""
    r = hrmax - rhr
    cuts = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    return [(round(rhr + r * a, 1), round(rhr + r * b, 1)) for a, b in zip(cuts, cuts[1:])]


def zones_lthr(lthr: float) -> list[tuple[float, float]]:
    """Friel 러닝 5존(%LTHR): <85, 85-90, 90-95, 95-100, ≥100."""
    cuts = [0.0, 0.85, 0.90, 0.95, 1.00]
    z = [(round(lthr * a, 1), round(lthr * b, 1)) for a, b in zip(cuts, cuts[1:])]
    return z + [(round(lthr, 1), 250.0)]


def vapor_pressure_hpa(temp_c: float, rh_pct: float) -> float:
    return rh_pct / 100.0 * 6.105 * math.exp(17.27 * temp_c / (237.7 + temp_c))


def wbgt_approx(temp_c: float, rh_pct: float) -> float:
    """호주 기상청(BoM) 그늘·약풍 근사: WBGT ≈ 0.567·T + 0.393·e + 3.94."""
    return 0.567 * temp_c + 0.393 * vapor_pressure_hpa(temp_c, rh_pct) + 3.94


def ambient_from_device(device_c: float) -> float:
    """손목 기기 온도 → 외기 추정. 이 러너 261개 활동 적합: device ≈ 11.0 + 0.65·ambient."""
    return (device_c - 11.0) / 0.65


def round_coord(x: float) -> float:
    """외부 전송용 좌표 정밀도 축소(소수 2자리 ≈ 1km)."""
    return round(x, 2)

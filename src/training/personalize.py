"""개인화 규칙(순수) — 복귀 구간 램프율과 시작 롱런 (DESIGN-U16-PLAN-ENGINE §3.2, v2 전용).

DB를 읽지 않는다. 입력은 직전 4주·16주 평균 km, 6주·12주 최장 km.
복귀 구간(직전 4주 평균 < 0.6 × 직전 16주 평균)은 이미 해본 볼륨으로 돌아가는 것이라 16주 평균에 닿을 때까지 0.15를 허용한다.
"""
from __future__ import annotations

RAMP_DEFAULT = 0.10
RAMP_COMEBACK = 0.15
COMEBACK_RATIO = 0.6
LONG12_FACTOR = 0.85


def is_comeback(prev4_avg: float, avg16: float) -> bool:
    """직전 4주 평균이 직전 16주 평균의 60% 미만이면 복귀 구간. 16주 기록이 없으면 False."""
    return avg16 > 0 and prev4_avg < COMEBACK_RATIO * avg16


def comeback_ceiling(prev4_avg: float, avg16: float) -> float:
    """0.15 램프를 쓸 수 있는 주간 km 상한(= 16주 평균). 복귀 구간이 아니면 0."""
    return avg16 if is_comeback(prev4_avg, avg16) else 0.0


def next_level(level: float, peak_km: float, ceiling: float = 0.0) -> float:
    """다음 부하주 주간 km(내림 전). level < ceiling 이면 ceiling 까지는 +15%, 넘는 부분은 +10%. peak_km 로 자른다."""
    if ceiling > 0 and level < ceiling:
        step = min(level * (1 + RAMP_COMEBACK), max(ceiling, level * (1 + RAMP_DEFAULT)))
    else:
        step = level * (1 + RAMP_DEFAULT)
    return min(peak_km, step)


def start_long_km(long6: float, long12: float) -> float:
    """시작 롱런 = 직전 6주 최장과 12주 최장 × 0.85 중 큰 값(일시적 공백에 롱런이 리셋되지 않게)."""
    return max(long6, LONG12_FACTOR * long12)

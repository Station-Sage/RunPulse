"""HR존 및 페이스존 계산 유틸리티."""


# HR존 경계 비율 (max_hr 기준)
_HR_ZONE_BOUNDS = [
    (0.50, 0.60),  # Zone 1: 회복
    (0.60, 0.70),  # Zone 2: 유산소 기초
    (0.70, 0.80),  # Zone 3: 유산소 강화
    (0.80, 0.90),  # Zone 4: 젖산 역치
    (0.90, 1.00),  # Zone 5: VO2Max
]

# 페이스존 배수 (threshold_pace 기준, 높은 값 = 느린 페이스)
_PACE_ZONE_BOUNDS = [
    (1.25, 1.40),  # Zone 1: Easy
    (1.10, 1.25),  # Zone 2: Aerobic
    (1.00, 1.10),  # Zone 3: Tempo
    (0.95, 1.00),  # Zone 4: Threshold
    (0.85, 0.95),  # Zone 5: VO2Max
]


def hr_zones(max_hr: int) -> list[tuple[int, int]]:
    """5존 HR 범위 반환.

    Args:
        max_hr: 최대 심박수.

    Returns:
        [(low, high), ...] 5개 존 리스트.
    """
    return [
        (round(max_hr * low), round(max_hr * high))
        for low, high in _HR_ZONE_BOUNDS
    ]


def get_hr_zone(hr: int, max_hr: int) -> int:
    """주어진 HR이 몇 존인지 반환.

    Args:
        hr: 현재 심박수.
        max_hr: 최대 심박수.

    Returns:
        존 번호 (1~5). 범위 밖이면 0 또는 5.
    """
    if hr <= 0 or max_hr <= 0:
        return 0
    ratio = hr / max_hr
    for i, (low, high) in enumerate(_HR_ZONE_BOUNDS, 1):
        if ratio < high:
            return i
    return 5


def pace_zones(threshold_pace: int) -> list[tuple[int, int]]:
    """임계 페이스 기반 5존 페이스 범위 반환.

    Args:
        threshold_pace: 젖산 역치 페이스 (sec/km).

    Returns:
        [(fast, slow), ...] 5개 존 리스트. 값이 작을수록 빠른 페이스.
    """
    return [
        (round(threshold_pace * low), round(threshold_pace * high))
        for low, high in _PACE_ZONE_BOUNDS
    ]


def get_pace_zone(pace_sec: int, threshold_pace: int) -> int:
    """주어진 페이스가 몇 존인지 반환.

    Args:
        pace_sec: 현재 페이스 (sec/km).
        threshold_pace: 젖산 역치 페이스 (sec/km).

    Returns:
        존 번호 (1~5). 범위 밖이면 1(매우 느림) 또는 5(매우 빠름).
    """
    if pace_sec <= 0 or threshold_pace <= 0:
        return 0
    ratio = pace_sec / threshold_pace
    # 높은 ratio = 느린 페이스 = 낮은 존
    for i, (low, high) in enumerate(_PACE_ZONE_BOUNDS, 1):
        if low <= ratio <= high:
            return i
    # 범위 밖: 매우 느리면 Zone 1, 매우 빠르면 Zone 5
    return 1 if ratio > _PACE_ZONE_BOUNDS[0][1] else 5

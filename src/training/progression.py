"""품질 세션 진행 사다리(순수) — 유형별 단계 정수와 R5 라벨 기반 승급·유지·강등 (DESIGN-U16 §3.3).

DB를 읽지 않는다. 다음 단계 규칙: 직전 같은 유형 세션이 on_target/over 면 +1, under/missed 면 유지,
연속 2회 under 면 -1. 단계는 0..len-1 로 자른다.
"""
from __future__ import annotations

LONG_MP_KM = (6, 8, 10, 12, 14, 16)
TEMPO = ((3, 1.6), (4, 1.6), (3, 3.2), (2, 4.8), (1, 0.0))   # (반복, km) — 마지막은 연속 25분
INTERVAL = ((5, 1.0), (6, 1.0), (5, 1.2), (4, 1.6))
TEMPO_CONT_MIN = 25
LADDERS = {"long_mp": LONG_MP_KM, "tempo": TEMPO, "interval": INTERVAL}
_UP = ("on_target", "over")
_HOLD = ("under", "missed")


def max_step(qtype: str) -> int:
    return len(LADDERS[qtype]) - 1


def next_step(qtype: str, step: int, labels: list[str]) -> tuple[int, str]:
    """labels: 같은 유형 세션의 R5 라벨(오래된 것 → 최신). 반환: (다음 단계, 사유)."""
    top = max_step(qtype)
    step = max(0, min(step, top))
    if not labels:
        return step, "no_history"
    last = labels[-1]
    if len(labels) >= 2 and labels[-1] == labels[-2] == "under":
        return max(0, step - 1), "down_2under"
    if last in _UP:
        return min(top, step + 1), "up"
    if last in _HOLD:
        return step, "hold"
    return step, "hold_other"


def prescription(qtype: str, step: int) -> dict:
    """단계 → 처방 구조. long_mp {mp_km}, tempo {reps, rep_km | continuous_min}, interval {reps, rep_km}."""
    ladder = LADDERS[qtype]
    v = ladder[max(0, min(step, len(ladder) - 1))]
    if qtype == "long_mp":
        return {"mp_km": float(v)}
    reps, km = v
    if qtype == "tempo" and km == 0.0:
        return {"continuous_min": TEMPO_CONT_MIN}
    return {"reps": reps, "rep_km": km}

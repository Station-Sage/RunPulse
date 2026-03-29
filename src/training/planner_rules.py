"""훈련 계획 — 훈련 단계·볼륨·Q-day·페이스·볼륨 배분·설명 규칙.

planner.py에서 분리. 순수 규칙/계산 함수만 포함 (DB 직접 접근 없음).
"""
from __future__ import annotations

from datetime import date

from .planner_config import (
    LONG_RUN_BASE,
    LONG_RUN_PHASE_FACTOR,
    PHASE_VOLUME_FACTOR,
    Q_TYPES,
    TYPE_WEIGHT,
)

# ── 훈련 단계 결정 ────────────────────────────────────────────────────────

def weeks_to_race(race_date_str: str | None) -> int | None:
    if not race_date_str:
        return None
    try:
        delta = (date.fromisoformat(race_date_str) - date.today()).days
        return max(0, delta // 7)
    except ValueError:
        return None


def training_phase(weeks_left: int | None, week_idx: int) -> str:
    """훈련 단계 결정.

    3:1 회복주(week_idx==3)이면 단계와 무관하게 'recovery_week' 표시.
    """
    if week_idx == 3:
        return "recovery_week"  # Foster 1998 3:1 사이클
    if weeks_left is None or weeks_left > 16:
        return "base"
    if weeks_left > 8:
        return "build"
    if weeks_left > 3:
        return "peak"
    return "taper"


# ── 주간 볼륨 계산 ────────────────────────────────────────────────────────

def resolve_distance_label(goal_distance_km: float,
                           distance_label: str | None) -> str:
    """거리 레이블 결정."""
    if distance_label and distance_label in LONG_RUN_BASE:
        return distance_label
    if goal_distance_km >= 40:   return "full"
    if goal_distance_km >= 18:   return "half"
    if goal_distance_km >= 8:    return "10k"
    if goal_distance_km >= 4:    return "5k"
    if goal_distance_km >= 2.5:  return "3k"
    return "1.5k"


def weekly_volume_km(ctl: float, phase: str, tsb: float,
                     shape_pct: float | None) -> float:
    """주간 목표 거리 계산.

    근거:
    - CTL → 기본 볼륨 (Coggan 2003 / Banister 1991)
    - Pfitzinger 방식: 절대값 상한 병행 (주간 최대 증가 20km)
    - TSB 보정: Coggan 2003 TSB < -30 과훈련 경계
    - MarathonShape 보정: 현재 훈련 완성도가 낮으면 볼륨 조정
    """
    if ctl < 20:
        base = 25.0
    elif ctl < 40:
        base = 30.0 + (ctl - 20) * 0.80
    elif ctl < 60:
        base = 46.0 + (ctl - 40) * 0.90
    else:
        base = 64.0 + min(ctl - 60, 25) * 0.5

    if phase == "recovery_week":
        volume = base * 0.70
    else:
        volume = base * PHASE_VOLUME_FACTOR.get(phase, 1.0)

    if tsb < -30:
        volume *= 0.78
    elif tsb < -20:
        volume *= 0.88
    elif tsb > 15:
        volume *= 1.05

    if shape_pct is not None and shape_pct < 40:
        volume *= 0.85

    return round(volume, 1)


# ── Q-day 배치 (Hard-Easy 원칙) ───────────────────────────────────────────

def assign_qday_slots(available_days: list[int], n_q: int,
                      label: str, phase: str) -> list[int]:
    """Q-day 요일 인덱스 선택.

    Hard-Easy 원칙 (Lydiard/Bowerman): Q-day 사이 최소 1일 간격.
    Long run은 주말(5=토, 6=일) 우선 배치.
    """
    if not available_days or n_q == 0:
        return []

    selected: list[int] = []
    last_q = -2

    candidates = [d for d in available_days if d > available_days[0]]
    for d in candidates:
        if len(selected) >= n_q:
            break
        if d - last_q >= 2:
            selected.append(d)
            last_q = d

    return sorted(selected)


def assign_long_run_slot(available_days: list[int],
                         q_slots: list[int]) -> int | None:
    """Long run 배치: 주말 가용일 우선, Q-day와 겹치지 않게."""
    prefer = [d for d in available_days if d >= 5 and d not in q_slots]
    if prefer:
        return prefer[-1]
    others = [d for d in available_days if d not in q_slots]
    return others[-1] if others else None


# ── 페이스 처방 (Daniels VDOT 테이블) ────────────────────────────────────

def get_paces_from_vdot(vdot: float | None,
                        config: dict | None) -> dict[str, int]:
    """VDOT_ADJ → E/T/I/R 페이스 (sec/km).

    VDOT 없으면 eFTP 기반 fallback, 없으면 config threshold_pace fallback.
    """
    if vdot and vdot > 20:
        try:
            from src.metrics.daniels_table import get_training_paces
            return get_training_paces(vdot)
        except Exception:
            pass

    tp = 300
    if config:
        tp_cfg = config.get("user", {}).get("threshold_pace_sec_km")
        if tp_cfg:
            try:
                tp = int(tp_cfg)
            except (ValueError, TypeError):
                pass
    return {
        "E": tp + 75, "M": tp + 20, "T": tp,
        "I": tp - 30, "R": tp - 55,
    }


def pace_range(workout_type: str, paces: dict[str, int]) -> tuple[int | None, int | None]:
    """훈련 유형 → 페이스 범위 (min, max) sec/km."""
    mapping = {
        "easy":     ("E", 30),
        "long":     ("E", 30),
        "recovery": ("E", 50),
        "tempo":    ("T", 10),
        "interval": ("I", 10),
        "rest":     None,
    }
    spec = mapping.get(workout_type)
    if spec is None:
        return None, None
    key, delta = spec
    base = paces.get(key, 300)
    return base - delta, base + delta


# ── 볼륨 배분 ─────────────────────────────────────────────────────────────

def distribute_volume(template: list[str], total_km: float,
                      long_km: float) -> list[float | None]:
    """타입별 거리 배분.

    Long run 고정 후 Seiler 80/20 원칙:
    - 전체 볼륨 중 Q-day(tempo+interval) 비중 ≤ 20%
    - 나머지 80%를 easy/recovery에 배분
    """
    dists: list[float | None] = []
    long_count = template.count("long")
    q_max_km = total_km * 0.20
    long_total = long_km * long_count
    remaining = max(0.0, total_km - long_total)

    non_rest = [t for t in template if t not in ("rest", "long")]
    q_types = [t for t in non_rest if t in Q_TYPES]
    e_types = [t for t in non_rest if t not in Q_TYPES]

    q_weight_sum = sum(TYPE_WEIGHT.get(t, 1.0) for t in q_types)
    e_weight_sum = sum(TYPE_WEIGHT.get(t, 1.0) for t in e_types)
    total_weight = q_weight_sum + e_weight_sum

    q_budget = min(q_max_km, remaining * q_weight_sum / total_weight) if total_weight else 0
    e_budget = remaining - q_budget

    type_km: dict[str, float] = {}
    if q_weight_sum > 0:
        for t in Q_TYPES:
            w = TYPE_WEIGHT.get(t, 1.0)
            cnt = q_types.count(t)
            if cnt:
                type_km[t] = round(q_budget * w / q_weight_sum, 1)
    if e_weight_sum > 0:
        for t in ("easy", "recovery"):
            w = TYPE_WEIGHT.get(t, 1.0)
            cnt = e_types.count(t)
            if cnt:
                type_km[t] = round(e_budget * w / e_weight_sum, 1)

    for wtype in template:
        if wtype == "rest":
            dists.append(None)
        elif wtype == "long":
            dists.append(long_km)
        else:
            km = type_km.get(wtype, 5.0)
            dists.append(max(2.0, km))

    return dists


# ── 설명/근거 ─────────────────────────────────────────────────────────────

TYPE_NAMES = {
    "easy": "이지런", "tempo": "템포런", "interval": "인터벌",
    "long": "장거리런", "rest": "휴식", "recovery": "회복조깅",
}

RATIONALE = {
    "rest":
        "충분한 회복. 다음 훈련 품질을 높입니다.",
    "recovery":
        "극저강도 회복 조깅 (HR Zone 1). 혈류 촉진으로 피로 물질 제거.",
    "easy":
        "저강도 유산소 (HR Zone 2). Seiler 2010: 전체 볼륨의 80% 이상 유지.",
    "tempo":
        "젖산 역치 훈련 (HR Zone 3~4). Daniels T-pace 유지. 20~60분 연속.",
    "interval":
        "VO2max 자극 (HR Zone 4~5). Billat 2001: 반복당 60초+ 유지.",
    "long":
        "지구력 기반 장거리 (HR Zone 2). 대화 가능 페이스. "
        "Daniels: E-pace 유지. Friel: 디커플링 5% 이하 목표.",
}


def description(wtype: str, dist: float | None, day: date) -> str:
    day_names = ["월", "화", "수", "목", "금", "토", "일"]
    dn = day_names[day.weekday()]
    if wtype == "rest":
        return f"{dn}요일 휴식"
    name = TYPE_NAMES.get(wtype, wtype)
    dist_str = f"{dist:.1f}km " if dist else ""
    return f"{dn}요일 {dist_str}{name}"

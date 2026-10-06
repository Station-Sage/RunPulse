"""목표 대회 역산 주기화(순수) — 대회 주에서 거꾸로 감량·피크·빌드 구간을 배치하고 주간 거리·롱런을 점진 증가시킨다.

  - 마지막 taper_weeks 주(대회 주 포함)는 감량, 그 앞은 base(40%)·build(35%)·peak(25%).
  - 볼륨은 현재 수준(start_km)에서 시작해 주 +10% 이하로 늘려 peak_km 까지(Pfitzinger/Daniels 관용). 3:1 — 4번째 부하주는
    직전 수준의 80% 회복주(레벨은 유지), 단 피크 주(마지막 훈련 주)는 회복주로 두지 않는다.
  - 롱런은 현재 최장에서 시작해 부하주마다 long_step 씩(회복주는 75%), 상한은 거리별 최대·주간 거리의 비율.
  - 감량: 마지막 부하 수준 대비 주별 비율(taper_weeks 3 → 75/60/45%). 감량 첫 주만 롱런(피크의 65%), 이후 없음.
근거를 두는 상수는 여기 한 곳에 모아 두었다 — 개인화 조정은 이 값만 바꾼다.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Callable

from . import personalize as P

# long_cap(phase, weeks_to_race, week_km, sched_long_km, prev_long_km) → 그 주 롱런 상한(long_run_rules.long_cap_km)
LongCapFn = Callable[[str, int, float, float, float], float]

RAMP = 0.10                 # 부하주 간 주간 거리 최대 증가율
RECOVERY_FACTOR = 0.80      # 3:1 회복주 볼륨 (Foster 1998)
LONG_RECOVERY_FACTOR = 0.75
LONG_STEP = 2.0             # 부하주마다 롱런 증가(km)
TAPER_FACTORS = {1: [0.55], 2: [0.70, 0.50], 3: [0.75, 0.60, 0.45]}   # Mujika & Padilla 2003: 40~60% 감소
TAPER_LONG_FACTOR = 0.65
FULL_TAPER_V2 = [0.70, 0.50]            # v2 풀: 2주 (U16i)
FULL_TAPER3_MIN_WEEKS, FULL_TAPER3_MIN_PEAK_KM = 16, 80.0
D14_LONG_RANGE = (20.0, 24.0)           # 대회 2주 전 주말 롱런(km)


@dataclass(frozen=True)
class WeekTarget:
    index: int               # 0-based, 계획 시작 주 기준
    weeks_to_race: int       # 대회 주 = 0
    phase: str               # base | build | peak | recovery_week | taper
    weekly_km: float         # 대회일 자체를 제외한 그 주 목표 거리
    long_km: float           # 0 이면 롱런 없음


def _phase(i: int, n_train: int) -> str:
    base_end, build_end = int(n_train * 0.40), int(n_train * 0.75)
    return "base" if i < base_end else "build" if i < build_end else "peak"


def _down(x: float) -> float:
    return math.floor(x * 10 + 1e-6) / 10


def build_schedule(total_weeks: int, start_km: float, start_long_km: float, peak_km: float, long_max_km: float,
                   long_cap_ratio: float, taper_weeks: int, rules_version: int = 1,
                   max_week_km: float | None = None, long_cap: LongCapFn | None = None,
                   comeback_ceiling: float = 0.0) -> list[WeekTarget]:
    """total_weeks 주 계획(마지막 주 = 대회 주)의 주별 목표. 입력이 비정상이면 빈 리스트.

    max_week_km: 주 러닝 일수로 소화 가능한 상한 — 시작·피크 볼륨을 이 값으로 자른다.
    rules_version 2: taper_weeks>=3(풀)이면 2주(0.70/0.50)로 줄이고, 16주 이상·피크 80km 이상일 때만 3주.
    감량 주에는 롱런을 두지 않고(MP 세션은 marathon_rules), 대회 2주 전 주말에 20~24km 롱런(상한 이내)을 둔다.
    v2 볼륨은 반올림된 직전 주 값 × 1.10을 0.1km 내림(R7). long_cap(v2)이 있으면 롱런은 매주 공유 상한
    (진행 상한 포함)으로 자른 값에서 다음 주 +2km 진행한다(DESIGN-U16-LONGRUN §6.3).
    comeback_ceiling(v2, personalize): 이 km 에 닿을 때까지 부하주 증가율 15%(복귀 구간), 넘는 부분은 10%.
    """
    if total_weeks < 1 or start_km <= 0:
        return []
    if max_week_km:       # 러닝 일수로 소화 가능한 주간 상한(week_structure.feasible_week_km)
        start_km, peak_km = min(start_km, max_week_km), min(peak_km, max_week_km)
    v2_full = rules_version >= 2 and taper_weeks >= 3
    if v2_full and not (total_weeks >= FULL_TAPER3_MIN_WEEKS and peak_km >= FULL_TAPER3_MIN_PEAK_KM):
        taper_weeks = 2
    taper_weeks = max(0, min(taper_weeks, total_weeks))
    n_train = total_weeks - taper_weeks
    v2 = rules_version >= 2
    cap_fn = long_cap if v2 else None
    out: list[WeekTarget] = []
    level, long_level = (_down(start_km) if v2 else start_km), max(start_long_km, 0.0)
    long_level = long_level if cap_fn else min(long_level, long_max_km)
    prev_max = 0.0
    for i in range(n_train):
        recovery = (i + 1) % 4 == 0 and i < n_train - 1
        phase, to_race = "recovery_week" if recovery else _phase(i, n_train), total_weeks - 1 - i
        if i > 0 and not recovery:
            level = _down(P.next_level(level, peak_km, comeback_ceiling)) if v2 else min(peak_km, level * (1 + RAMP))
            long_level = long_level + LONG_STEP if cap_fn else min(long_max_km, long_level + LONG_STEP)
        vol = level * (RECOVERY_FACTOR if recovery else 1.0)
        lng = long_level * (LONG_RECOVERY_FACTOR if recovery else 1.0)
        if cap_fn:      # 매주 공유 상한으로 자른 값을 다음 주 진행의 출발점으로 둔다
            cap = cap_fn(phase, to_race, round(vol, 1), lng, prev_max)
            long_level = long_level if recovery else min(long_level, cap)
            lng = min(lng, cap)
        else:
            lng = min(lng, vol * long_cap_ratio)
        prev_max = max(prev_max, round(lng, 1))
        out.append(WeekTarget(i, to_race, phase, round(vol, 1), round(lng, 1)))
    peak_level, peak_long = level, long_level
    factors = FULL_TAPER_V2 if v2_full and taper_weeks == 2 else TAPER_FACTORS.get(taper_weeks, [0.5] * taper_weeks)
    for k in range(taper_weeks):
        i = n_train + k
        has_long = k == 0 and taper_weeks >= 2 and not v2_full
        vol = peak_level * factors[k]
        lng = peak_long * TAPER_LONG_FACTOR if has_long else 0.0
        if has_long:
            lng = min(lng, cap_fn("taper", total_weeks - 1 - i, round(vol, 1), lng, prev_max) if cap_fn
                      else vol * long_cap_ratio)
        out.append(WeekTarget(i, total_weeks - 1 - i, "taper", round(vol, 1), round(lng, 1)))
    if v2_full:
        out = [_with_d14_long(w, long_cap_ratio, cap_fn, max((x.long_km for x in out[:w.index]), default=0.0))
               if w.weeks_to_race == 2 else w for w in out]
    return out


def _with_d14_long(w: WeekTarget, cap_ratio: float, cap_fn: LongCapFn | None = None, prev_max: float = 0.0) -> WeekTarget:
    """대회 2주 전 롱런 20~24km. cap_fn 이 있으면 공유 상한(진행 상한 포함)을 넘지 않는다."""
    lo, hi = D14_LONG_RANGE
    want = min(max(w.long_km, lo), hi)
    cap = cap_fn(w.phase, w.weeks_to_race, w.weekly_km, want, prev_max) if cap_fn else w.weekly_km * cap_ratio
    return replace(w, long_km=round(min(want, cap), 1))


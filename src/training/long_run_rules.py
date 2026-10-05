"""롱런 하한·상한 규칙(순수) — 엔진 후처리·주기화·게이트가 같은 함수를 부른다 (DESIGN-U16-LONGRUN §3~§5).

DB를 읽지 않는다. 입력은 주 단위 문맥 LongCtx 이고, 거리 단위는 km, 페이스는 초/km.
상수 표는 이 파일 한 곳에 둔다(표값은 대중 계획의 단계별 최소 롱런을 반올림한 가정치, 설계서 §3.3).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

MIN_SESSION_KM = 6.0            # 일반 세션 최소(G3)
EASY_MAX_KM = 12.0              # 이지 세션 상한(week_structure.EASY_FILL_MAX_KM)
QUALITY_KM = 6.0                # 퀄리티 세션 가정 거리(feasible_week_km)
MP_SESSION_KM = 8.0             # G4 MP 구간 하한
MP_EXTRA_KM = 5.0               # 별도 MP 세션(11km) − 일반 세션(6km)
DEFAULT_LONG_PACE = 360.0       # MP가 없을 때 롱런 페이스(실사용 경로에서는 M 페이스가 항상 있음)
LONG_PACE_BAND = 10.0           # 롱런 처방 페이스 범위 = 롱런 페이스 ± 10초

LONG_ABS_MIN = {"full": 12.0, "half": 10.0, "10k": 8.0, "5k": 8.0}
PHASE_FLOOR = {
    "full": {"base": 16.0, "build": 20.0, "peak": 24.0, "recovery_week": 14.0, "taper": 12.0},
    "half": {"base": 12.0, "build": 14.0, "peak": 16.0, "recovery_week": 10.0, "taper": 10.0},
    "10k": {"base": 10.0, "build": 12.0, "peak": 14.0, "recovery_week": 8.0, "taper": 8.0},
    "5k": {"base": 8.0, "build": 10.0, "peak": 10.0, "recovery_week": 8.0, "taper": 8.0},
}
D14_FLOOR = 20.0                # 풀 v2 대회 2주 전 롱런 하한
ENV_LOW_DAYS, ENV_HIGH_DAYS = 0.70, 0.60    # 하한의 주간 대비 외피(n ≤ 2 / n ≥ 3)
R_DEFAULT, R_HIGH, R_HIGH_WEEK_KM = 0.35, 0.45, 60.0     # D-U16-4
R_DAYS = {1: 1.0, 2: 0.60, 3: 0.50, 4: 0.45}
R_FULL = {"build": 0.50, "peak": 0.50}
R_MAX = 0.60
TIME_CAP_MIN = {"full": 150.0, "half": 150.0, "10k": 120.0, "5k": 120.0}
FULL_TIME_CAP_MIN = {"build": 180.0, "peak": 180.0}
ABS_CAP = {"full": 32.0, "half": 24.0, "10k": 20.0, "5k": 16.0}
FULL_ABS_HIGH, FULL_ABS_HIGH_WEEK, FULL_ABS_HIGH_LONG = 35.0, 90.0, 30.0
PROG_STEP_KM, PROG_STEP_RATIO = 2.0, 0.10
BASIS_LONG12 = 0.85
_EPS = 1e-6


@dataclass(frozen=True)
class LongCtx:
    """한 주의 롱런 판정 문맥. 엔진이 주별로 기록하고 게이트가 같은 함수로 다시 계산한다."""
    dlabel: str
    phase: str
    weeks_to_race: int
    week_km: float
    run_days: int
    long_pace_sec: float = DEFAULT_LONG_PACE
    sched_long_km: float = 0.0          # 주기화가 정한 롱런
    long6: float = 0.0                  # 직전 6주 최장
    long12: float = 0.0                 # 직전 12주 최장
    taper_first: bool = False
    prev_long_km: float | None = None   # 계획 내 직전 최장(주기화에서만, 진행 상한)
    mp_extra_km: float = 0.0            # 예산에 넣은 별도 MP 세션 추가분(엔진 결정 기록)


@dataclass(frozen=True)
class LongBudget:
    run_days: int
    floor_km: float          # 예산 반영 하한(롱런 없는 주면 0)
    has_long: bool
    mp_in_long: bool
    mp_extra_km: float


def _d(dlabel: str) -> str:
    return dlabel if dlabel in LONG_ABS_MIN else "10k"


def _down(x: float) -> float:
    """0.1km 단위 내림(부동소수 오차 보정)."""
    return math.floor(x * 10 + _EPS) / 10


def abs_min_km(dlabel: str) -> float:
    return LONG_ABS_MIN[_d(dlabel)]


def basis_km(ctx: LongCtx) -> float:
    """이력 기준 롱런 = max(6주 최장, 0.85 × 12주 최장)."""
    return max(ctx.long6, BASIS_LONG12 * ctx.long12)


def time_cap_km(ctx: LongCtx) -> float:
    d = _d(ctx.dlabel)
    minutes = FULL_TIME_CAP_MIN.get(ctx.phase, TIME_CAP_MIN[d]) if d == "full" else TIME_CAP_MIN[d]
    pace = ctx.long_pace_sec if ctx.long_pace_sec and ctx.long_pace_sec > 0 else DEFAULT_LONG_PACE
    return minutes * 60.0 / pace


def abs_cap_km(ctx: LongCtx) -> float:
    d = _d(ctx.dlabel)
    if d == "full" and ctx.week_km >= FULL_ABS_HIGH_WEEK and ctx.long12 >= FULL_ABS_HIGH_LONG:
        return FULL_ABS_HIGH
    return ABS_CAP[d]


def share_ratio(ctx: LongCtx) -> float:
    """비중 r = min(0.60, max(r_base, R_DAYS[n], 풀 build/peak 0.50))."""
    hi = ctx.week_km < R_HIGH_WEEK_KM and ctx.long12 >= R_HIGH * ctx.week_km
    r = max(R_HIGH if hi else R_DEFAULT, R_DAYS.get(ctx.run_days, 0.0))
    if _d(ctx.dlabel) == "full":
        r = max(r, R_FULL.get(ctx.phase, 0.0))
    return min(R_MAX, r)


def long_floor_km(ctx: LongCtx) -> float:
    """§3.2 하한 — 표값을 이력·스케줄 이상으로 강제하지 않고, 주간 외피·시간·절대 상한을 넘지 않는다."""
    d = _d(ctx.dlabel)
    f0 = D14_FLOOR if d == "full" and ctx.weeks_to_race == 2 else PHASE_FLOOR[d].get(ctx.phase, LONG_ABS_MIN[d])
    f1 = max(LONG_ABS_MIN[d], min(f0, max(ctx.sched_long_km, basis_km(ctx))))
    env = ENV_LOW_DAYS if ctx.run_days <= 2 else ENV_HIGH_DAYS
    f2 = min(f1, max(LONG_ABS_MIN[d], env * ctx.week_km))
    return _down(min(f2, time_cap_km(ctx), abs_cap_km(ctx)))


def prog_cap_km(ctx: LongCtx) -> float | None:
    """진행 상한 = max(계획 내 직전 최장, basis) + max(2km, 10%). 주기화 문맥(prev_long_km)에서만."""
    if ctx.prev_long_km is None:
        return None
    ref = max(ctx.prev_long_km, basis_km(ctx))
    return ref + max(PROG_STEP_KM, PROG_STEP_RATIO * ref)


def long_cap_km(ctx: LongCtx) -> float:
    """§4.1 상한 = min(max(비중×주간, 하한), 시간 상한, 절대 상한, 진행 상한)."""
    cands = [max(share_ratio(ctx) * ctx.week_km, long_floor_km(ctx)), time_cap_km(ctx), abs_cap_km(ctx)]
    prog = prog_cap_km(ctx)
    if prog is not None:
        cands.append(prog)
    return min(cands)


def min_viable_week_km(dlabel: str, run_days: int) -> float:
    """롱런(절대 최소) + 6km 세션 (n−1)회를 담을 수 있는 최소 주간 km."""
    return abs_min_km(dlabel) + MIN_SESSION_KM * (max(1, run_days) - 1)


def budget_floor_km(ctx: LongCtx) -> float:
    """§5.1-4 예산 반영 하한 = min(하한, max(절대 최소, 주간 − (n−1)×6 − MP 추가분))."""
    room = ctx.week_km - (ctx.run_days - 1) * MIN_SESSION_KM - ctx.mp_extra_km
    return min(long_floor_km(ctx), max(abs_min_km(ctx.dlabel), _down(room)))


def _mp_extra(ctx: LongCtx, floor: float, mp_week: bool) -> float:
    """별도 MP 세션이 필요한 주(풀 테이퍼 1주차, 또는 하한 롱런에 MP 8km를 못 담는 주)만 +5km."""
    from .marathon_rules import long_mp_km
    if not mp_week:
        return 0.0
    return MP_EXTRA_KM if ctx.phase == "taper" or long_mp_km(floor, ctx.phase) < MP_SESSION_KM else 0.0


def plan_long_budget(ctx: LongCtx, mp_week: bool = False) -> LongBudget:
    """§5.1 예산 처리: 일수 감소 → MP를 롱런 안으로 → 하한 완화 → 롱런 없는 저볼륨 주. 비교는 정확값."""
    def need(n: int, f: float, x: float) -> float:
        return f + (n - 1) * MIN_SESSION_KM + x

    def at(n: int) -> LongCtx:
        return LongCtx(**{**ctx.__dict__, "run_days": n})

    w, n = ctx.week_km, max(1, ctx.run_days)
    f = long_floor_km(at(n))
    x = _mp_extra(ctx, f, mp_week)
    while n > 2 and need(n, f, x) > w + _EPS:
        n -= 1
        f = long_floor_km(at(n))
        x = _mp_extra(ctx, f, mp_week)
    mp_in_long = False
    if x and need(n, f, x) > w + _EPS and ctx.phase in ("build", "peak"):
        x, mp_in_long = 0.0, True
    if need(n, f, x) > w + _EPS:
        f = max(abs_min_km(ctx.dlabel), _down(w - (n - 1) * MIN_SESSION_KM - x))
    if need(n, f, x) > w + _EPS:
        return LongBudget(min(n, max(1, int(w // MIN_SESSION_KM))), 0.0, False, False, 0.0)
    return LongBudget(n, f, True, mp_in_long, x)


def feasible_week_km(dlabel: str, run_days: int, long_pace_sec: float = DEFAULT_LONG_PACE) -> float:
    """D-LR-8(B): 러닝 일수로 소화 가능한 주간 최대 km — 피크 롱런 공유 상한 + 퀄리티 6km + 이지 12km×(n−2)."""
    n = max(1, run_days)
    others = (n - 2) * EASY_MAX_KM + QUALITY_KM if n >= 2 else 0.0

    def fits(wk: float) -> bool:
        ctx = LongCtx(dlabel, "peak", 3, wk, n, long_pace_sec)
        return long_cap_km(ctx) + others >= wk - _EPS

    lo, hi = 0.0, 300.0         # fits 는 wk 에 대해 단조 감소(상한 항이 비중 이상으로 늘지 않음) → 이분 탐색
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if fits(mid) else (lo, mid)
    return _down(lo)

"""롱런 게이트(순수) — G2a 공유 상한·G2b 외피·G9 하한·F6 진행 (DESIGN-U16-LONGRUN §4.4).

G2a·G9는 엔진이 기록한 WeekPlan.long_ctx 로 long_run_rules 의 같은 함수를 다시 계산한다. 기록이 없는 주(v1 등)는
관찰값(주간 km·일수·단계·롱런 거리)으로 문맥을 만든다. G2b 상수는 long_run_rules 와 독립으로 여기에 둔다.
"""
from __future__ import annotations

from . import long_run_rules as LR
from .plan_gates import LONG_TOL_KM, GateResult, WeekPlan, _result

FLOOR_TOL_KM = 0.05
CTX_KM_TOL, CTX_PACE_TOL = 0.1, 1.0
ENV_SHARE_LOW, ENV_SHARE_HIGH = 0.70, 0.60     # 롱런 ≤ 비중×주간(2일 이하 / 3일 이상)
ENV_MAX_MIN, ENV_MAX_KM = 200.0, 35.5
ENV_DEFAULT_PACE = 360.0
PROG_TOL_KM = 0.5
_EPS = 1e-9               # 부동소수 경계(0.6×36+0.5 = 22.1 통과)
_LONG = ("long", "long_mp")
_NO_LONG = ("1.5k", "3k")


def _long_session(w: WeekPlan):
    return max((s for s in w.days if s.type in _LONG), key=lambda s: s.km, default=None)


def week_ctx(w: WeekPlan, dlabel: str, long6: float = 0.0, long12: float = 0.0) -> LR.LongCtx:
    """기록된 문맥, 없으면 관찰값으로 만든 문맥(롱런 페이스 = 처방 하단 + 10초, 없으면 360)."""
    if w.long_ctx is not None:
        return w.long_ctx
    s = _long_session(w)
    lp = s.pace_sec + LR.LONG_PACE_BAND if s is not None and s.pace_sec else LR.DEFAULT_LONG_PACE
    return LR.LongCtx(dlabel, w.phase, w.weeks_to_race, w.km, w.run_days, lp, w.long_km, long6, long12)


def _ctx_mismatch(w: WeekPlan) -> str:
    c, s = w.long_ctx, _long_session(w)
    if c is None:
        return ""
    if abs(c.week_km - w.km) > CTX_KM_TOL:
        return f"주간 {w.km:.1f} != 기록 {c.week_km:.1f}"
    if c.run_days != w.run_days or c.phase != w.phase:
        return f"일수/단계 {w.run_days}/{w.phase} != 기록 {c.run_days}/{c.phase}"
    if s is not None and s.pace_sec is not None and abs(s.pace_sec - round(c.long_pace_sec - LR.LONG_PACE_BAND)) > CTX_PACE_TOL:
        return f"롱런 페이스 {s.pace_sec:.0f} != 기록 {c.long_pace_sec:.0f}−{LR.LONG_PACE_BAND:.0f}"
    return ""


def g2a_long_cap(weeks: list[WeekPlan], dlabel: str, long6: float = 0.0, long12: float = 0.0) -> GateResult:
    """롱런 ≤ long_cap_km(ctx) + 0.5. 기록 문맥이 관찰과 다르면 위반."""
    bad = []
    for w in weeks:
        if w.long_km <= 0:
            continue
        miss = _ctx_mismatch(w)
        if miss:
            bad.append(f"w{w.index}: 문맥 불일치 — {miss}")
            continue
        cap = LR.long_cap_km(week_ctx(w, dlabel, long6, long12))
        if w.long_km > cap + LONG_TOL_KM + _EPS:
            bad.append(f"w{w.index}: 롱런 {w.long_km:.1f} > {cap:.1f}+{LONG_TOL_KM}")
    return _result("G2a", bad)


def g2b_long_envelope(weeks: list[WeekPlan]) -> GateResult:
    """엔진과 무관한 외피: 롱런 ≤ 0.60(3일 이상)/0.70(2일 이하)×주간 + 0.5, ≤ 200분, ≤ 35.5km."""
    bad = []
    for w in weeks:
        s = _long_session(w)
        if s is None or s.km <= 0:
            continue
        share = ENV_SHARE_HIGH if w.run_days >= 3 else ENV_SHARE_LOW
        minutes = s.km * (s.pace_sec or ENV_DEFAULT_PACE) / 60.0
        if s.km > share * w.km + LONG_TOL_KM + _EPS:
            bad.append(f"w{w.index}: 롱런 {s.km:.1f} > {share:.2f}×{w.km:.1f}+{LONG_TOL_KM}")
        elif minutes > ENV_MAX_MIN + _EPS or s.km > ENV_MAX_KM + _EPS:
            bad.append(f"w{w.index}: 롱런 {s.km:.1f}km/{minutes:.0f}분 외피 초과")
    return _result("G2b", bad)


def g9_long_floor(weeks: list[WeekPlan], dlabel: str, long6: float = 0.0, long12: float = 0.0) -> GateResult:
    """테이퍼가 아닌 주: 롱런 ≥ budget_floor_km(ctx) − 0.05 이고 ≥ 절대 최소. 주간 ≥ min_viable 인데 롱런이 없으면 위반."""
    if dlabel in _NO_LONG:
        return GateResult("G9")
    bad = []
    for w in weeks:
        if w.weeks_to_race <= 0 or w.phase == "taper":
            continue
        if w.long_km <= 0:     # 롱런 주는 최소 2일(롱런 + 세션, §5.1-1) — 1일 주는 2일 기준으로 판정
            viable = LR.min_viable_week_km(dlabel, max(2, w.run_days))
            if w.km >= viable - _EPS:
                bad.append(f"w{w.index}: 주간 {w.km:.1f} ≥ {viable:.0f}인데 롱런 없음")
            continue
        floor = max(LR.budget_floor_km(week_ctx(w, dlabel, long6, long12)), LR.abs_min_km(dlabel))
        if w.long_km < floor - FLOOR_TOL_KM - _EPS:
            bad.append(f"w{w.index}: 롱런 {w.long_km:.1f} < 하한 {floor:.1f}")
    return _result("G9", bad)


def f6_long_step(weeks: list[WeekPlan], long12: float) -> GateResult:
    """소프트: 롱런_k ≤ max(계획 내 직전 최장, 12주 최장) + max(2km, 10%) + 0.5."""
    bad, prev = [], 0.0
    for w in weeks:
        ref = max(prev, long12)
        lim = ref + max(LR.PROG_STEP_KM, LR.PROG_STEP_RATIO * ref) + PROG_TOL_KM
        if w.long_km > 0 and ref > 0 and w.long_km > lim + _EPS:
            bad.append(f"w{w.index}: 롱런 {w.long_km:.1f} > {lim:.1f}")
        prev = max(prev, w.long_km)
    return _result("F6", bad)

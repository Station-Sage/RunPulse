"""목표 대회 역산 주간 목표 조회 — 최근 훈련량(DB)을 읽어 periodization.build_schedule 에 넣는다.

계획 시작 직전 4주의 주평균 거리와 최근 6주 최장 러닝이 출발점이라, 같은 계획을 언제 다시 만들어도 같은 결과가 나온다.
v2 콜드스타트(직전 4주 평균 < 12km 또는 기록 없음)는 DESIGN-U16-LONGRUN §5.2 출처로 시작 부하를 정한다(v1은 기존대로 빈 일정).
"""
from __future__ import annotations

import math
import sqlite3
from datetime import date, timedelta

from . import long_run_rules as LR
from . import marathon_rules as MR
from . import personalize as P
from .goals import get_reported_load, get_rules_version
from .periodization import WeekTarget, build_schedule
from .plan_readiness import cold_peak_km
from .planner_config import DISTANCE_LABEL_KM, LONG_RUN_BASE, load_prefs
from .planner_rules import get_paces_from_vdot, plan_start_monday
from .week_structure import feasible_week_km
from .readiness import get_taper_weeks, recommend_weekly_km

_RUN = "('running','run','virtualrun','treadmill','highintensityintervaltraining')"
_LONG_CAP = {"full": 0.50, "half": 0.50}      # 그 외 0.40
COLD_WEEK_KM = 12.0                           # 이 미만이면 콜드스타트(6km 세션 2회 미만)
W_COLD = {"5k": 12.0, "10k": 12.0, "half": 16.0, "full": 20.0}   # 기록 없음 기본 시작 부하
DETRAIN_FACTOR = 0.6                          # 직전 16주 평균 할인(가정)


def recent_load(conn: sqlite3.Connection, as_of: date) -> tuple[float, float]:
    """(as_of 직전 4주 주평균 km, 직전 6주 최장 러닝 km). 데이터가 없으면 (0, 0)."""
    def _sum(days: int, agg: str) -> float:
        r = conn.execute(
            f"SELECT {agg}(distance_m) FROM v_canonical_activities WHERE activity_type IN {_RUN} "
            "AND DATE(start_time) >= ? AND DATE(start_time) < ?",
            ((as_of - timedelta(days=days)).isoformat(), as_of.isoformat())).fetchone()
        return float(r[0] or 0.0) / 1000.0
    return round(_sum(28, "SUM") / 4, 1), round(_sum(42, "MAX"), 1)


def recent_long_max(conn: sqlite3.Connection, as_of: date, weeks: int = 12) -> float:
    """as_of 직전 weeks 주 최장 러닝 km(롱런 basis·게이트 공용). 없으면 0."""
    r = conn.execute(
        f"SELECT MAX(distance_m) FROM v_canonical_activities WHERE activity_type IN {_RUN} "
        "AND DATE(start_time) >= ? AND DATE(start_time) < ?",
        ((as_of - timedelta(weeks=weeks)).isoformat(), as_of.isoformat())).fetchone()
    return round(float(r[0] or 0.0) / 1000.0, 1)


def recent_avg_km(conn: sqlite3.Connection, as_of: date, weeks: int = 16) -> float:
    """as_of 직전 weeks 주 주평균 러닝 km. 없으면 0."""
    r = conn.execute(
        f"SELECT SUM(distance_m) FROM v_canonical_activities WHERE activity_type IN {_RUN} "
        "AND DATE(start_time) >= ? AND DATE(start_time) < ?",
        ((as_of - timedelta(weeks=weeks)).isoformat(), as_of.isoformat())).fetchone()
    return round(float(r[0] or 0.0) / 1000.0 / weeks, 1)


def cold_start_km(dlabel: str, prev4: float, avg16: float, user_km: float | None = None) -> tuple[float, str]:
    """§5.2 콜드 시작 부하와 출처. 사용자 입력 → 16주 평균×0.6 → 거리별 기본. 12km 이상, 1주차 ≤ max(1.10×prev4, 12)."""
    if user_km and user_km > 0:
        km, src = user_km, "user"
    elif avg16 > 0:
        km, src = avg16 * DETRAIN_FACTOR, "avg16"
    else:
        km, src = W_COLD.get(dlabel, COLD_WEEK_KM), "default"
    km = max(km, prev4, COLD_WEEK_KM)
    if prev4 > 0:       # G6 1주차 예외와 같은 기준(기록이 있으면 그 이상 뛰지 않는다)
        km = min(km, max(1.10 * prev4, COLD_WEEK_KM))
    return math.floor(km * 10 + 1e-6) / 10, src      # 내림(1주차 상한을 넘지 않게)


def start_load(conn: sqlite3.Connection, dlabel: str, as_of: date, rules_version: int,
               user_km: float | None = None, user_long: float | None = None) -> tuple[float, float, str]:
    """(시작 주간 km, 시작 최장 km, 출처). 출처 history 는 직전 4주 그대로, v1 은 콜드 처리 없음.

    user_km·user_long: 목표 생성 시 입력값(콜드일 때만 쓴다. 최장은 출처가 user 일 때 시작 롱런 후보)."""
    km4, long6 = recent_load(conn, as_of)
    if rules_version >= 2:
        long6 = P.start_long_km(long6, recent_long_max(conn, as_of, 12))
    if rules_version < 2 or km4 >= COLD_WEEK_KM:
        return km4, long6, "history"
    km, src = cold_start_km(dlabel, km4, recent_avg_km(conn, as_of, 16), user_km)
    reported = user_long if src == "user" and user_long else 0.0
    return km, max(long6, reported, LR.abs_min_km(dlabel)), src     # 롱런은 절대 최소에서 시작(§5.2-4)


COLD_SOURCE_TEXT = {"user": "입력한 최근 주간 거리", "avg16": "직전 16주 평균의 60%", "default": "거리별 기본값"}


def _rules_version(conn: sqlite3.Connection, goal: dict) -> int:
    return get_rules_version(conn, goal["id"]) if goal.get("id") is not None else 1


def _goal_start_load(conn: sqlite3.Connection, goal: dict, dlabel: str, as_of: date, rv: int):
    """목표에 저장된 사용자 입력(v28)을 넣어 start_load 를 부른다."""
    user_km, user_long = get_reported_load(conn, goal["id"]) if goal.get("id") is not None else (None, None)
    return start_load(conn, dlabel, as_of, rv, user_km, user_long)


def _long_pace_fn(goal: dict, dlabel: str, vdot: float | None, conn: sqlite3.Connection | None = None):
    """대회까지 남은 주 → 그 주 처방 MP 기반 롱런 페이스(planner_v2.apply_for_goal 과 같은 정의)."""
    secs = goal.get("target_time_sec")
    mp_goal = goal.get("target_pace_sec_km") or (secs / 42.195 if secs and dlabel == "full" else None)
    cfg = None
    if not (vdot and vdot > 20):        # VDOT 없을 때만 프로필 역치 페이스가 쓰인다(요청 사용자 설정)
        from src.utils.config import load_config
        cfg = load_config()
    mp_now = get_paces_from_vdot(vdot, cfg, conn).get("M")

    def pace(to_race: int) -> float:
        mp = MR.prescribed_mp(mp_now, mp_goal, max(0, 16 - to_race))
        return MR.long_run_pace(mp) if mp else LR.DEFAULT_LONG_PACE
    return pace


def _long_cap_fn(dlabel: str, pace, n_days: int, long6: float, long12: float):
    """v2 주기화용 롱런 공유 상한(long_run_rules.long_cap_km, 진행 상한 포함)."""
    def cap(phase: str, to_race: int, week_km: float, sched: float, prev: float) -> float:
        return LR.long_cap_km(LR.LongCtx(dlabel, phase, to_race, week_km, n_days, pace(to_race), sched, long6, long12,
                                         prev_long_km=prev))
    return cap


def schedule_for_goal(conn: sqlite3.Connection, goal: dict, dlabel: str, vdot: float | None,
                      today: date | None = None) -> list[WeekTarget]:
    """goal(race_date·plan_weeks 필요)의 주별 목표. 계획 정보가 부족하면 빈 리스트(호출부가 기존 규칙으로 폴백)."""
    start = plan_start_monday(goal.get("race_date"), goal.get("plan_weeks"))
    if start is None:
        return []
    today = today or date.today()
    rv = _rules_version(conn, goal)
    start_km, start_long, src = _goal_start_load(conn, goal, dlabel, min(start, today), rv)
    if start_km <= 0:       # v1 기록 없음(v2 는 콜드 출처로 항상 > 0)
        return []
    peak = recommend_weekly_km(vdot, dlabel, "peak", 0, goal["plan_weeks"]) if vdot else start_km * 1.3
    if rv >= 2 and src != "history":        # 콜드: 피크 목표를 거리별 최소 준비 볼륨 이상으로(램프 10%는 그대로)
        peak = max(peak, cold_peak_km(dlabel))
    cap, long_cap = None, None
    if rv >= 2:
        n_days = _run_days(conn)
        pace = _long_pace_fn(goal, dlabel, vdot, conn)
        cap = feasible_week_km(n_days, pace(2), dlabel)      # D-LR-8(B): 피크 롱런 공유 상한과 결합
        long_cap = _long_cap_fn(dlabel, pace, n_days, start_long, recent_long_max(conn, min(start, today), 12))
    return build_schedule(int(goal["plan_weeks"]), start_km, start_long, max(peak, start_km),
                          LONG_RUN_BASE.get(dlabel, 14.0), _LONG_CAP.get(dlabel, 0.40),
                          get_taper_weeks(DISTANCE_LABEL_KM.get(dlabel, goal["distance_km"])),
                          rv, cap, long_cap, _comeback_ceiling(conn, rv, min(start, today)))


def _comeback_ceiling(conn: sqlite3.Connection, rv: int, as_of: date) -> float:
    """v2 복귀 구간이면 0.15 램프 상한(직전 16주 평균 km), 아니면 0."""
    if rv < 2:
        return 0.0
    return P.comeback_ceiling(recent_load(conn, as_of)[0], recent_avg_km(conn, as_of, 16))


def _run_days(conn: sqlite3.Connection) -> int:
    return 7 - bin(load_prefs(conn).get("rest_weekdays_mask", 0) & 0x7F).count("1")


def week_cap_km(conn: sqlite3.Connection, goal: dict, dlabel: str, vdot: float | None) -> float | None:
    """v2 주간 상한(러닝 일수로 소화 가능한 km, schedule_for_goal 과 같은 값). v1 은 None."""
    if goal.get("id") is None or _rules_version(conn, goal) < 2:
        return None
    return feasible_week_km(_run_days(conn), _long_pace_fn(goal, dlabel, vdot, conn)(2), dlabel)


def plan_start_source(conn: sqlite3.Connection, goal: dict, dlabel: str, today: date | None = None) -> str:
    """schedule_for_goal 이 쓴 시작 부하 출처(history | user | avg16 | default)."""
    start = plan_start_monday(goal.get("race_date"), goal.get("plan_weeks"))
    if start is None:
        return "history"
    return _goal_start_load(conn, goal, dlabel, min(start, today or date.today()), _rules_version(conn, goal))[2]


def week_target(conn: sqlite3.Connection, goal: dict, week_start: date, dlabel: str, vdot: float | None,
                as_of: date | None = None) -> WeekTarget | None:
    """week_start 가 계획 범위 안이면 그 주 목표, 밖이면 None. as_of 는 시작 부하를 읽는 기준일(백테스트용)."""
    start = plan_start_monday(goal.get("race_date"), goal.get("plan_weeks"))
    if start is None:
        return None
    idx = (week_start - start).days // 7
    sched = schedule_for_goal(conn, goal, dlabel, vdot, as_of)
    return sched[idx] if 0 <= idx < len(sched) else None

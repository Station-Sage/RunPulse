"""Coach 규칙 답변 — 목표·계획 계열 핸들러 (goal_feasibility · race_build · week_plan · taper_when).

숫자 표기는 `format_ko` 한 곳을 쓴다. 데이터가 없으면 에러 대신 정직한 안내문을 돌려준다.
"""
from __future__ import annotations

import logging
import sqlite3
from datetime import date, timedelta

from src.utils.format_ko import fmt_distance, fmt_duration, fmt_gap, fmt_pace, fmt_signed, workout_ko

from .coach_rule_types import RuleAnswer

log = logging.getLogger(__name__)

PHASE_KO = {"base": "기초", "build": "빌드", "peak": "피크", "recovery_week": "회복주", "taper": "테이퍼"}
TAPER_WEEKS = 3
_TAPER_CUTS = ("25%", "40%", "55%")     # periodization.TAPER_FACTORS[3] = 75/60/45% 의 감량률
_INTENSITY_OF = {"recovery": "저강도", "easy": "저강도", "long": "저강도", "tempo": "중강도",
                 "interval": "고강도", "race": "고강도"}
_NO_GOAL = "등록된 목표 레이스가 없어요. 목표를 등록하면 예측과 준비 상황을 알려드릴게요."


def _hub(conn: sqlite3.Connection, today: date) -> dict | None:
    from src.services.race_hub_service import get_race_hub
    try:
        return get_race_hub(conn, today.isoformat())
    except Exception:
        log.warning("coach rule: race hub 조회 실패", exc_info=True)
        return None


def _trend_line(history: list[dict], today: date) -> str | None:
    """최근 4주 예측 추이 — 첫 값과 마지막 값의 차이."""
    cut = (today - timedelta(days=28)).isoformat()
    pts = [h["value"] for h in history or [] if h.get("date", "") >= cut and isinstance(h.get("value"), (int, float))]
    if len(pts) < 2:
        return None
    delta = pts[-1] - pts[0]
    if abs(delta) < 10:
        return "최근 4주 예측은 큰 변화 없이 비슷해요."
    return f"최근 4주 동안 예측이 {fmt_gap(delta)} {'빨라졌어요' if delta < 0 else '느려졌어요'}."


def goal_feasibility(conn: sqlite3.Connection, today: date) -> RuleAnswer:
    hub = _hub(conn, today)
    goal = (hub or {}).get("goal")
    if not goal:
        return RuleAnswer(_NO_GOAL, followups=["today_advice", "explain_ctl"])
    pred = hub.get("prediction")
    target = goal.get("target_time_sec")
    if not pred or not isinstance(pred.get("value_sec"), (int, float)):
        return RuleAnswer(f"{goal['name']} 예측 기록이 아직 없어요 — 데이터 수집 중입니다.",
                          followups=["race_build", "today_advice"])
    value = pred["value_sec"]
    lines = [f"{goal['name']} 목표는 {fmt_duration(target)}, 지금 예측은 {fmt_duration(value)}예요."]
    dist = goal.get("distance_km")
    if isinstance(target, (int, float)) and target > 0:
        gap = value - target
        if abs(gap) < 1:
            lines.append("예측이 목표와 같아요.")
        else:
            per_km = f" (km당 {fmt_gap(gap / dist)})" if dist else ""
            lines.append(f"목표보다 {fmt_gap(gap)} {'느려요' if gap > 0 else '빨라요'}{per_km}.")
        if dist:
            lines.append(f"목표 페이스는 {fmt_pace(target / dist)}예요.")
    trend = _trend_line(pred.get("history") or [], today)
    if trend:
        lines.append(trend)
    form = (hub.get("projection") or {})
    scen = {s.get("key"): s for s in form.get("scenarios") or []}
    taper = scen.get("taper")
    if taper and isinstance(taper.get("tsb"), (int, float)):
        lines.append(f"계획대로 테이퍼하면 대회 날 폼은 {fmt_signed(taper['tsb'])} 정도로 예상돼요.")
    return RuleAnswer(" ".join(lines), followups=["race_build", "taper_when", "explain_tsb"])


def _phase_for(conn: sqlite3.Connection, goal: dict, weeks_left: int | None, today: date):
    """(phase, WeekTarget|None) — planner 와 같은 기준(역산 주기화 우선, 없으면 규칙)."""
    from src.training.planner_config import get_vdot_adj, get_week_index
    from src.training.planner_rules import resolve_distance_label, training_phase
    from src.training.planner_schedule import week_target
    monday = today - timedelta(days=today.weekday())
    dlabel = resolve_distance_label(goal.get("distance_km") or 10.0, goal.get("distance_label"))
    target = week_target(conn, goal, monday, dlabel, get_vdot_adj(conn))
    if target:
        return target.phase, target
    return training_phase(weeks_left, get_week_index(monday, conn)), None


def _goal_row(conn: sqlite3.Connection, goal_id: int) -> dict:
    conn.row_factory = sqlite3.Row
    r = conn.execute("SELECT * FROM goals WHERE id=?", (goal_id,)).fetchone()
    return dict(r) if r else {}


def race_build(conn: sqlite3.Connection, today: date) -> RuleAnswer:
    hub = _hub(conn, today)
    goal = (hub or {}).get("goal")
    if not goal:
        return RuleAnswer(_NO_GOAL, followups=["today_advice", "explain_ctl"])
    weeks_left = goal.get("weeks_left")
    full = {**_goal_row(conn, goal["id"]), **goal}
    phase, target = _phase_for(conn, full, weeks_left, today)
    lines = [f"{goal['name']}까지 {goal.get('days_left')}일(약 {weeks_left}주) 남았고, 지금은 {PHASE_KO.get(phase, phase)} 단계예요."]
    plan = None
    try:
        from src.services.plan_service import get_active_plan
        plan = get_active_plan(conn, goal_id=goal["id"])
    except Exception:
        log.warning("coach rule: 계획 조회 실패", exc_info=True)
    if target:
        lines.append(f"이번 주 목표는 {fmt_distance(target.weekly_km)}예요.")
    peak_km = _peak_week_km(conn, full, today)
    if peak_km:
        lines.append(f"피크 주에는 주간 {fmt_distance(peak_km)}까지 올라가요.")
    taper = next((s for s in (hub.get("projection") or {}).get("scenarios") or [] if s.get("key") == "taper"), None)
    if taper and isinstance(taper.get("ctl"), (int, float)) and isinstance(taper.get("tsb"), (int, float)):
        lines.append(f"대회 날 예상 체력(CTL)은 {taper['ctl']:.0f}, 폼은 {fmt_signed(taper['tsb'])}예요.")
    link = ({"label": "계획 보기 ›", "href": "/v2/coach/plan"} if plan
            else {"label": "계획 만들기 ›", "href": "/v2/coach/plan"})
    return RuleAnswer(" ".join(lines), followups=["week_plan" if plan else "goal_feasibility", "taper_when"], links=[link])


def _peak_week_km(conn: sqlite3.Connection, goal: dict, today: date) -> float | None:
    from src.training.planner_config import get_vdot_adj
    from src.training.planner_rules import resolve_distance_label
    from src.training.planner_schedule import schedule_for_goal
    try:
        dlabel = resolve_distance_label(goal.get("distance_km") or 10.0, goal.get("distance_label"))
        sched = schedule_for_goal(conn, goal, dlabel, get_vdot_adj(conn), today)
    except Exception:
        log.warning("coach rule: 주기화 조회 실패", exc_info=True)
        return None
    return max((w.weekly_km for w in sched if w.phase != "taper"), default=None)


def week_plan(conn: sqlite3.Connection, today: date) -> RuleAnswer:
    from src.training.planned_query import get_planned_workouts
    monday = today - timedelta(days=today.weekday())
    try:
        week = get_planned_workouts(conn, monday)
    except Exception:
        log.warning("coach rule: 주간 계획 조회 실패", exc_info=True)
        week = []
    left = [w for w in week if w.get("date", "") >= today.isoformat() and not w.get("completed")
            and not w.get("superseded") and w.get("workout_type") != "rest"]
    if not left:
        return RuleAnswer("이번 주 남은 계획 훈련이 없어요.", followups=["today_advice", "race_build"])
    parts = []
    for w in left:
        d = date.fromisoformat(w["date"])
        km = fmt_distance(w["distance_km"]) if w.get("distance_km") else ""
        parts.append(f"{d.month}/{d.day} {workout_ko(w['workout_type'])} {km}".strip()
                     + f"({_INTENSITY_OF.get(w['workout_type'], '중강도')})")
    return RuleAnswer(f"이번 주 남은 훈련은 {len(left)}개예요: " + ", ".join(parts) + ".",
                      links=[{"label": "계획 보기 ›", "href": "/v2/coach/plan"}],
                      followups=["today_advice", "race_build"])


def taper_when(conn: sqlite3.Connection, today: date) -> RuleAnswer:
    hub = _hub(conn, today)
    goal = (hub or {}).get("goal")
    if not goal:
        return RuleAnswer(_NO_GOAL, followups=["today_advice", "explain_ctl"])
    race = date.fromisoformat(goal["race_date"])
    start = race - timedelta(days=7 * TAPER_WEEKS)
    cuts = ", ".join(f"{i + 1}주차 {c}" for i, c in enumerate(_TAPER_CUTS))
    if start <= today:
        head = f"{goal['name']} 테이퍼는 이미 시작되는 구간이에요 (대회 {TAPER_WEEKS}주 전부터)."
    else:
        head = f"{goal['name']} 테이퍼는 {start.month}월 {start.day}일(대회 {TAPER_WEEKS}주 전)부터 시작해요."
    return RuleAnswer(f"{head} 주간 거리를 피크 주 대비 {cuts}씩 줄여요.",
                      links=[{"label": "레이스 준비 보기 ›", "href": "/v2/today/race"}],
                      followups=["race_build", "explain_tsb"])

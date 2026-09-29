"""Today 히어로·주간 스트립 데이터 — briefing.state 판정, 세션·조정·결손 caveat, week_compliance.

design 10-today §2.4(상태 표)·§7.3. 판정(`readiness_decision`)은 fatigue 모듈이, 계획 조정은 adjuster가
하고 여기서는 오늘 상태만 조합한다(새 판정 로직 없음).
"""
from __future__ import annotations

import sqlite3
from datetime import date as _date
from datetime import timedelta

from src.training import week_compliance as wc
from src.training.adjuster import adjust_todays_plan

WORKOUT_LABELS = {
    "easy": "이지런", "tempo": "템포", "interval": "인터벌", "long": "롱런",
    "recovery": "회복런", "race": "레이스", "rest": "휴식",
}
_KEY_TYPES = wc.QUALITY_TYPES | {"long"}


def _label(workout_type: str | None) -> str:
    return WORKOUT_LABELS.get(workout_type or "", workout_type or "")


def race_days_left(conn: sqlite3.Connection, day: str) -> int | None:
    """활성 목표의 대회일까지 남은 일수(목표 없음/지난 대회는 None)."""
    from src.training.goals import get_active_goal
    goal = get_active_goal(conn)
    if not goal or not goal.get("race_date"):
        return None
    left = (_date.fromisoformat(goal["race_date"]) - _date.fromisoformat(day)).days
    return left if left >= 0 else None


def _has_active_goal(conn: sqlite3.Connection) -> bool:
    from src.training.goals import get_active_goal
    return get_active_goal(conn) is not None


def _session(workout: dict, adjusted_type: str | None = None) -> dict:
    wtype = adjusted_type or workout["workout_type"]
    km = workout.get("distance_km")
    return {
        "id": workout.get("id"),
        "date": workout.get("date"),
        "workout_type": wtype,
        "title": _label(wtype),
        "distance_m": round(km * 1000) if km else None,
        "pace_min": workout.get("target_pace_min"),
        "pace_max": workout.get("target_pace_max"),
        "zone": workout.get("target_hr_zone"),
    }


def _week_bounds(day: str) -> tuple[_date, _date]:
    d = _date.fromisoformat(day)
    start = d - timedelta(days=d.weekday())
    return start, start + timedelta(days=6)


def _effective_start(conn: sqlite3.Connection, week_start: _date) -> _date | None:
    """이행 집계 시작일 — plan_service와 같은 규칙(계획 생기기 전 날짜는 집계 제외)."""
    from src.services.plan_service import _effective_start as eff
    from src.training.goals import get_active_goal
    goal = get_active_goal(conn)
    return eff(goal) if goal else week_start


def build_week(conn: sqlite3.Connection, day: str) -> dict:
    """이번 주(월~일) 계획 대비 진행: {done_km, plan_km, key_done, key_total, days[]}."""
    start, end = _week_bounds(day)
    today = _date.fromisoformat(day)
    res = wc.compute(conn, start, end, _effective_start(conn, start), today)
    runs = wc._run_activities(conn, start.isoformat(), end.isoformat())
    days, plan_km, key_done, key_total = [], 0.0, 0, 0
    for e in res["days"]:
        eff = e.get("effective") or {}
        wtype = eff.get("workout_type")
        if e["state"] not in ("rest", "pre_plan") and e.get("planned_km"):
            plan_km += e["planned_km"]
        if wtype in _KEY_TYPES and e["state"] != "pre_plan":
            key_total += 1
            key_done += e["state"] == "done"
        days.append({
            "date": e["date"], "state": e["state"], "workout_type": wtype,
            "title": _label(wtype) if wtype else None, "planned_km": e.get("planned_km"),
            "session_id": eff.get("id"), "activity_id": eff.get("matched_activity_id"),
            "substituted": bool(e.get("substituted")), "today": bool(e.get("today")),
        })
    done_km = sum(a["distance_km"] for acts in runs.values() for a in acts)
    return {"done_km": round(done_km, 1), "plan_km": round(plan_km, 1),
            "key_done": key_done, "key_total": key_total, "days": days}


def _today_run(conn: sqlite3.Connection, day: str) -> dict | None:
    acts = wc._run_activities(conn, day, day).get(day) or []
    if not acts:
        return None
    return {"activity_id": acts[0]["id"], "distance_m": round(sum(a["distance_km"] for a in acts) * 1000)}


def _caveats(conn: sqlite3.Connection, config: dict | None) -> list[dict]:
    if config is None:
        return []
    from src.services.sync_state_service import get_sync_state
    return get_sync_state(conn, config)["caveats"]


def build_briefing_state(conn: sqlite3.Connection, day: str, week: dict,
                         config: dict | None = None) -> dict:
    """{state, target_date, verdict, today_result, session, adjustment, caveats}."""
    out: dict = {"state": "no_plan", "target_date": day, "verdict": "as_planned",
                 "today_result": None, "session": None, "adjustment": None,
                 "caveats": _caveats(conn, config)}
    left = race_days_left(conn, day)
    today_day = next((d for d in week["days"] if d["date"] == day), None)
    run = _today_run(conn, day)
    planned = today_day if today_day and today_day["state"] not in ("rest", "pre_plan") else None

    has_plan = _has_active_goal(conn) and any(d["workout_type"] for d in week["days"])

    if left == 0:
        out["state"] = "race_day"
    elif left is not None and left <= 7:
        out["state"] = "race_week"
    elif run:
        out["state"] = "done" if planned else "extra"
    elif planned:
        out["state"] = "pre"
    elif has_plan:
        out["state"] = "rest"
    if run:
        ratio = None
        if planned and planned.get("planned_km"):
            ratio = round(run["distance_m"] / 1000 / planned["planned_km"] * 100)
        out["today_result"] = {**run, "outcome_label": None, "plan_ratio_pct": ratio}

    adj = adjust_todays_plan(conn, date=day)
    if adj and out["state"] in ("pre", "race_week", "race_day"):
        out["session"] = _session(adj, adj["adjusted_type"])
        if adj["adjusted"]:
            out["verdict"] = "down"
            out["adjustment"] = {"reason": adj["adjustment_reason"],
                                 "from": _label(adj["original_type"]),
                                 "to": _label(adj["adjusted_type"])}
        elif adj["volume_boost"]:
            out["verdict"] = "up"
    if out["session"] is None:
        nxt = next((d for d in week["days"] if d["date"] > day and d["state"] == "upcoming"), None)
        if nxt and out["state"] in ("done", "extra", "rest"):
            out["session"] = {"id": nxt["session_id"], "date": nxt["date"], "workout_type": nxt["workout_type"],
                              "title": nxt["title"], "distance_m": round(nxt["planned_km"] * 1000) if nxt["planned_km"] else None,
                              "pace_min": None, "pace_max": None, "zone": None}
    return out


def build_today_extras(conn: sqlite3.Connection, config: dict | None = None,
                       day: str | None = None) -> dict:
    """`/today` 응답의 v2 확장 필드: as_of / briefing_state / readiness / week_compliance."""
    from datetime import datetime

    from src.services.today_readiness import build_readiness
    day = day or _date.today().isoformat()
    week = build_week(conn, day)
    return {
        "as_of": {"basis": "morning", "date": day, "computed_at": datetime.now().isoformat(timespec="seconds")},
        "briefing_state": build_briefing_state(conn, day, week, config),
        "readiness": build_readiness(conn, day),
        "week_compliance": week,
    }

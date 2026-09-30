"""Coach 규칙 답변 핸들러 레지스트리 — chip_id → 핸들러 (30-coach-chat design §7.3).

답변 가능한 칩만 노출하고(`answerable_chips`), 자유 입력은 AI 없이는 정직하게 못 답한다고 알린다.
오늘 판정은 `readiness_decision` 헤드라인을 그대로 첫 문장으로 써서 Today 화면과 어긋나지 않게 한다.
"""
from __future__ import annotations

import logging
import sqlite3
from datetime import date, timedelta
from typing import Callable

from src.utils.format_ko import fmt_distance, fmt_signed, workout_ko

from .coach_rule_grade import (
    NO_RECOVERY_DATA, RecoveryGrade, checkin_drop, intensity_label, intensity_step,
)
from .coach_rule_plan_handlers import goal_feasibility, race_build, taper_when, week_plan
from .coach_rule_types import CHIP_TEXT, RuleAnswer, chip_view

log = logging.getLogger(__name__)

FREE_TEXT_HEAD = "지금은 AI가 연결되지 않아 이 질문에 답할 수 없어요."
_EXPLAIN_SLUGS = ("tsb", "ctl", "atl", "utrs", "cirs", "rri")
_PLAN_CHIPS = ("goal_feasibility", "race_build", "taper_when")


def _checkin(conn: sqlite3.Connection, today: date) -> dict | None:
    from src.services.today_service import get_todays_checkin
    try:
        return get_todays_checkin(conn, today.isoformat())
    except Exception:
        log.warning("coach rule: 체크인 조회 실패", exc_info=True)
        return None


def _grade(conn: sqlite3.Connection, today: date) -> RecoveryGrade | None:
    from src.analysis.recovery import get_recovery_status
    try:
        return RecoveryGrade.parse(get_recovery_status(conn, today.isoformat()).get("grade"))
    except Exception:
        log.warning("coach rule: 회복 등급 조회 실패", exc_info=True)
        return None


def _session_line(conn: sqlite3.Connection, today: date) -> str | None:
    from src.training.adjuster import adjust_todays_plan
    try:
        w = adjust_todays_plan(conn, None, today.isoformat())
    except Exception:
        log.warning("coach rule: 오늘 계획 조회 실패", exc_info=True)
        return None
    if not w:
        return None
    km = f" {fmt_distance(w['distance_km'])}" if w.get("distance_km") else ""
    if w.get("adjusted"):
        return (f"계획은 {workout_ko(w['original_type'])}{km}였지만 "
                f"{workout_ko(w['adjusted_type'])}로 낮추는 게 좋아요 ({w.get('adjustment_reason')}).")
    return f"오늘 계획은 {workout_ko(w['workout_type'])}{km}예요."


def today_advice(conn: sqlite3.Connection, today: date) -> RuleAnswer:
    from src.training.fatigue import readiness_decision
    decision = readiness_decision(conn, date=today.isoformat())
    checkin = _checkin(conn, today)
    grade = _grade(conn, today)
    step = intensity_step(grade, decision["fatigue_level"], checkin)
    lines = [decision["headline"]]
    if grade is None:
        lines.append(f"{NO_RECOVERY_DATA}: 오늘은 {intensity_label(step)} 수준이 적당해요.")
    else:
        lines.append(f"회복 상태로 보면 오늘은 {intensity_label(step)} 수준이 적당해요.")
    if checkin_drop(checkin):
        f = checkin.get("fatigue")
        bits = ([f"피로도 {f}/10 (1 가뿐함–10 탈진)"] if isinstance(f, (int, float)) else []) + (
            ["통증 입력"] if checkin.get("pain") else [])
        lines.append(f"직접 입력한 {', '.join(bits)}을(를) 반영해 한 단계 낮췄어요.")
    session = _session_line(conn, today)
    if session:
        lines.append(session)
    return RuleAnswer(" ".join(lines), followups=["week_plan", "injury_check", "explain_tsb"])


def _explain(conn: sqlite3.Connection, today: date, slug: str) -> dict | None:
    from src.services.metrics_explain import get_metric_explain
    for d in (today, today - timedelta(days=1)):
        try:
            result = get_metric_explain(conn, "daily", d.isoformat(), slug)
        except Exception:
            log.warning("coach rule: 지표 설명 조회 실패 %s", slug, exc_info=True)
            return None
        if result:
            return result
    return None


def explain_metric(conn: sqlite3.Connection, today: date, slug: str) -> RuleAnswer:
    info = _explain(conn, today, slug)
    if not info:
        return RuleAnswer(f"{CHIP_TEXT[f'explain_{slug}'].rstrip('?')} — 아직 이 지표 데이터가 없어요 (데이터 수집 중).",
                          followups=["today_advice"])
    meaning = info.get("meaning") or {}
    value = info.get("value")
    shown = fmt_signed(value) if slug == "tsb" else (f"{value:.0f}" if isinstance(value, (int, float)) else "-")
    status = f" ({info['status_label']})" if info.get("status_label") else ""
    lines = [f"{info['name_ko']}({info['abbr']}): {meaning.get('what', '')}".strip(),
             f"지금 값은 {shown}{status}예요."]
    if meaning.get("so_what"):
        lines.append(meaning["so_what"])
    links = [{"label": "자세히 보기 ›", "href": f"/v2/library/metrics/{slug}"}]
    return RuleAnswer(" ".join(lines), links=links, followups=["today_advice", "injury_check"])


def _band(conn: sqlite3.Connection, today: date, name: str) -> tuple[float | None, dict | None]:
    from src.metrics.bands import grade
    from src.utils.db_helpers import get_primary_metric
    for d in (today, today - timedelta(days=1)):
        try:
            row = get_primary_metric(conn, "daily", d.isoformat(), name)
        except Exception:
            log.warning("coach rule: 지표 조회 실패 %s", name, exc_info=True)
            return None, None
        if row and isinstance(row.get("numeric_value"), (int, float)):
            return row["numeric_value"], grade(name, row["numeric_value"])
    return None, None


def injury_check(conn: sqlite3.Connection, today: date) -> RuleAnswer:
    cirs, cirs_band = _band(conn, today, "cirs")
    acwr, acwr_band = _band(conn, today, "acwr")
    checkin = _checkin(conn, today)
    lines: list[str] = []
    if cirs is not None:
        lines.append(f"부상 위험도(CIRS)는 {cirs:.0f}({cirs_band['label'] if cirs_band else '-'})예요.")
    if acwr is not None:
        lines.append(f"급성/만성 부하 비(ACWR)는 {acwr:.2f}({acwr_band['label'] if acwr_band else '-'})예요.")
    top = _top_cirs_term(conn, today) if cirs is not None else None
    if top:
        lines.append(f"가장 크게 기여하는 항목은 {top}이에요.")
    if checkin and checkin.get("pain"):
        lines.append("오늘 통증을 입력하셨어요 — 통증이 이어지면 훈련을 쉬고 전문가와 상의하세요.")
    if not lines:
        return RuleAnswer("부상 위험 지표가 아직 없어요 — 데이터 수집 중입니다.", followups=["today_advice"])
    high = (cirs_band or {}).get("status") in ("poor", "caution") or (acwr_band or {}).get("status") in ("poor", "caution")
    lines.append("무리하지 말고 강도를 낮춰 주세요." if high else "지금은 큰 위험 신호가 없어요.")
    return RuleAnswer(" ".join(lines), followups=["explain_cirs", "today_advice"])


def _top_cirs_term(conn: sqlite3.Connection, today: date) -> str | None:
    info = _explain(conn, today, "cirs")
    terms = ((info or {}).get("formula") or {}).get("terms") or []
    return terms[0].get("label") if terms else None


HANDLERS: dict[str, Callable[[sqlite3.Connection, date], RuleAnswer]] = {
    "today_advice": today_advice,
    "goal_feasibility": goal_feasibility,
    "race_build": race_build,
    "week_plan": week_plan,
    "taper_when": taper_when,
    "injury_check": injury_check,
    **{f"explain_{s}": (lambda c, t, _s=s: explain_metric(c, t, _s)) for s in _EXPLAIN_SLUGS},
}


def answer_chip(conn: sqlite3.Connection, chip_id: str, today: date | None = None) -> RuleAnswer | None:
    handler = HANDLERS.get(chip_id)
    if handler is None:
        return None
    return handler(conn, today or date.today())


def _has_goal(conn: sqlite3.Connection, today: date) -> bool:
    return conn.execute("SELECT 1 FROM goals WHERE status='active' AND race_date>=? LIMIT 1",
                        (today.isoformat(),)).fetchone() is not None


def _has_plan(conn: sqlite3.Connection, today: date) -> bool:
    monday = today - timedelta(days=today.weekday())
    return conn.execute("SELECT 1 FROM planned_workouts WHERE date>=? AND date<=? AND completed=0 "
                        "AND workout_type!='rest' LIMIT 1",
                        (today.isoformat(), (monday + timedelta(days=6)).isoformat())).fetchone() is not None


def answerable_chips(conn: sqlite3.Connection, today: date | None = None) -> list[str]:
    """지금 실제로 답할 수 있는 chip_id (데이터가 없는 칩은 숨긴다)."""
    today = today or date.today()
    out = ["today_advice"]
    try:
        if _has_goal(conn, today):
            out += list(_PLAN_CHIPS)
        if _has_plan(conn, today):
            out.append("week_plan")
    except sqlite3.Error:
        log.warning("coach rule: 칩 가용성 조회 실패", exc_info=True)
    out.append("injury_check")
    out.append("explain_tsb")
    out += [f"explain_{s}" for s in _EXPLAIN_SLUGS if s != "tsb" and _explain(conn, today, s)]
    return out


def suggestion_chips(conn: sqlite3.Connection, today: date | None = None, limit: int = 6) -> list[dict]:
    return [chip_view(c) for c in answerable_chips(conn, today)[:limit]]


def free_text_answer(conn: sqlite3.Connection, today: date | None = None) -> RuleAnswer:
    """AI 없이 자유 질문은 답할 수 없다 — 상태 한 줄 + 답할 수 있는 칩 3개를 안내한다."""
    today = today or date.today()
    from src.training.fatigue import readiness_decision
    try:
        state = readiness_decision(conn, date=today.isoformat())["headline"]
    except Exception:
        log.warning("coach rule: 상태 요약 실패", exc_info=True)
        state = None
    text = FREE_TEXT_HEAD + (f" 참고로 {state}" if state else "")
    return RuleAnswer(text, followups=answerable_chips(conn, today)[:3])

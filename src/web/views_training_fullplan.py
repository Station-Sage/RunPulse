"""훈련 전체 일정 뷰 — GET /training/fullplan.

전체 기간 planned_workouts를 주별 Collapsible 카드로 표시.
"""
from __future__ import annotations

import html as _html
import sqlite3
from datetime import date, timedelta

from flask import Blueprint, request

from src.web.helpers import db_path, fmt_pace, html_page, no_data_card
from src.web.views_training_loaders import load_full_plan_weeks, load_goal

fullplan_bp = Blueprint("fullplan", __name__)

_DAY_KO = ["월", "화", "수", "목", "금", "토", "일"]

_TYPE_ICON: dict[str, str] = {
    "easy":     "🟢",
    "tempo":    "🟠",
    "interval": "🔴",
    "long":     "🟣",
    "rest":     "⚪",
    "recovery": "🔵",
    "race":     "🏁",
}

_TYPE_KO: dict[str, str] = {
    "easy": "이지런", "tempo": "템포런", "interval": "인터벌",
    "long": "롱런", "rest": "휴식", "recovery": "회복조깅", "race": "레이스",
}


def _phase_from_weeks_left(weeks_left: int | None) -> tuple[str, str]:
    """(phase_ko, color) 반환."""
    if weeks_left is None:
        return "기본", "#00d4ff"
    if weeks_left > 12:
        return "Base", "#00c853"
    if weeks_left > 8:
        return "Build", "#ff9100"
    if weeks_left > 3:
        return "Peak", "#ff1744"
    return "Taper", "#7c4dff"


def _weeks_left_from_goal(goal: dict | None, week_start: date) -> int | None:
    if not goal or not goal.get("race_date"):
        return None
    try:
        rd = date.fromisoformat(goal["race_date"])
        return max(0, (rd - week_start).days // 7)
    except ValueError:
        return None


def _render_week_card(
    idx: int,
    week: dict,
    goal: dict | None,
    total_weeks: int,
) -> str:
    """단일 주 Collapsible 카드 렌더링."""
    ws: date = week["week_start"]
    we = ws + timedelta(days=6)
    is_current: bool = week["is_current"]
    workouts: list[dict] = week["workouts"]
    total_km: float = week["total_km"]
    total_count: int = week["total_count"]
    done_count: int = week["completed_count"]

    weeks_left = _weeks_left_from_goal(goal, ws)
    phase_ko, phase_color = _phase_from_weeks_left(weeks_left)

    completion_pct = (done_count / total_count * 100) if total_count else 0
    bar_color = "#00ff88" if completion_pct >= 80 else "#ffaa00" if completion_pct >= 50 else "#ff6b6b"
    today_tag = " 🔵 현재 주" if is_current else ""

    # 요약 헤더
    week_label = f"Week {idx + 1}"
    date_range = f"{ws.month}/{ws.day}~{we.month}/{we.day}"
    km_str = f"{total_km:.1f}km" if total_km else "—"
    comp_str = f"{done_count}/{total_count} 완료" if total_count else "휴식"

    summary = (
        f"<summary style='list-style:none;display:flex;align-items:center;"
        f"gap:12px;padding:12px 16px;cursor:pointer;flex-wrap:wrap;'>"
        # 주 번호 + 날짜
        f"<span style='font-weight:bold;min-width:60px;'>{week_label}</span>"
        f"<span style='color:rgba(255,255,255,0.6);font-size:12px;'>{date_range}</span>"
        f"<span style='color:{phase_color};font-size:11px;padding:2px 8px;"
        f"border:1px solid {phase_color}40;border-radius:10px;'>{phase_ko}</span>"
        f"<span style='color:rgba(255,255,255,0.8);font-size:13px;'>{km_str}</span>"
        # 완료율 미니바
        f"<div style='display:flex;align-items:center;gap:6px;margin-left:auto;'>"
        f"<div style='width:60px;height:4px;background:rgba(255,255,255,0.1);"
        f"border-radius:2px;overflow:hidden;'>"
        f"<div style='width:{completion_pct:.0f}%;height:100%;background:{bar_color};"
        f"border-radius:2px;'></div></div>"
        f"<span style='font-size:11px;color:rgba(255,255,255,0.5);'>{comp_str}</span>"
        f"</div>"
        f"{today_tag}"
        f"</summary>"
    )

    # 워크아웃 테이블
    rows_html = ""
    for w in workouts:
        wtype = w.get("workout_type", "easy")
        icon = _TYPE_ICON.get(wtype, "⚪")
        type_ko = _TYPE_KO.get(wtype, wtype)
        d = date.fromisoformat(w["date"])
        day_ko = _DAY_KO[d.weekday()]
        dist = w.get("distance_km")
        p_min = w.get("target_pace_min")
        p_max = w.get("target_pace_max")
        completed = w.get("completed", 0)

        dist_str = f"{dist:.1f}" if dist else "—"
        pace_str = (f"{fmt_pace(p_min)}~{fmt_pace(p_max)}" if p_min and p_max
                    else fmt_pace(p_min) if p_min else "—")
        done_icon = "✅" if completed == 1 else ("⏭" if completed == -1 else "")
        row_style = "opacity:0.5;" if completed == 1 else ""

        rows_html += (
            f"<tr style='border-bottom:1px solid rgba(255,255,255,0.05);{row_style}'>"
            f"<td style='padding:6px 8px;color:rgba(255,255,255,0.5);font-size:12px;"
            f"white-space:nowrap;'>{day_ko} {d.day}일</td>"
            f"<td style='padding:6px 8px;font-size:12px;'>{icon} {type_ko}</td>"
            f"<td style='padding:6px 8px;font-size:12px;text-align:right;'>{dist_str}km</td>"
            f"<td style='padding:6px 8px;font-size:12px;color:rgba(255,255,255,0.6);'>"
            f"{pace_str}</td>"
            f"<td style='padding:6px 8px;font-size:14px;text-align:center;'>{done_icon}</td>"
            f"</tr>"
        )

    table = (
        "<div style='overflow-x:auto;padding:0 8px 12px;'>"
        "<table style='width:100%;border-collapse:collapse;'>"
        "<thead><tr style='color:rgba(255,255,255,0.4);font-size:11px;"
        "border-bottom:1px solid rgba(255,255,255,0.1);'>"
        "<th style='padding:4px 8px;text-align:left;font-weight:400;'>날짜</th>"
        "<th style='padding:4px 8px;text-align:left;font-weight:400;'>종류</th>"
        "<th style='padding:4px 8px;text-align:right;font-weight:400;'>거리</th>"
        "<th style='padding:4px 8px;text-align:left;font-weight:400;'>페이스</th>"
        "<th style='padding:4px 8px;text-align:center;font-weight:400;'>완료</th>"
        "</tr></thead>"
        f"<tbody>{rows_html}</tbody>"
        "</table></div>"
    )

    border = "border:1px solid rgba(0,212,255,0.4);" if is_current else ""
    open_attr = " open" if is_current else ""

    return (
        f"<details{open_attr} style='background:rgba(255,255,255,0.04);"
        f"border-radius:12px;margin-bottom:8px;{border}'>"
        + summary + table
        + "</details>"
    )


def _render_fullplan_page(weeks: list[dict], goal: dict | None) -> str:
    """전체 훈련 일정 페이지 본문."""
    if not weeks:
        return no_data_card("전체 훈련 일정", "생성된 훈련 계획이 없습니다.")

    total_weeks = len(weeks)
    all_non_rest = sum(w["total_count"] for w in weeks)
    all_done = sum(w["completed_count"] for w in weeks)
    all_km = sum(w["total_km"] for w in weeks)
    overall_pct = (all_done / all_non_rest * 100) if all_non_rest else 0

    # 목표 정보
    goal_info = ""
    if goal:
        name = _html.escape(goal.get("name", ""))
        rd = goal.get("race_date", "")
        dist = goal.get("distance_km", 0)
        goal_info = (
            f"<div style='margin-bottom:16px;padding:12px 16px;"
            f"background:rgba(0,212,255,0.08);border-radius:10px;"
            f"border-left:3px solid #00d4ff;'>"
            f"<span style='font-size:14px;font-weight:bold;'>🎯 {name}</span>"
            f"<span style='margin-left:12px;color:rgba(255,255,255,0.6);font-size:13px;'>"
            f"{dist:.0f}km · {rd}</span>"
            f"</div>"
        )

    # 전체 요약 통계
    stats = (
        "<div style='display:grid;grid-template-columns:repeat(3,1fr);gap:10px;"
        "margin-bottom:20px;'>"
        f"<div style='text-align:center;padding:12px;background:rgba(255,255,255,0.05);"
        f"border-radius:10px;'><div style='font-size:20px;font-weight:bold;'>"
        f"{total_weeks}</div><div style='font-size:11px;color:var(--muted);'>총 주</div></div>"
        f"<div style='text-align:center;padding:12px;background:rgba(255,255,255,0.05);"
        f"border-radius:10px;'><div style='font-size:20px;font-weight:bold;'>"
        f"{all_km:.0f}km</div><div style='font-size:11px;color:var(--muted);'>총 거리</div></div>"
        f"<div style='text-align:center;padding:12px;background:rgba(255,255,255,0.05);"
        f"border-radius:10px;'><div style='font-size:20px;font-weight:bold;"
        f"color:#00ff88;'>{overall_pct:.0f}%</div>"
        f"<div style='font-size:11px;color:var(--muted);'>전체 달성률</div></div>"
        "</div>"
    )

    # 위상(phase) 범례
    legend = (
        "<div style='display:flex;gap:10px;flex-wrap:wrap;margin-bottom:16px;"
        "font-size:11px;color:rgba(255,255,255,0.5);'>"
        "<span style='color:#00c853;'>● Base</span>"
        "<span style='color:#ff9100;'>● Build</span>"
        "<span style='color:#ff1744;'>● Peak</span>"
        "<span style='color:#7c4dff;'>● Taper</span>"
        "</div>"
    )

    cards = "".join(
        _render_week_card(i, w, goal, total_weeks)
        for i, w in enumerate(weeks)
    )

    return (
        "<div style='display:flex;align-items:center;gap:12px;"
        "padding:16px 0;border-bottom:1px solid var(--card-border);margin-bottom:20px;'>"
        "<a href='/training' style='color:var(--cyan);text-decoration:none;"
        "font-size:14px;'>← 훈련 계획</a>"
        "<span style='font-size:18px;font-weight:bold;'>전체 훈련 일정</span>"
        "</div>"
        + goal_info + stats + legend + cards
    )


# ── 라우트 ──────────────────────────────────────────────────────────────────


@fullplan_bp.route("/training/fullplan")
def training_fullplan():
    """전체 훈련 일정 페이지."""
    dbp = db_path()
    if not dbp or not dbp.exists():
        body = no_data_card("전체 훈련 일정", "데이터 수집 중입니다.")
        return html_page("전체 훈련 일정", body, active_tab="training")

    try:
        conn = sqlite3.connect(str(dbp))
        try:
            goal = load_goal(conn)
            weeks = load_full_plan_weeks(conn, goal)
        finally:
            conn.close()
    except Exception as exc:
        import html as _h
        body = f"<div class='card'><p style='color:var(--red);'>오류: {_h.escape(str(exc))}</p></div>"
        return html_page("전체 훈련 일정", body, active_tab="training")

    body = _render_fullplan_page(weeks, goal)
    return html_page("전체 훈련 일정", body, active_tab="training")

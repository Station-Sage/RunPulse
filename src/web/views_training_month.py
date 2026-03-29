"""훈련 계획 — 월간 캘린더 렌더러 (4주 뷰).

render_month_calendar() 단일 함수를 외부에 노출.
JS는 views_training_cal_js.CALENDAR_JS 공유 (H-1~H-3 포함).
"""
from __future__ import annotations

from datetime import date, timedelta

from src.web.helpers import fmt_pace
from src.web.views_training_cal_js import CALENDAR_JS
from src.web.views_training_shared import _TYPE_STYLE

_DAY_KO = ["월", "화", "수", "목", "금", "토", "일"]

_TYPE_ICON: dict[str, str] = {k: v[2] for k, v in _TYPE_STYLE.items()}

_TYPE_BG: dict[str, str] = {
    "easy":     "rgba(0,255,136,0.12)",
    "tempo":    "rgba(255,170,0,0.12)",
    "interval": "rgba(255,68,68,0.12)",
    "long":     "rgba(128,0,255,0.12)",
    "rest":     "rgba(84,110,122,0.08)",
    "recovery": "rgba(0,188,212,0.12)",
    "race":     "rgba(255,214,0,0.12)",
}


def _view_tabs(week_offset: int, current_view: str) -> str:
    """주간 | 월간 | 전체 탭 버튼 (주간/월간 전환은 rpNavTo AJAX)."""
    def _tab(label: str, href: str, active: bool, cal_url: str = "") -> str:
        bg = "rgba(0,212,255,0.2)" if active else "rgba(255,255,255,0.08)"
        color = "#00d4ff" if active else "rgba(255,255,255,0.6)"
        onclick = (
            f" onclick=\"rpNavTo('{href}','{cal_url}');return false;\""
            if cal_url and not active else ""
        )
        return (
            f"<a href='{href}'{onclick} style='background:{bg};color:{color};"
            f"padding:5px 12px;border-radius:16px;font-size:12px;"
            f"text-decoration:none;white-space:nowrap;'>{label}</a>"
        )

    week_href = f"/training?week={week_offset}"
    month_href = f"/training?view=month&week={week_offset}"
    return (
        "<div style='display:flex;gap:6px;'>"
        + _tab("주간", week_href, current_view == "week",
               f"/training/calendar-partial?week={week_offset}")
        + _tab("월간", month_href, current_view == "month",
               f"/training/calendar-partial?view=month&week={week_offset}")
        + _tab("전체", "/training/fullplan", current_view == "full")
        + "</div>"
    )


def _render_day_cell(
    d: date,
    w: dict | None,
    actual: dict | None,
    is_today: bool,
) -> str:
    """단일 날짜 셀 (월간 뷰용 — 간략 표시)."""
    border = "border:1px solid rgba(0,212,255,0.5);" if is_today else ""
    num_color = "#00d4ff" if is_today else "rgba(255,255,255,0.5)"

    workout_html = ""
    if w:
        wtype = w.get("workout_type", "easy")
        icon = _TYPE_ICON.get(wtype, "⚪")
        bg = _TYPE_BG.get(wtype, "rgba(255,255,255,0.05)")
        dist = w.get("distance_km")
        completed = w.get("completed", 0)
        dist_str = f"{dist:.0f}" if dist else ""
        dist_data = f"{dist:.1f}" if dist else ""
        opacity = "opacity:0.45;" if completed == 1 else ""
        done_dot = (
            "<span style='position:absolute;top:3px;right:4px;"
            "width:5px;height:5px;border-radius:50%;background:#00ff88;'></span>"
            if completed == 1 else ""
        )
        _, label_ko, _ = _TYPE_STYLE.get(wtype, _TYPE_STYLE["easy"])
        p_min = w.get("target_pace_min")
        p_max = w.get("target_pace_max")
        pace_min_str = fmt_pace(p_min) if p_min else ""
        pace_max_str = fmt_pace(p_max) if p_max else ""
        tip_parts = [label_ko]
        if dist:
            tip_parts.append(f"{dist:.1f}km")
        if pace_min_str and pace_max_str:
            tip_parts.append(f"{pace_min_str}~{pace_max_str}/km")
        data_tip = " · ".join(tip_parts)
        wid = w.get("id", "")
        workout_html = (
            f"<div onclick='rpOpenWorkout(this)' "
            f"data-wid='{wid}' data-wtype='{wtype}' data-dist='{dist_data}' "
            f"data-pace-min='{pace_min_str}' data-pace-max='{pace_max_str}' "
            f"data-date='{d.isoformat()}' data-completed='{completed}' "
            f"data-label='{label_ko}' data-tip='{data_tip}' "
            f"style='position:relative;background:{bg};border-radius:6px;"
            f"padding:3px 5px;margin-top:3px;font-size:10px;cursor:pointer;{opacity}'>"
            f"{done_dot}{icon}"
            + (f" <span style='color:rgba(255,255,255,0.7);'>{dist_str}k</span>" if dist_str else "")
            + "</div>"
        )

    # 실제 활동 (간략)
    actual_html = ""
    if actual and actual.get("km"):
        act_km = actual["km"]
        plan_km = w.get("distance_km") if w else None
        color = "#00ff88" if (plan_km and act_km / plan_km >= 0.9) else "#ffaa00"
        actual_html = (
            f"<div style='font-size:9px;color:{color};margin-top:2px;'>"
            f"✓{act_km:.0f}k</div>"
        )

    return (
        f"<div style='background:rgba(255,255,255,0.04);border-radius:10px;"
        f"min-height:72px;padding:6px;{border}'>"
        f"<div style='font-size:11px;color:{num_color};margin-bottom:2px;'>{d.day}</div>"
        + workout_html + actual_html
        + "</div>"
    )


def render_month_calendar(
    weeks_data: list[tuple[list[dict], date]],
    week_offset: int = 0,
    actual_activities: dict[str, dict] | None = None,
) -> str:
    """4주 그리드 캘린더 + 주 네비게이션 탭.

    Args:
        weeks_data: load_month_workouts() 반환값 [(workouts, week_start), ...]
        week_offset: 기준 주 오프셋 (← → 4주씩 이동)
        actual_activities: 날짜별 실제 활동 {"yyyy-mm-dd": {"km": ..., "pace": ...}}
    """
    actual_activities = actual_activities or {}
    today_iso = date.today().isoformat()

    if not weeks_data:
        return "<div class='card'><p class='muted'>표시할 데이터가 없습니다.</p></div>"

    first_ws = weeks_data[0][1]
    last_we = weeks_data[-1][1] + timedelta(days=6)
    month_str = f"{first_ws.year}년 {first_ws.month}월"
    range_str = f"{first_ws.month}/{first_ws.day}~{last_we.month}/{last_we.day}"

    prev_off = week_offset - 4
    next_off = week_offset + 4
    today_off = 0  # 이번 주 기준

    _a = "style='width:30px;height:30px;background:rgba(255,255,255,0.1);border-radius:50%;display:flex;align-items:center;justify-content:center;text-decoration:none;color:#fff;font-size:13px;'"
    nav = (
        "<div style='display:flex;justify-content:space-between;align-items:center;"
        "margin-bottom:14px;flex-wrap:wrap;gap:8px;'>"
        "<div style='display:flex;align-items:center;gap:10px;'>"
        f"<a href='/training?view=month&week={prev_off}' "
        f"onclick=\"rpNavTo('/training?view=month&week={prev_off}',"
        f"'/training/calendar-partial?view=month&week={prev_off}');return false;\" "
        f"{_a}>←</a>"
        f"<span style='font-size:15px;font-weight:bold;'>{month_str}</span>"
        f"<span style='font-size:11px;color:var(--muted);'>{range_str}</span>"
        f"<a href='/training?view=month&week={next_off}' "
        f"onclick=\"rpNavTo('/training?view=month&week={next_off}',"
        f"'/training/calendar-partial?view=month&week={next_off}');return false;\" "
        f"{_a}>→</a>"
        + (f"<a href='/training?view=month' "
           f"onclick=\"rpNavTo('/training?view=month',"
           f"'/training/calendar-partial?view=month&week=0');return false;\" "
           "style='font-size:11px;color:var(--cyan);"
           "text-decoration:none;padding:3px 8px;border:1px solid rgba(0,212,255,0.3);"
           "border-radius:10px;'>오늘</a>" if week_offset != today_off else "")
        + "</div>"
        + _view_tabs(week_offset, "month")
        + "</div>"
    )

    # 요일 헤더
    day_header = (
        "<div style='display:grid;grid-template-columns:repeat(7,1fr);gap:6px;"
        "margin-bottom:6px;'>"
        + "".join(
            f"<div style='text-align:center;font-size:11px;"
            f"color:rgba(255,255,255,0.4);padding:4px;'>{d}</div>"
            for d in _DAY_KO
        )
        + "</div>"
    )

    # 4주 × 7일 그리드
    rows_html = ""
    for workouts, ws in weeks_data:
        by_date = {w["date"]: w for w in workouts}
        row = "<div style='display:grid;grid-template-columns:repeat(7,1fr);gap:6px;margin-bottom:6px;'>"
        for i in range(7):
            d = ws + timedelta(days=i)
            d_iso = d.isoformat()
            w = by_date.get(d_iso)
            actual = actual_activities.get(d_iso)
            row += _render_day_cell(d, w, actual, d_iso == today_iso)
        row += "</div>"
        rows_html += row

    return (
        CALENDAR_JS
        + f"<div id='rp-calendar' class='card' data-week-offset='{week_offset}' data-view='month'>"
        + nav + day_header + rows_html
        + "</div>"
    )

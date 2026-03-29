"""훈련탭 — 주간 캘린더 렌더러 (S5).

render_week_calendar() 단일 함수를 외부에 노출.
JS는 views_training_cal_js.CALENDAR_JS 공유 (H-1~H-3 포함).
"""
from __future__ import annotations

from datetime import date, timedelta

from src.web.helpers import fmt_pace
from src.web.views_training_cal_js import CALENDAR_JS
from src.web.views_training_shared import _TYPE_STYLE, _TYPE_BG

# ── 입력 필드 공통 CSS ────────────────────────────────────────────────

_INP = (
    "background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.2);"
    "border-radius:4px;color:#fff;font-size:10px;padding:3px;width:100%;box-sizing:border-box;"
)

# ── 인라인 편집 패널 ────────────────────────────────────────────────

def _render_edit_panel(
    wid: int,
    wtype: str,
    dist: float | None,
    pace_min: int | None,
    pace_max: int | None,
) -> str:
    """인라인 AJAX 편집 패널 HTML."""
    int_display = "flex" if wtype == "interval" else "none"
    type_opts = "".join(
        f"<option value='{t}'{' selected' if t == wtype else ''}>{s[1]}</option>"
        for t, s in _TYPE_STYLE.items()
    )
    return (
        f"<div id='edit-{wid}' style='display:none;margin-top:6px;padding:8px;"
        f"background:rgba(255,255,255,0.05);border-radius:8px;"
        f"border:1px solid rgba(255,255,255,0.1);'>"
        f"<div style='display:flex;flex-direction:column;gap:4px;'>"
        f"<select id='et-{wid}' onchange='rpEditTypeChange({wid},this.value)' style='{_INP}'>"
        f"{type_opts}</select>"
        f"<input id='ed-{wid}' type='number' step='0.1' value='{dist or ''}' "
        f"placeholder='거리(km)' style='{_INP}'/>"
        f"<div style='display:flex;gap:4px;'>"
        f"<input id='epm-{wid}' type='text' value='{fmt_pace(pace_min) if pace_min else ''}' "
        f"placeholder='최소(4:30 또는 430)' style='{_INP}' title='페이스 예: 4:30 또는 430'/>"
        f"<input id='epx-{wid}' type='text' value='{fmt_pace(pace_max) if pace_max else ''}' "
        f"placeholder='최대(5:00 또는 500)' style='{_INP}' title='페이스 예: 5:00 또는 500'/>"
        f"</div>"
        f"<div id='ei-{wid}' style='display:{int_display};flex-direction:column;gap:4px;'>"
        f"<div style='display:flex;gap:4px;align-items:center;'>"
        f"<input id='er-{wid}' type='number' value='1000' min='100' max='5000' step='100' "
        f"placeholder='반복거리(m)' style='{_INP}'/>"
        f"<button onclick='rpCalcInterval({wid})' "
        f"style='background:rgba(255,68,68,0.2);color:#ff8888;"
        f"border:1px solid rgba(255,68,68,0.3);border-radius:4px;"
        f"padding:2px 6px;font-size:9px;cursor:pointer;white-space:nowrap;'>처방↺</button>"
        f"</div>"
        f"<div id='ep-{wid}' style='font-size:9px;color:rgba(255,255,255,0.6);line-height:1.4;'></div>"
        f"</div>"
        f"<div style='display:flex;gap:4px;'>"
        f"<button onclick='rpSaveEdit({wid})' "
        f"style='background:var(--cyan);color:#000;border:none;"
        f"border-radius:4px;padding:3px 10px;font-size:10px;cursor:pointer;'>저장</button>"
        f"<button onclick=\"document.getElementById('edit-{wid}').style.display='none'\" "
        f"style='background:rgba(255,255,255,0.1);color:#fff;border:none;"
        f"border-radius:4px;padding:3px 10px;font-size:10px;cursor:pointer;'>취소</button>"
        f"</div>"
        f"<div id='em-{wid}' style='font-size:9px;min-height:12px;'></div>"
        f"</div></div>"
    )


# ── 주간 캘린더 탭 ─────────────────────────────────────────────────

def _week_view_tabs(week_offset: int) -> str:
    """주간 캘린더용 3탭 (주간 활성)."""
    def _tab(label: str, href: str, active: bool, cal_url: str = "") -> str:
        bg = "rgba(0,212,255,0.2)" if active else "rgba(255,255,255,0.08)"
        color = "#00d4ff" if active else "rgba(255,255,255,0.6)"
        onclick = (
            f" onclick=\"rpNavTo('{href}','{cal_url}');return false;\""
            if cal_url else ""
        )
        return (
            f"<a href='{href}'{onclick} style='background:{bg};color:{color};"
            f"padding:5px 12px;border-radius:16px;font-size:12px;"
            f"text-decoration:none;white-space:nowrap;'>{label}</a>"
        )

    month_href = f"/training?view=month&week={week_offset}"
    return (
        "<div style='display:flex;gap:6px;'>"
        + _tab("주간", f"/training?week={week_offset}", True)
        + _tab("월간", month_href, False,
               f"/training/calendar-partial?view=month&week={week_offset}")
        + _tab("전체", "/training/fullplan", False)
        + "</div>"
    )


# ── S5: 주간 캘린더 ────────────────────────────────────────────────

def render_week_calendar(
    workouts: list[dict],
    week_start: date,
    week_offset: int = 0,
    actual_activities: dict[str, dict] | None = None,
) -> str:
    """7열 그리드 캘린더 + 주 네비게이션 + 완료 토글/삭제 버튼.

    Args:
        actual_activities: 날짜별 실제 활동 dict {"2026-03-25": {"km": 10.5, ...}}
    """
    today_iso = date.today().isoformat()
    actual_activities = actual_activities or {}

    month_str = f"{week_start.year}년 {week_start.month}월"
    week_end = week_start + timedelta(days=6)
    range_str = f"{week_start.month}/{week_start.day}~{week_end.month}/{week_end.day}"
    prev_w = week_offset - 1
    next_w = week_offset + 1

    nav = (
        "<div style='display:flex;justify-content:space-between;align-items:center;"
        "margin-bottom:16px;flex-wrap:wrap;gap:8px;'>"
        "<div style='display:flex;align-items:center;gap:12px;'>"
        f"<a href='/training?week={prev_w}' onclick='rpWeekNav({prev_w});return false;' "
        "style='width:32px;height:32px;"
        "background:rgba(255,255,255,0.1);border-radius:50%;display:flex;"
        "align-items:center;justify-content:center;text-decoration:none;color:#fff;'>←</a>"
        f"<span style='font-size:16px;font-weight:bold;'>{month_str}</span>"
        f"<span style='font-size:12px;color:var(--muted);'>{range_str}</span>"
        f"<a href='/training?week={next_w}' onclick='rpWeekNav({next_w});return false;' "
        "style='width:32px;height:32px;"
        "background:rgba(255,255,255,0.1);border-radius:50%;display:flex;"
        "align-items:center;justify-content:center;text-decoration:none;color:#fff;'>→</a>"
        + (f"<a href='/training' onclick='rpWeekNav(0);return false;' "
           "style='font-size:11px;color:var(--cyan);text-decoration:none;"
           "padding:4px 10px;border:1px solid rgba(0,212,255,0.3);border-radius:12px;'>오늘</a>"
           if week_offset != 0 else "")
        + "</div>"
        + _week_view_tabs(week_offset)
        + "</div>"
    )

    day_names = ["월", "화", "수", "목", "금", "토", "일"]
    workout_by_date: dict[str, dict] = {w["date"]: w for w in workouts}

    cols = ""
    for i in range(7):
        d = week_start + timedelta(days=i)
        d_iso = d.isoformat()
        is_today = d_iso == today_iso
        w = workout_by_date.get(d_iso)

        header_cls = "color:#00d4ff;font-weight:bold;" if is_today else "color:rgba(255,255,255,0.6);"
        day_border = "border:1px solid rgba(0,212,255,0.5);" if is_today else ""
        num_style = "color:#00d4ff;font-weight:bold;" if is_today else "color:rgba(255,255,255,0.6);"

        workout_html = ""
        if w:
            wid = w.get("id")
            wtype = w.get("workout_type", "easy")
            style_info = _TYPE_STYLE.get(wtype, _TYPE_STYLE["easy"])
            _, label_ko, icon = style_info
            bg = _TYPE_BG.get(wtype, "rgba(255,255,255,0.05)")
            completed = w.get("completed", False)
            dist = w.get("distance_km")

            comp_cls = "opacity:0.5;text-decoration:line-through;" if completed else ""
            check = " ✅" if completed else ""
            dist_str = f"{dist:.1f}km" if dist else ""
            dist_data = f"{dist:.1f}" if dist else ""

            p_min = w.get("target_pace_min")
            p_max = w.get("target_pace_max")
            pace_str = ""
            pace_min_str = fmt_pace(p_min) if p_min else ""
            pace_max_str = fmt_pace(p_max) if p_max else ""
            if p_min and p_max:
                pace_str = f"{pace_min_str}~{pace_max_str}"

            actions = ""
            if wid:
                toggle_label = "↩️" if completed else "✓"
                actions = (
                    "<div style='display:flex;gap:4px;margin-top:4px;'"
                    " onclick='event.stopPropagation()'>"
                    f"<form method='POST' action='/training/workout/{wid}/toggle' style='margin:0;'>"
                    f"<input type='hidden' name='week' value='{week_offset}'/>"
                    f"<button type='submit' title='{'완료 취소' if completed else '완료 처리'}' "
                    f"style='background:rgba(255,255,255,0.15);border:none;"
                    f"color:#fff;padding:2px 6px;border-radius:6px;font-size:10px;cursor:pointer;'>"
                    f"{toggle_label}</button></form>"
                    f"<button title='수정 패널 열기/닫기' "
                    f"onclick=\"document.getElementById('edit-{wid}').style.display="
                    f"document.getElementById('edit-{wid}').style.display==='none'?'block':'none'\" "
                    f"style='background:rgba(0,212,255,0.15);border:none;color:var(--cyan);"
                    f"padding:2px 6px;border-radius:6px;font-size:10px;cursor:pointer;'>⚙️</button>"
                    f"<form method='POST' action='/training/workout/{wid}/delete' style='margin:0;'>"
                    f"<input type='hidden' name='week' value='{week_offset}'/>"
                    f"<button type='submit' title='워크아웃 삭제' "
                    f"style='background:rgba(255,68,68,0.2);border:none;"
                    f"color:#ff4444;padding:2px 6px;border-radius:6px;font-size:10px;cursor:pointer;'"
                    f" onclick=\"return confirm('삭제?')\">✕</button></form></div>"
                    + _render_edit_panel(
                        wid, wtype, dist,
                        w.get("target_pace_min"), w.get("target_pace_max")
                    )
                )

            workout_html = (
                f"<div onclick='rpOpenWorkout(this)' "
                f"data-wid='{wid}' data-wtype='{wtype}' data-dist='{dist_data}' "
                f"data-pace-min='{pace_min_str}' data-pace-max='{pace_max_str}' "
                f"data-date='{d_iso}' data-completed='{1 if completed else 0}' "
                f"data-label='{label_ko}' "
                f"style='background:{bg};border-radius:8px;padding:8px;"
                f"font-size:11px;transition:all 0.2s;cursor:pointer;{comp_cls}'>"
                f"<div style='font-weight:600;margin-bottom:2px;'>{icon} {label_ko}{check}</div>"
                + (f"<div style='font-size:10px;color:rgba(255,255,255,0.7);'>{dist_str}</div>"
                   if dist_str else "")
                + (f"<div style='font-size:9px;color:rgba(255,255,255,0.5);'>{pace_str}</div>"
                   if pace_str else "")
                + actions
                + "</div>"
            )

        actual_html = ""
        if d_iso < today_iso or (d_iso == today_iso):
            act = actual_activities.get(d_iso)
            if act:
                act_km = act.get("km")
                act_pace = act.get("pace")
                plan_km = w.get("distance_km") if w else None

                if plan_km and act_km:
                    ratio = act_km / plan_km
                    act_color = "#00ff88" if ratio >= 0.9 else "#ffaa00" if ratio >= 0.7 else "#ff6b6b"
                else:
                    act_color = "rgba(255,255,255,0.5)"

                pace_str_act = ""
                if act_pace:
                    m, s = divmod(int(act_pace), 60)
                    pace_str_act = f"{m}:{s:02d}"

                km_str = f"{act_km:.1f}km" if act_km else ""
                actual_html = (
                    f"<div style='margin-top:4px;padding:4px 6px;background:rgba(0,255,136,0.08);"
                    f"border-radius:6px;border-left:2px solid {act_color};font-size:9px;"
                    f"color:rgba(255,255,255,0.7);'>"
                    f"<span style='color:{act_color};font-weight:600;'>실제</span> "
                    + (f"{km_str} " if km_str else "")
                    + (f"· {pace_str_act}/km" if pace_str_act else "")
                    + "</div>"
                )

        cols += (
            "<div style='display:flex;flex-direction:column;gap:6px;'>"
            f"<div style='text-align:center;padding:6px;font-size:12px;{header_cls}'>"
            f"{day_names[i]}</div>"
            f"<div style='background:rgba(255,255,255,0.05);border-radius:12px;"
            f"min-height:100px;padding:10px;{day_border}'>"
            f"<div style='font-size:13px;margin-bottom:6px;{num_style}'>{d.day}</div>"
            + workout_html
            + actual_html
            + "</div></div>"
        )

    grid = (
        "<div style='display:grid;grid-template-columns:repeat(7,1fr);gap:10px;"
        "overflow-x:auto;min-width:0;'>"
        + cols + "</div>"
    )

    legend = (
        "<div style='margin-top:10px;padding-top:8px;border-top:1px solid rgba(255,255,255,0.08);"
        "display:flex;flex-wrap:wrap;gap:8px 16px;font-size:10px;color:var(--muted);'>"
        "<span title='완료 처리 / 완료 취소'>✓ / ↩️ 완료토글</span>"
        "<span title='수정 패널 열기'>⚙️ 수정</span>"
        "<span title='워크아웃 삭제'>✕ 삭제</span>"
        "<span style='margin-left:auto;'>페이스: 4:30 또는 430 형식</span>"
        "</div>"
    )
    return (
        CALENDAR_JS
        + f"<div id='rp-calendar' class='card' data-week-offset='{week_offset}' data-view='week'>"
        + nav + grid + legend
        + "</div>"
    )

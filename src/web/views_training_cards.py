"""훈련 계획 뷰 — 카드 렌더러 (S1~S7).

프로토타입 app-UI/training_plan.html 기준 UI 재설계.
"""
from __future__ import annotations

import html as _html
from datetime import date, timedelta

from src.web.helpers import fmt_pace, fmt_duration, no_data_card

# 운동 타입별 색상·라벨
_TYPE_STYLE: dict[str, tuple[str, str, str]] = {
    "easy":     ("linear-gradient(135deg,#00c853,#00e676)", "이지런",   "🟢"),
    "tempo":    ("linear-gradient(135deg,#ff9100,#ffab40)", "템포런",   "🟠"),
    "interval": ("linear-gradient(135deg,#ff1744,#ff5252)", "인터벌",   "🔴"),
    "long":     ("linear-gradient(135deg,#7c4dff,#b388ff)", "롱런",     "🟣"),
    "rest":     ("linear-gradient(135deg,#546e7a,#78909c)", "휴식",     "⚪"),
    "recovery": ("linear-gradient(135deg,#00bcd4,#4dd0e1)", "회복조깅", "🔵"),
    "race":     ("linear-gradient(135deg,#ffd600,#ffff00)", "레이스",   "🏁"),
}

# 타입별 CSS 클래스용 배경
_TYPE_BG: dict[str, str] = {
    "easy":     "rgba(0,255,136,0.15)",
    "tempo":    "rgba(255,170,0,0.15)",
    "interval": "rgba(255,68,68,0.15)",
    "long":     "rgba(128,0,255,0.15)",
    "rest":     "rgba(84,110,122,0.1)",
    "recovery": "rgba(0,188,212,0.15)",
    "race":     "rgba(255,214,0,0.15)",
}


def _esc(s: str) -> str:
    return _html.escape(str(s))


# ── S1: 헤더 액션 ─────────────────────────────────────────────────────

def render_header_actions(has_plan: bool) -> str:
    """타이틀 영역 액션 버튼 (공유 + 플랜 생성)."""
    label = "🗓️ 재생성" if has_plan else "🗓️ 플랜 생성"
    return (
        "<div style='display:flex;justify-content:space-between;align-items:center;"
        "padding:16px 0;border-bottom:1px solid var(--card-border);margin-bottom:20px;'>"
        "<div style='font-size:18px;font-weight:bold;'>훈련 계획</div>"
        "<div style='display:flex;gap:10px;'>"
        "<button onclick=\"if(navigator.clipboard){navigator.clipboard.writeText("
        "window.location.href).then(function(){alert('링크 복사됨');});}\" "
        "style='background:rgba(255,255,255,0.1);border:none;color:#fff;"
        "padding:8px 16px;border-radius:20px;cursor:pointer;font-size:13px;'>"
        "📤 공유</button>"
        "<form method='POST' action='/training/generate' style='margin:0;'>"
        f"<button type='submit' style='background:linear-gradient(135deg,#00d4ff,#00ff88);"
        f"color:#000;border:none;padding:8px 16px;border-radius:20px;font-size:13px;"
        f"font-weight:bold;cursor:pointer;'>{label}</button></form>"
        "</div></div>"
    )


# ── S2: 목표 카드 ─────────────────────────────────────────────────────

def render_goal_card(goal: dict | None, utrs_val: float | None = None) -> str:
    """활성 목표 + UTRS 미니 표시."""
    if not goal:
        return (
            "<div class='card' style='text-align:center;padding:1.5rem;'>"
            "<p class='muted'>설정된 목표가 없습니다.</p>"
            "<p style='font-size:0.85rem;color:var(--muted);'>"
            "아래 🎯 목표 관리에서 목표를 추가하세요.</p>"
            "</div>"
        )

    name = goal.get("name", "")
    dist = goal.get("distance_km", 0)
    race_date = goal.get("race_date")
    target_time = goal.get("target_time_sec")
    target_pace = goal.get("target_pace_sec_km")

    # D-day
    dday = ""
    if race_date:
        try:
            days_left = (date.fromisoformat(race_date) - date.today()).days
            if days_left > 0:
                dday = f"D-{days_left}"
            elif days_left == 0:
                dday = "D-Day!"
            else:
                dday = "완료"
        except ValueError:
            pass

    pace_str = fmt_pace(target_pace) + "/km" if target_pace else ""
    time_str = fmt_duration(target_time) if target_time else ""
    target_info = " / ".join(filter(None, [time_str, pace_str]))

    # UTRS 미니 배지
    utrs_html = ""
    if utrs_val is not None:
        color = "#00ff88" if utrs_val >= 70 else "#ffaa00" if utrs_val >= 40 else "#ff4444"
        utrs_html = (
            f"<div style='display:flex;align-items:center;gap:6px;margin-top:8px;'>"
            f"<span style='font-size:0.75rem;color:var(--muted);'>훈련 준비도</span>"
            f"<span style='font-size:1rem;font-weight:bold;color:{color};'>"
            f"UTRS {utrs_val:.0f}</span></div>"
        )

    return (
        "<div class='card' style='border-left:4px solid #00d4ff;'>"
        "<div style='display:flex;justify-content:space-between;align-items:flex-start;'>"
        f"<div><h3 style='margin:0 0 4px;'>🎯 {_esc(name)}</h3>"
        f"<span class='muted' style='font-size:0.85rem;'>{dist:.1f}km"
        + (f" · {target_info}" if target_info else "")
        + (f" · {race_date}" if race_date else "")
        + "</span>"
        + utrs_html
        + "</div>"
        + (f"<span style='font-size:1.8rem;font-weight:bold;color:#00d4ff;'>{dday}</span>"
           if dday else "")
        + "</div></div>"
    )


# ── S3: 주간 요약 (4칸 그리드) ────────────────────────────────────────

def render_weekly_summary(
    workouts: list[dict],
    utrs_val: float | None = None,
) -> str:
    """주간 요약: 완료율 / 목표km / 목표시간 / UTRS."""
    if not workouts:
        return ""

    non_rest = [w for w in workouts if w.get("workout_type") != "rest"]
    total_train = len(non_rest)
    completed = sum(1 for w in non_rest if w.get("completed"))
    total_km = sum(w.get("distance_km") or 0 for w in workouts)

    # 총 예상 시간 (거리 / 평균 페이스)
    total_sec = 0
    for w in workouts:
        d = w.get("distance_km") or 0
        p_avg = None
        p_min = w.get("target_pace_min")
        p_max = w.get("target_pace_max")
        if p_min and p_max:
            p_avg = (p_min + p_max) / 2
        if d and p_avg:
            total_sec += d * p_avg
    hours = total_sec / 3600
    time_str = f"{hours:.1f}" if hours else "—"

    comp_pct = int(completed / total_train * 100) if total_train else 0
    km_pct = min(100, int(total_km / max(total_km, 1) * 100)) if total_km else 0
    utrs_pct = int(utrs_val) if utrs_val is not None else 0

    return (
        "<div class='card'>"
        "<div style='display:flex;align-items:center;gap:10px;margin-bottom:16px;'>"
        "<div style='width:4px;height:20px;background:linear-gradient(135deg,#00d4ff,#00ff88);"
        "border-radius:2px;'></div>"
        "<span style='font-size:16px;font-weight:bold;'>이번 주 요약</span></div>"
        "<div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));"
        "gap:14px;'>"
        + _summary_stat("훈련 완료", f"{completed}/{total_train}", comp_pct)
        + _summary_stat("목표 km", f"{total_km:.1f}", km_pct)
        + _summary_stat("목표 시간", f"{time_str}h", min(100, int(hours / max(hours, 0.1) * 100)))
        + _summary_stat("UTRS", f"{utrs_val:.0f}" if utrs_val is not None else "—", utrs_pct)
        + "</div></div>"
    )


def _summary_stat(label: str, value: str, pct: int) -> str:
    return (
        "<div style='background:rgba(255,255,255,0.05);border-radius:16px;"
        "padding:18px;text-align:center;'>"
        f"<div style='font-size:24px;font-weight:bold;color:#00d4ff;'>{value}</div>"
        f"<div style='font-size:11px;color:rgba(255,255,255,0.6);margin-top:6px;'>{label}</div>"
        f"<div style='height:4px;background:rgba(255,255,255,0.1);border-radius:2px;"
        f"margin-top:10px;overflow:hidden;'>"
        f"<div style='height:100%;width:{pct}%;background:linear-gradient(90deg,#00d4ff,#00ff88);"
        f"border-radius:2px;'></div></div></div>"
    )


# ── S4: 컨디션 조정 ───────────────────────────────────────────────────

def render_adjustment_card(adj: dict | None, cirs_val: float | None = None,
                           utrs_val: float | None = None) -> str:
    """오늘 컨디션 조정 카드 + 웰니스 상세 + CIRS/UTRS 반영."""
    if not adj:
        return ""

    wellness = adj.get("wellness", {})
    fatigue = adj.get("fatigue_level", "low")

    # 피로도 한국어 변환
    _FATIGUE_KO = {"low": "낮음", "moderate": "보통", "high": "높음"}
    fatigue_ko = _FATIGUE_KO.get(fatigue, fatigue)

    # CIRS/UTRS 기반 경고 오버라이드
    cirs_warning = ""
    if cirs_val is not None and cirs_val >= 75:
        cirs_warning = (
            f"<p style='color:#ff4444;font-weight:600;margin:0 0 6px;'>"
            f"⚠️ CIRS {cirs_val:.0f} — 부상 위험 높음. 훈련 강도를 낮추세요.</p>"
        )
        fatigue_ko = "높음"
    elif cirs_val is not None and cirs_val >= 50:
        cirs_warning = (
            f"<p style='color:#ffaa00;margin:0 0 6px;'>"
            f"CIRS {cirs_val:.0f} — 주의 필요. 워밍업/쿨다운 충실히.</p>"
        )

    utrs_note = ""
    if utrs_val is not None and utrs_val < 40:
        utrs_note = (
            f"<p style='color:#ff4444;margin:0 0 6px;'>"
            f"UTRS {utrs_val:.0f} — 회복이 필요합니다. 가벼운 활동만 권장.</p>"
        )

    # 웰니스 미니 표시
    well_items = []
    bb = wellness.get("body_battery")
    if bb is not None:
        c = "#00ff88" if bb >= 50 else "#ffaa00" if bb >= 30 else "#ff4444"
        well_items.append(f"<span style='color:{c};'>⚡ BB {bb}</span>")
    ss = wellness.get("sleep_score")
    if ss is not None:
        c = "#00ff88" if ss >= 60 else "#ffaa00" if ss >= 40 else "#ff4444"
        well_items.append(f"<span style='color:{c};'>😴 수면 {ss:.0f}</span>")
    hrv = wellness.get("hrv_value")
    if hrv is not None:
        well_items.append(f"<span style='color:var(--secondary);'>💓 HRV {hrv:.0f}</span>")
    tsb = adj.get("tsb")
    if tsb is not None:
        c = "#00ff88" if tsb > 0 else "#ffaa00" if tsb > -15 else "#ff4444"
        well_items.append(f"<span style='color:{c};'>📊 TSB {tsb:+.1f}</span>")

    wellness_html = (
        "<div style='display:flex;gap:12px;flex-wrap:wrap;margin-top:8px;"
        "font-size:0.82rem;'>" + " ".join(well_items) + "</div>"
    ) if well_items else ""

    if not adj.get("adjusted"):
        color = "#00ff88" if fatigue == "low" and not cirs_warning else "#ffaa00" if not cirs_warning else "#ff4444"
        boost = " 볼륨 부스트 가능! 💪" if adj.get("volume_boost") and not cirs_warning else ""
        msg = "계획대로 진행하세요." if not cirs_warning else "컨디션을 확인하세요."
        return (
            f"<div class='card' style='border-left:4px solid {color};'>"
            "<h3 style='margin:0 0 8px;'>오늘 컨디션</h3>"
            + cirs_warning + utrs_note
            + f"<p style='margin:0;'>피로도: <strong>{fatigue_ko}</strong> — {msg}{boost}</p>"
            + wellness_html
            + "</div>"
        )

    orig = adj.get("original_type", "")
    new_type = adj.get("adjusted_type", "")
    reason = adj.get("adjustment_reason", "")
    color = "#ff4444" if fatigue == "high" or cirs_warning else "#ffaa00"
    orig_label = _TYPE_STYLE.get(orig, ("", orig, ""))[1]
    new_label = _TYPE_STYLE.get(new_type, ("", new_type, ""))[1]

    return (
        f"<div class='card' style='border-left:4px solid {color};'>"
        "<h3 style='margin:0 0 8px;'>⚠️ 오늘 컨디션 조정</h3>"
        + cirs_warning + utrs_note
        + f"<p style='margin:0 0 4px;'>피로도: <strong>{fatigue_ko}</strong></p>"
        f"<p style='margin:0 0 4px;'>{orig_label} → <strong>{new_label}</strong>으로 변경</p>"
        + (f"<p class='muted' style='margin:0;font-size:0.85rem;'>{_esc(reason)}</p>"
           if reason else "")
        + wellness_html
        + "</div>"
    )


# ── S5: 주간 캘린더 (7열 그리드) ──────────────────────────────────────

def render_week_calendar(
    workouts: list[dict],
    week_start: date,
    week_offset: int = 0,
) -> str:
    """7열 그리드 캘린더 + 주 네비게이션 + 완료 토글/삭제 버튼."""
    today_iso = date.today().isoformat()

    # 네비게이션
    month_str = f"{week_start.year}년 {week_start.month}월"
    week_end = week_start + timedelta(days=6)
    range_str = f"{week_start.month}/{week_start.day}~{week_end.month}/{week_end.day}"
    prev_w = week_offset - 1
    next_w = week_offset + 1

    nav = (
        "<div style='display:flex;justify-content:space-between;align-items:center;"
        "margin-bottom:16px;flex-wrap:wrap;gap:8px;'>"
        "<div style='display:flex;align-items:center;gap:12px;'>"
        f"<a href='/training?week={prev_w}' style='width:32px;height:32px;"
        "background:rgba(255,255,255,0.1);border-radius:50%;display:flex;"
        "align-items:center;justify-content:center;text-decoration:none;color:#fff;'>←</a>"
        f"<span style='font-size:16px;font-weight:bold;'>{month_str}</span>"
        f"<span style='font-size:12px;color:var(--muted);'>{range_str}</span>"
        f"<a href='/training?week={next_w}' style='width:32px;height:32px;"
        "background:rgba(255,255,255,0.1);border-radius:50%;display:flex;"
        "align-items:center;justify-content:center;text-decoration:none;color:#fff;'>→</a>"
        "</div>"
        "<div style='display:flex;gap:6px;'>"
        f"<a href='/training/export.ics?week={week_offset}' style='background:rgba(255,255,255,0.1);"
        "color:rgba(255,255,255,0.7);padding:6px 14px;border-radius:20px;font-size:12px;"
        "text-decoration:none;'>📅 ICS</a>"
        + _view_toggle_btn("주간", True)
        + "</div></div>"
    )

    # 7일 데이터 매핑
    day_names = ["월", "화", "수", "목", "금", "토", "일"]
    workout_by_date: dict[str, dict] = {w["date"]: w for w in workouts}

    # 7열 그리드
    cols = ""
    for i in range(7):
        d = week_start + timedelta(days=i)
        d_iso = d.isoformat()
        is_today = d_iso == today_iso
        w = workout_by_date.get(d_iso)

        header_cls = "color:#00d4ff;font-weight:bold;" if is_today else "color:rgba(255,255,255,0.6);"
        day_border = "border:1px solid rgba(0,212,255,0.5);" if is_today else ""
        num_style = "color:#00d4ff;font-weight:bold;" if is_today else "color:rgba(255,255,255,0.6);"

        # 워크아웃 아이템
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

            pace_str = ""
            p_min = w.get("target_pace_min")
            p_max = w.get("target_pace_max")
            if p_min and p_max:
                pace_str = f"{fmt_pace(p_min)}~{fmt_pace(p_max)}"

            # 완료 토글 + 삭제 버튼
            actions = ""
            if wid:
                toggle_label = "↩️" if completed else "✓"
                actions = (
                    "<div style='display:flex;gap:4px;margin-top:4px;'>"
                    f"<form method='POST' action='/training/workout/{wid}/toggle' style='margin:0;'>"
                    f"<input type='hidden' name='week' value='{week_offset}'/>"
                    f"<button type='submit' style='background:rgba(255,255,255,0.15);border:none;"
                    f"color:#fff;padding:2px 6px;border-radius:6px;font-size:10px;cursor:pointer;'>"
                    f"{toggle_label}</button></form>"
                    f"<form method='POST' action='/training/workout/{wid}/delete' style='margin:0;'>"
                    f"<button type='submit' style='background:rgba(255,68,68,0.2);border:none;"
                    f"color:#ff4444;padding:2px 6px;border-radius:6px;font-size:10px;cursor:pointer;'"
                    f" onclick=\"return confirm('삭제?')\">✕</button></form></div>"
                )

            workout_html = (
                f"<div style='background:{bg};border-radius:8px;padding:8px;"
                f"font-size:11px;transition:all 0.2s;{comp_cls}'>"
                f"<div style='font-weight:600;margin-bottom:2px;'>{icon} {label_ko}{check}</div>"
                + (f"<div style='font-size:10px;color:rgba(255,255,255,0.7);'>{dist_str}</div>"
                   if dist_str else "")
                + (f"<div style='font-size:9px;color:rgba(255,255,255,0.5);'>{pace_str}</div>"
                   if pace_str else "")
                + actions
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
            + "</div></div>"
        )

    # 모바일 스크롤 지원
    grid = (
        "<div style='display:grid;grid-template-columns:repeat(7,1fr);gap:10px;"
        "overflow-x:auto;min-width:0;'>"
        + cols + "</div>"
    )

    return (
        "<div class='card'>"
        + nav + grid
        + "</div>"
    )


def _view_toggle_btn(label: str, active: bool) -> str:
    bg = "rgba(0,212,255,0.2)" if active else "rgba(255,255,255,0.1)"
    color = "#00d4ff" if active else "rgba(255,255,255,0.7)"
    return (
        f"<span style='background:{bg};color:{color};padding:6px 14px;"
        f"border-radius:20px;font-size:12px;cursor:pointer;'>{label}</span>"
    )


# ── S6: AI 훈련 추천 ──────────────────────────────────────────────────

def render_ai_recommendation(
    utrs_val: float | None,
    cirs_val: float | None,
    cirs_json: dict,
    workouts: list[dict],
) -> str:
    """UTRS/CIRS 기반 규칙 기반 AI 훈련 추천 카드."""
    # 데이터 없으면 미표시
    if utrs_val is None and cirs_val is None:
        return ""

    lines: list[str] = []

    # UTRS 기반 메시지
    if utrs_val is not None:
        if utrs_val >= 70:
            lines.append(
                f"현재 <strong>UTRS {utrs_val:.0f}</strong>으로 "
                "고강도 훈련 준비가 완료되었습니다."
            )
        elif utrs_val >= 40:
            lines.append(
                f"현재 <strong>UTRS {utrs_val:.0f}</strong>으로 "
                "보통 수준입니다. 중강도 훈련을 권장합니다."
            )
        else:
            lines.append(
                f"현재 <strong>UTRS {utrs_val:.0f}</strong>으로 "
                "회복이 필요합니다. 가벼운 운동이나 휴식을 권장합니다."
            )

    # CIRS 기반 부상 위험도
    if cirs_val is not None:
        grade = cirs_json.get("grade", "")
        if cirs_val >= 70:
            lines.append(
                f"⚠️ <strong>CIRS {cirs_val:.0f}</strong> — "
                "부상 위험이 높습니다. 훈련 강도를 줄이세요."
            )
        elif cirs_val >= 40:
            lines.append(
                f"CIRS {cirs_val:.0f} ({grade}) — "
                "부상 위험 보통. 워밍업과 쿨다운을 충실히 하세요."
            )

    # 이번 주 주요 훈련 안내
    key_workouts = [
        w for w in workouts
        if w.get("workout_type") in ("interval", "tempo", "long")
        and not w.get("completed")
    ]
    if key_workouts:
        tips: list[str] = []
        for w in key_workouts[:3]:
            wtype = w.get("workout_type", "")
            label = _TYPE_STYLE.get(wtype, ("", wtype, ""))[1]
            d = w.get("distance_km")
            wdate = w.get("date", "")
            d_str = f" {d:.1f}km" if d else ""
            tips.append(f"{wdate} {label}{d_str}")
        if tips:
            lines.append("이번 주 핵심 훈련: " + " / ".join(tips))

    if not lines:
        return ""

    content = "</p><p style='margin:8px 0;'>".join(lines)

    return (
        "<div style='background:linear-gradient(135deg,rgba(0,212,255,0.1),rgba(0,255,136,0.1));"
        "border-radius:20px;padding:24px;margin-top:16px;margin-bottom:16px;"
        "border:1px solid rgba(0,212,255,0.3);'>"
        "<div style='display:flex;align-items:center;gap:12px;margin-bottom:14px;'>"
        "<div style='width:44px;height:44px;background:linear-gradient(135deg,#00d4ff,#00ff88);"
        "border-radius:50%;display:flex;align-items:center;justify-content:center;"
        "font-size:22px;'>🤖</div>"
        "<span style='font-size:16px;font-weight:bold;'>AI 훈련 추천</span></div>"
        f"<div style='font-size:13px;line-height:1.7;color:rgba(255,255,255,0.9);'>"
        f"<p style='margin:0 0 8px;'>{content}</p></div></div>"
    )


# ── S7: 캘린더 연동 상태 ──────────────────────────────────────────────

_SERVICE_LABEL: dict[str, tuple[str, str]] = {
    "garmin":    ("⌚", "Garmin Connect"),
    "strava":    ("🏃", "Strava"),
    "intervals": ("📊", "Intervals.icu"),
    "runalyze":  ("📈", "Runalyze"),
}


def render_sync_status(sync_info: list[dict]) -> str:
    """소스별 동기화 상태 표시."""
    if not sync_info:
        return ""

    has_recent = any(s.get("status") == "completed" for s in sync_info)
    status_dot = (
        "<div style='display:flex;align-items:center;gap:6px;font-size:12px;"
        + (f"color:#00ff88;'>"
           "<span style='width:7px;height:7px;background:#00ff88;border-radius:50%;"
           "display:inline-block;'></span>동기화 완료"
           if has_recent else
           "color:var(--muted);'>"
           "<span style='width:7px;height:7px;background:var(--muted);border-radius:50%;"
           "display:inline-block;'></span>대기 중")
        + "</div>"
    )

    platforms = ""
    for s in sync_info:
        svc = s.get("service", "")
        icon, label = _SERVICE_LABEL.get(svc, ("📌", svc))
        last = s.get("last_sync", "")
        # 날짜만 간략히 표시
        short_date = last[:16] if last else "—"
        platforms += (
            f"<div style='display:flex;align-items:center;gap:8px;"
            f"background:rgba(255,255,255,0.08);border-radius:20px;"
            f"padding:8px 14px;font-size:12px;'>"
            f"<span>{icon}</span>"
            f"<span>{_esc(label)}</span>"
            f"<span style='color:var(--muted);font-size:10px;'>{short_date}</span>"
            f"</div>"
        )

    return (
        "<div class='card'>"
        "<div style='display:flex;justify-content:space-between;align-items:center;"
        "margin-bottom:14px;'>"
        "<span style='font-size:16px;font-weight:bold;'>데이터 연동</span>"
        + status_dot
        + "</div>"
        f"<div style='display:flex;gap:10px;flex-wrap:wrap;'>{platforms}</div>"
        "</div>"
    )

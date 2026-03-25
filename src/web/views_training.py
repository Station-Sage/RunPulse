"""훈련 계획 뷰 — Flask Blueprint.

/training       : 이번 주 훈련 플랜 + 목표 + 컨디션 조정
POST /training/generate : 플랜 자동 생성
"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from flask import Blueprint, redirect, request

from src.utils.config import load_config
from src.web.helpers import (
    db_path, fmt_pace, html_page, no_data_card,
)

training_bp = Blueprint("training", __name__)

# 운동 타입별 색상·라벨
_TYPE_STYLE: dict[str, tuple[str, str, str]] = {
    # type: (gradient, label_ko, icon)
    "easy":     ("linear-gradient(135deg,#00c853,#00e676)", "이지런",   "🟢"),
    "tempo":    ("linear-gradient(135deg,#ff9100,#ffab40)", "템포런",   "🟠"),
    "interval": ("linear-gradient(135deg,#ff1744,#ff5252)", "인터벌",   "🔴"),
    "long":     ("linear-gradient(135deg,#7c4dff,#b388ff)", "롱런",     "🟣"),
    "rest":     ("linear-gradient(135deg,#546e7a,#78909c)", "휴식",     "⚪"),
    "recovery": ("linear-gradient(135deg,#00bcd4,#4dd0e1)", "회복조깅", "🔵"),
    "race":     ("linear-gradient(135deg,#ffd600,#ffff00)", "레이스",   "🏁"),
}


# ── 렌더링 헬퍼 ──────────────────────────────────────────────────────────


def _render_goal_card(goal: dict | None) -> str:
    """활성 목표 카드."""
    if not goal:
        return (
            "<div class='card' style='text-align:center;padding:1.5rem;'>"
            "<p class='muted'>설정된 목표가 없습니다.</p>"
            "<p style='font-size:0.85rem;color:var(--muted);'>"
            "<code>python src/plan.py goal add</code>로 목표를 추가하세요.</p>"
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
            dday = f"D-{days_left}" if days_left > 0 else "D-Day!" if days_left == 0 else "완료"
        except ValueError:
            pass

    pace_str = fmt_pace(target_pace) + "/km" if target_pace else ""
    from src.web.helpers import fmt_duration
    time_str = fmt_duration(target_time) if target_time else ""
    target_info = " / ".join(filter(None, [time_str, pace_str]))

    return (
        "<div class='card' style='border-left:4px solid #00d4ff;'>"
        "<div style='display:flex;justify-content:space-between;align-items:center;'>"
        f"<div><h3 style='margin:0 0 4px;'>🎯 {_esc(name)}</h3>"
        f"<span class='muted' style='font-size:0.85rem;'>{dist:.1f}km"
        + (f" · {target_info}" if target_info else "")
        + (f" · {race_date}" if race_date else "")
        + "</span></div>"
        + (f"<span style='font-size:1.5rem;font-weight:bold;color:#00d4ff;'>{dday}</span>" if dday else "")
        + "</div></div>"
    )


def _render_weekly_summary(workouts: list[dict]) -> str:
    """주간 요약 카드 (완료율, 총 거리)."""
    if not workouts:
        return ""
    total = len(workouts)
    completed = sum(1 for w in workouts if w.get("completed"))
    total_km = sum(w.get("distance_km") or 0 for w in workouts)
    non_rest = [w for w in workouts if w.get("workout_type") != "rest"]
    train_days = len(non_rest)

    pct = int(completed / total * 100) if total else 0
    return (
        "<div class='card'>"
        "<h3 style='margin:0 0 12px;'>이번 주 요약</h3>"
        "<div style='display:flex;gap:16px;flex-wrap:wrap;'>"
        + _stat_pill("완료", f"{completed}/{train_days}", pct)
        + _stat_pill("거리", f"{total_km:.1f}km", min(int(total_km / max(total_km, 1) * 100), 100))
        + _stat_pill("훈련일", f"{train_days}일", int(train_days / 7 * 100))
        + "</div></div>"
    )


def _stat_pill(label: str, value: str, pct: int) -> str:
    color = "#00ff88" if pct >= 80 else "#ffaa00" if pct >= 50 else "#ff4444"
    return (
        f"<div style='flex:1;min-width:80px;background:rgba(255,255,255,0.05);"
        f"border-radius:12px;padding:12px;text-align:center;'>"
        f"<div style='font-size:0.75rem;color:var(--muted);margin-bottom:4px;'>{label}</div>"
        f"<div style='font-size:1.2rem;font-weight:bold;'>{value}</div>"
        f"<div style='height:3px;background:rgba(255,255,255,0.1);border-radius:2px;margin-top:6px;'>"
        f"<div style='height:100%;width:{pct}%;background:{color};border-radius:2px;'></div>"
        f"</div></div>"
    )


def _render_week_calendar(workouts: list[dict]) -> str:
    """7일 캘린더 뷰."""
    if not workouts:
        return ""
    today_iso = date.today().isoformat()
    rows = ""
    for w in workouts:
        wdate = w.get("date", "")
        wtype = w.get("workout_type", "easy")
        dist = w.get("distance_km")
        desc = w.get("description", "")
        completed = w.get("completed", False)
        pace_min = w.get("target_pace_min")
        pace_max = w.get("target_pace_max")

        style_info = _TYPE_STYLE.get(wtype, _TYPE_STYLE["easy"])
        gradient, label_ko, icon = style_info

        # 요일
        try:
            d = date.fromisoformat(wdate)
            day_name = ["월", "화", "수", "목", "금", "토", "일"][d.weekday()]
            day_num = d.day
        except ValueError:
            day_name, day_num = "?", ""

        is_today = wdate == today_iso
        border = "border:2px solid #00d4ff;" if is_today else "border:1px solid rgba(255,255,255,0.08);"
        opacity = "opacity:0.5;" if completed else ""
        strike = "text-decoration:line-through;" if completed else ""
        check = " ✅" if completed else ""

        pace_str = ""
        if pace_min and pace_max:
            pace_str = f"{fmt_pace(pace_min)}~{fmt_pace(pace_max)}/km"

        dist_str = f"{dist:.1f}km" if dist else ""

        rows += (
            f"<div style='display:flex;align-items:center;gap:10px;padding:10px 12px;"
            f"{border}border-radius:12px;margin-bottom:6px;{opacity}'>"
            f"<div style='min-width:32px;text-align:center;'>"
            f"<div style='font-size:0.7rem;color:var(--muted);'>{day_name}</div>"
            f"<div style='font-size:1rem;font-weight:bold;"
            + ("color:#00d4ff;" if is_today else "")
            + f"'>{day_num}</div></div>"
            f"<div style='width:6px;height:36px;border-radius:3px;background:{gradient};'></div>"
            f"<div style='flex:1;{strike}'>"
            f"<div style='font-size:0.9rem;font-weight:600;'>{icon} {label_ko}"
            + (f" — {dist_str}" if dist_str else "")
            + f"{check}</div>"
            + (f"<div style='font-size:0.75rem;color:var(--muted);'>{pace_str}</div>" if pace_str else "")
            + "</div></div>"
        )

    return (
        "<div class='card'>"
        "<h3 style='margin:0 0 12px;'>주간 훈련 일정</h3>"
        + rows
        + "</div>"
    )


def _render_adjustment_card(adj: dict | None) -> str:
    """오늘 컨디션 조정 카드."""
    if not adj:
        return ""
    if not adj.get("adjusted"):
        fatigue = adj.get("fatigue_level", "low")
        color = "#00ff88" if fatigue == "low" else "#ffaa00"
        return (
            "<div class='card' style='border-left:4px solid " + color + ";'>"
            "<h3 style='margin:0 0 8px;'>오늘 컨디션</h3>"
            f"<p style='margin:0;'>피로도: <strong>{fatigue}</strong> — 계획대로 진행하세요."
            + (" 볼륨 부스트 가능! 💪" if adj.get("volume_boost") else "")
            + "</p></div>"
        )

    orig = adj.get("original_type", "")
    new = adj.get("adjusted_type", "")
    reason = adj.get("adjustment_reason", "")
    fatigue = adj.get("fatigue_level", "moderate")
    color = "#ff4444" if fatigue == "high" else "#ffaa00"

    orig_label = _TYPE_STYLE.get(orig, ("", orig, ""))[1]
    new_label = _TYPE_STYLE.get(new, ("", new, ""))[1]

    return (
        f"<div class='card' style='border-left:4px solid {color};'>"
        "<h3 style='margin:0 0 8px;'>⚠️ 오늘 컨디션 조정</h3>"
        f"<p style='margin:0 0 4px;'>피로도: <strong>{fatigue}</strong></p>"
        f"<p style='margin:0 0 4px;'>{orig_label} → <strong>{new_label}</strong>으로 변경</p>"
        + (f"<p class='muted' style='margin:0;font-size:0.85rem;'>{_esc(reason)}</p>" if reason else "")
        + "</div>"
    )


def _render_generate_form(has_plan: bool) -> str:
    """플랜 생성 폼."""
    label = "플랜 재생성" if has_plan else "플랜 생성"
    return (
        "<div class='card' style='text-align:center;'>"
        "<form method='POST' action='/training/generate'>"
        f"<button type='submit' style='background:linear-gradient(135deg,#00d4ff,#00ff88);"
        f"color:#000;border:none;padding:12px 32px;border-radius:24px;font-size:1rem;"
        f"font-weight:bold;cursor:pointer;'>🗓️ {label}</button>"
        "<p class='muted' style='margin:8px 0 0;font-size:0.8rem;'>"
        "활성 목표 + 현재 피트니스 기반 규칙 기반 자동 생성</p>"
        "</form></div>"
    )


def _esc(s: str) -> str:
    import html
    return html.escape(str(s))


# ── 라우트 ──────────────────────────────────────────────────────────────


@training_bp.route("/training")
def training_page():
    """훈련 계획 페이지."""
    dbp = db_path()
    if not dbp or not dbp.exists():
        body = no_data_card("훈련 계획", "데이터 수집 중입니다. 동기화 후 확인하세요.")
        return html_page("훈련 계획", body, active_tab="training")

    try:
        conn = sqlite3.connect(str(dbp))
        try:
            from src.training.goals import get_active_goal
            from src.training.planner import get_planned_workouts
            from src.training.adjuster import adjust_todays_plan

            config = load_config()
            goal = get_active_goal(conn)
            workouts = get_planned_workouts(conn)
            adjustment = None
            try:
                adjustment = adjust_todays_plan(conn, config)
            except Exception:
                pass

            body = (
                "<div style='max-width:1200px;margin:0 auto;padding:20px;padding-bottom:100px;'>"
                + _render_goal_card(goal)
                + _render_weekly_summary(workouts)
                + _render_adjustment_card(adjustment)
                + _render_week_calendar(workouts)
                + _render_generate_form(bool(workouts))
                + "</div>"
            )
        finally:
            conn.close()
    except Exception as exc:
        body = (
            "<div class='card'><p style='color:var(--red);'>오류: "
            + _esc(str(exc))
            + "</p><p class='muted'>데이터 수집 중이거나 DB에 문제가 있을 수 있습니다.</p></div>"
        )

    return html_page("훈련 계획", body, active_tab="training")


@training_bp.route("/training/generate", methods=["POST"])
def training_generate():
    """규칙 기반 주간 플랜 생성 후 /training 으로 리다이렉트."""
    dbp = db_path()
    if not dbp or not dbp.exists():
        return redirect("/training")

    try:
        conn = sqlite3.connect(str(dbp))
        try:
            from src.training.planner import generate_weekly_plan, save_weekly_plan
            config = load_config()
            plan = generate_weekly_plan(conn, config=config)
            save_weekly_plan(conn, plan)
            conn.commit()
        finally:
            conn.close()
    except Exception:
        pass  # 실패해도 리다이렉트

    return redirect("/training")

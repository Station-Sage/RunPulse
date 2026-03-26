"""훈련 계획 뷰 — Flask Blueprint.

/training            : 주간 훈련 플랜 + 목표 + 컨디션 + AI 추천
CRUD/목표/ICS 라우트 → views_training_crud.py에 분리.
렌더러 → views_training_cards.py, 로더 → views_training_loaders.py.
"""
from __future__ import annotations

import html as _html
import sqlite3
from datetime import date, timedelta

from flask import Blueprint, redirect, request

from src.utils.config import load_config
from src.web.helpers import db_path, html_page, no_data_card
from src.web.views_training_cards import (
    render_adjustment_card,
    render_ai_recommendation,
    render_goal_card,
    render_header_actions,
    render_plan_overview,
    render_sync_status,
    render_week_calendar,
    render_weekly_summary,
)
from src.web.views_training_loaders import (
    load_adjustment,
    load_goal,
    load_sync_status,
    load_training_metrics,
    load_workouts,
)

training_bp = Blueprint("training", __name__)


# ── 메인 라우트 ──────────────────────────────────────────────────────────


@training_bp.route("/training")
def training_page():
    """훈련 계획 페이지."""
    dbp = db_path()
    if not dbp or not dbp.exists():
        body = no_data_card("훈련 계획", "데이터 수집 중입니다. 동기화 후 확인하세요.")
        return html_page("훈련 계획", body, active_tab="training")

    week_offset = request.args.get("week", 0, type=int)

    try:
        conn = sqlite3.connect(str(dbp))
        try:
            config = load_config()

            goal = load_goal(conn)
            workouts, week_start = load_workouts(conn, week_offset)

            # 빈 주이고 목표가 있으면 자동 생성
            if not workouts and goal and week_offset >= 0:
                try:
                    from src.training.planner import generate_weekly_plan, save_weekly_plan
                    plan = generate_weekly_plan(conn, config=config, week_start=week_start)
                    save_weekly_plan(conn, plan)
                    conn.commit()
                    workouts, week_start = load_workouts(conn, week_offset)
                except Exception:
                    pass

            adjustment = load_adjustment(conn, config)
            metrics = load_training_metrics(conn)
            sync_info = load_sync_status(conn)
            goals_list = _load_goals_list(conn)

            utrs_val = metrics.get("utrs_val")
            cirs_val = metrics.get("cirs_val")
            cirs_json = metrics.get("cirs_json", {})

            # 현재 훈련 단계 계산
            current_phase = "base"
            weeks_left = None
            if goal and goal.get("race_date"):
                try:
                    race_d = date.fromisoformat(goal["race_date"])
                    weeks_left = max(0, (race_d - date.today()).days // 7)
                    if weeks_left > 16: current_phase = "base"
                    elif weeks_left > 8: current_phase = "build"
                    elif weeks_left > 3: current_phase = "peak"
                    else: current_phase = "taper"
                except ValueError:
                    pass

            # AI 탭별 통합 호출
            _train_ai = {}
            try:
                from src.ai.ai_message import get_tab_ai
                _train_ai = get_tab_ai("training", conn, config) or {}
            except Exception:
                pass

            body = (
                render_header_actions(bool(workouts))
                + render_goal_card(goal, utrs_val)
                + render_plan_overview(goal, current_phase, weeks_left)
                + _render_goal_form(goals_list)
                + render_weekly_summary(workouts, utrs_val)
                + render_adjustment_card(adjustment, cirs_val=cirs_val, utrs_val=utrs_val,
                                       config=config, conn=conn)
                + render_week_calendar(workouts, week_start, week_offset)
                + _render_workout_form(week_start)
                + render_ai_recommendation(utrs_val, cirs_val, cirs_json, workouts,
                                          config=config, conn=conn,
                                          ai_override=_train_ai.get("coaching"))
                + render_sync_status(sync_info)
            )
        finally:
            conn.close()
    except Exception as exc:
        body = (
            "<div class='card'><p style='color:var(--red);'>오류: "
            + _html.escape(str(exc))
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
            from datetime import timedelta as _td
            config = load_config()
            base = date.today() - _td(days=date.today().weekday())
            # 4주치 생성 (이번 주 + 다음 3주)
            for w in range(4):
                ws = base + _td(weeks=w)
                plan = generate_weekly_plan(conn, config=config, week_start=ws)
                save_weekly_plan(conn, plan)
            conn.commit()
        finally:
            conn.close()
    except Exception:
        pass

    return redirect("/training")


# ── UI 헬퍼 ──────────────────────────────────────────────────────────


def _load_goals_list(conn: sqlite3.Connection) -> list[dict]:
    """목표 목록 로드."""
    from src.training.goals import list_goals
    try:
        return list_goals(conn, status="all")
    except Exception:
        return []


def _render_goal_form(goals: list[dict]) -> str:
    """목표 추가 폼 + 기존 목표 목록 (접이식)."""
    goal_rows = ""
    for g in goals:
        status_badge = {
            "active": "<span style='color:#00ff88;'>활성</span>",
            "completed": "<span style='color:var(--muted);'>완료</span>",
            "cancelled": "<span style='color:var(--muted);'>취소</span>",
        }.get(g.get("status", ""), "")
        actions = ""
        if g.get("status") == "active":
            gid = g["id"]
            actions = (
                f"<form method='POST' action='/training/goal/{gid}/complete' style='display:inline;margin:0;'>"
                "<button type='submit' style='background:rgba(0,255,136,0.2);border:none;color:#00ff88;"
                "padding:4px 10px;border-radius:12px;font-size:11px;cursor:pointer;'>완료</button></form>"
                f"<form method='POST' action='/training/goal/{gid}/cancel' style='display:inline;margin:0;'>"
                "<button type='submit' style='background:rgba(255,68,68,0.2);border:none;color:#ff4444;"
                "padding:4px 10px;border-radius:12px;font-size:11px;cursor:pointer;'>취소</button></form>"
            )
        goal_rows += (
            f"<div style='display:flex;justify-content:space-between;align-items:center;"
            f"padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.08);font-size:0.85rem;'>"
            f"<div><strong>{_html.escape(g.get('name', ''))}</strong> "
            f"<span class='muted'>{g.get('distance_km', '')}km</span> {status_badge}</div>"
            f"<div style='display:flex;gap:6px;'>{actions}</div></div>"
        )

    has_active = any(g.get("status") == "active" for g in goals)
    open_attr = " open" if not has_active else ""
    return (
        f"<details style='margin-bottom:16px;'{open_attr}>"
        "<summary style='cursor:pointer;background:rgba(255,255,255,0.05);border-radius:12px;"
        "padding:12px 16px;font-size:14px;font-weight:600;list-style:none;'>"
        "🎯 목표 관리</summary>"
        "<div class='card' style='margin-top:8px;'>"
        + (goal_rows if goal_rows else "<p class='muted'>설정된 목표가 없습니다.</p>")
        + "<form method='POST' action='/training/goal' style='margin-top:12px;display:flex;gap:8px;flex-wrap:wrap;'>"
        "<input name='name' placeholder='목표명 (예: 서울마라톤)' required "
        "style='flex:1;min-width:120px;background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.2);"
        "border-radius:8px;padding:8px 12px;color:#fff;font-size:13px;'/>"
        "<input name='distance_km' type='number' step='0.1' placeholder='거리(km)' required "
        "style='width:80px;background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.2);"
        "border-radius:8px;padding:8px 12px;color:#fff;font-size:13px;'/>"
        "<input name='race_date' type='date' placeholder='레이스 날짜' "
        "style='background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.2);"
        "border-radius:8px;padding:8px 12px;color:#fff;font-size:13px;'/>"
        "<input name='target_time' placeholder='목표시간 (H:MM:SS)' "
        "style='width:100px;background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.2);"
        "border-radius:8px;padding:8px 12px;color:#fff;font-size:13px;'/>"
        "<button type='submit' style='background:linear-gradient(135deg,#00d4ff,#00ff88);"
        "color:#000;border:none;padding:8px 16px;border-radius:8px;font-size:13px;"
        "font-weight:bold;cursor:pointer;'>추가</button></form>"
        "</div></details>"
    )


def _render_workout_form(week_start) -> str:
    """워크아웃 수동 추가 폼 (접이식)."""
    options = "".join(
        f"<option value='{(week_start + timedelta(days=i)).isoformat()}'>"
        f"{['월','화','수','목','금','토','일'][i]} ({(week_start + timedelta(days=i)).isoformat()})</option>"
        for i in range(7)
    )
    type_opts = "".join(
        f"<option value='{t}'>{l}</option>"
        for t, l in [("easy", "이지런"), ("tempo", "템포런"), ("interval", "인터벌"),
                     ("long", "롱런"), ("rest", "휴식"), ("recovery", "회복조깅"), ("race", "레이스")]
    )
    return (
        "<details style='margin-bottom:16px;'>"
        "<summary style='cursor:pointer;background:rgba(255,255,255,0.05);border-radius:12px;"
        "padding:12px 16px;font-size:14px;font-weight:600;list-style:none;'>"
        "➕ 워크아웃 추가</summary>"
        "<div class='card' style='margin-top:8px;'>"
        "<form method='POST' action='/training/workout' style='display:flex;gap:8px;flex-wrap:wrap;'>"
        f"<select name='date' style='background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.2);"
        f"border-radius:8px;padding:8px 12px;color:#fff;font-size:13px;'>{options}</select>"
        f"<select name='workout_type' style='background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.2);"
        f"border-radius:8px;padding:8px 12px;color:#fff;font-size:13px;'>{type_opts}</select>"
        "<input name='distance_km' type='number' step='0.1' placeholder='거리(km)' "
        "style='width:80px;background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.2);"
        "border-radius:8px;padding:8px 12px;color:#fff;font-size:13px;'/>"
        "<button type='submit' style='background:linear-gradient(135deg,#00d4ff,#00ff88);"
        "color:#000;border:none;padding:8px 16px;border-radius:8px;font-size:13px;"
        "font-weight:bold;cursor:pointer;'>추가</button></form></div></details>"
    )

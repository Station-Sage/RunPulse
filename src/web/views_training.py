"""훈련 계획 뷰 — Flask Blueprint.

/training            : 주간 훈련 플랜 + 목표 + 컨디션 + AI 추천
POST /training/generate : 플랜 자동 생성

UI 재설계: 7열 그리드 캘린더, UTRS/CIRS 통합, AI 추천 카드, 동기화 상태.
렌더러 → views_training_cards.py, 로더 → views_training_loaders.py.
"""
from __future__ import annotations

import html as _html
import sqlite3

from flask import Blueprint, redirect, request

from src.utils.config import load_config
from src.web.helpers import db_path, html_page, no_data_card
from src.web.views_training_cards import (
    render_adjustment_card,
    render_ai_recommendation,
    render_goal_card,
    render_header_actions,
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


# ── 라우트 ──────────────────────────────────────────────────────────────


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

            # 데이터 로드
            goal = load_goal(conn)
            workouts, week_start = load_workouts(conn, week_offset)
            adjustment = load_adjustment(conn, config)
            metrics = load_training_metrics(conn)
            sync_info = load_sync_status(conn)

            utrs_val = metrics.get("utrs_val")
            cirs_val = metrics.get("cirs_val")
            cirs_json = metrics.get("cirs_json", {})

            # 섹션 조립 (S1~S7)
            body = (
                render_header_actions(bool(workouts))           # S1
                + render_goal_card(goal, utrs_val)              # S2
                + render_weekly_summary(workouts, utrs_val)     # S3
                + render_adjustment_card(adjustment)            # S4
                + render_week_calendar(                         # S5
                    workouts, week_start, week_offset)
                + render_ai_recommendation(                     # S6
                    utrs_val, cirs_val, cirs_json, workouts)
                + render_sync_status(sync_info)                 # S7
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
            config = load_config()
            plan = generate_weekly_plan(conn, config=config)
            save_weekly_plan(conn, plan)
            conn.commit()
        finally:
            conn.close()
    except Exception:
        pass  # 실패해도 리다이렉트

    return redirect("/training")

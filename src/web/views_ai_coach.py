"""AI 코칭 뷰 — Flask Blueprint.

/ai-coach       : 일일 브리핑 + 추천 칩 + 웰니스 컨텍스트 + 채팅
POST /ai-coach/chat : 메시지 전송 → AI 응답
"""
from __future__ import annotations

import html as _html
import json
import sqlite3

from flask import Blueprint, redirect, request

from src.web.helpers import (
    db_path, fmt_pace, html_page, no_data_card, fmt_duration,
)
from src.web.views_ai_coach_cards import (
    render_briefing_card,
    render_chat_section,
    render_chips,
    render_coach_profile,
    render_recent_training,
    render_risk_summary,
    render_wellness_card,
)

ai_coach_bp = Blueprint("ai_coach", __name__)


# ── 데이터 로더 ────────────────────────────────────────────────────────


def _safe_json(raw) -> dict:
    if not raw:
        return {}
    try:
        return json.loads(raw) if isinstance(raw, str) else raw
    except (json.JSONDecodeError, TypeError):
        return {}


def _load_metric(conn: sqlite3.Connection, name: str):
    """최신 메트릭 값+JSON 반환."""
    row = conn.execute(
        "SELECT metric_value, metric_json FROM computed_metrics "
        "WHERE metric_name=? ORDER BY date DESC LIMIT 1", (name,),
    ).fetchone()
    if not row:
        return None, {}
    return row[0], _safe_json(row[1])


def _load_wellness(conn: sqlite3.Connection) -> dict:
    """오늘 웰니스 데이터."""
    from datetime import date
    row = conn.execute(
        "SELECT sleep_score, sleep_hours, hrv_value, resting_hr, body_battery, stress_avg "
        "FROM daily_wellness WHERE date=? AND source='garmin' LIMIT 1",
        (date.today().isoformat(),),
    ).fetchone()
    if not row:
        return {}
    keys = ["sleep_score", "sleep_hours", "hrv_value", "resting_hr", "body_battery", "stress_avg"]
    return {k: v for k, v in zip(keys, row) if v is not None}


# ── 브리핑 생성 ────────────────────────────────────────────────────────


def _generate_briefing(conn: sqlite3.Connection) -> str | None:
    """메트릭 기반 간이 브리핑 생성."""
    utrs_val, utrs_json = _load_metric(conn, "UTRS")
    cirs_val, cirs_json = _load_metric(conn, "CIRS")
    darp_val, darp_json = _load_metric(conn, "DARP_half")
    di_val, _ = _load_metric(conn, "DI")
    lsi_val, _ = _load_metric(conn, "LSI")
    acwr_val, acwr_json = _load_metric(conn, "ACWR")

    parts = []

    # 종합 판단 (코치 톤)
    if cirs_val is not None and cirs_val >= 75:
        parts.append("🚨 <strong>오늘은 쉬는 날입니다.</strong> 부상 위험이 높아 훈련을 중단하고 회복에 집중하세요.")
    elif utrs_val is not None and utrs_val < 40:
        parts.append("😴 <strong>회복이 필요합니다.</strong> 가벼운 스트레칭이나 산책 정도만 권장합니다.")
    elif utrs_val is not None and utrs_val >= 85:
        parts.append("🔥 <strong>컨디션 최고!</strong> 고강도 훈련(인터벌/템포)에 도전해보세요.")
    elif utrs_val is not None and utrs_val >= 70:
        parts.append("✅ <strong>정상 훈련 가능합니다.</strong> 계획대로 진행하세요.")
    elif utrs_val is not None:
        parts.append("⚡ <strong>볼륨을 줄이세요.</strong> 이지런이나 회복 조깅을 권장합니다.")

    # 세부 지표
    details = []
    if utrs_val is not None:
        details.append(f"준비도(UTRS) {int(utrs_val)}")
    if cirs_val is not None:
        details.append(f"부상위험(CIRS) {int(cirs_val)}")
    if acwr_val is not None:
        acwr_status = acwr_json.get("status") or acwr_json.get("risk", "")
        status_ko = {"optimal": "적정", "caution": "주의", "danger": "위험",
                     "undertraining": "부족"}.get(acwr_status, "")
        details.append(f"ACWR {acwr_val:.2f}" + (f"({status_ko})" if status_ko else ""))
    if lsi_val is not None and lsi_val > 1.0:
        details.append(f"부하 스파이크 {lsi_val:.1f}")
    if di_val is not None:
        details.append(f"내구성 {int(di_val)}")
    if details:
        parts.append("<span style='font-size:0.85rem;color:var(--muted);'>" + " · ".join(details) + "</span>")
    if darp_val is not None:
        # darp_json에 time_sec가 있으면 완주 시간, 없으면 페이스×거리로 추정
        darp_time = darp_json.get("time_sec") if darp_json else None
        if darp_time:
            parts.append(f"DARP 하프 예측 <strong>{fmt_duration(int(darp_time))}</strong>")
        else:
            # darp_val은 pace(sec/km), 하프=21.0975km
            est_sec = int(darp_val * 21.0975)
            parts.append(f"DARP 하프 예측 <strong>{fmt_duration(est_sec)}</strong>")

    if not parts:
        return None
    return "<p>" + "</p><p>".join(parts) + "</p>"


# ── 추천 칩 (suggestions.py 연동) ──────────────────────────────────────


def _load_chips(conn: sqlite3.Connection) -> list[dict]:
    """규칙 기반 추천 칩 로드."""
    try:
        from src.ai.suggestions import get_runner_state, rule_based_chips
        state = get_runner_state(conn)
        return rule_based_chips(state)
    except Exception:
        return []


def _load_recent_activities(conn: sqlite3.Connection, limit: int = 3) -> list[dict]:
    """최근 러닝 활동 요약 로드."""
    rows = conn.execute(
        "SELECT start_time, distance_km, duration_sec, avg_pace_sec_km "
        "FROM v_canonical_activities WHERE activity_type='running' "
        "ORDER BY start_time DESC LIMIT ?", (limit,),
    ).fetchall()
    return [{"date": str(r[0])[:10], "km": r[1], "sec": r[2], "pace": r[3]} for r in rows]


# ── 라우트 ──────────────────────────────────────────────────────────────


@ai_coach_bp.route("/ai-coach")
def ai_coach_page():
    """AI 코칭 페이지."""
    dbp = db_path()
    if not dbp or not dbp.exists():
        body = no_data_card("AI 코치", "데이터 수집 중입니다. 동기화 후 확인하세요.")
        return html_page("AI 코칭", body, active_tab="ai-coach")

    try:
        conn = sqlite3.connect(str(dbp))
        try:
            briefing_text = _generate_briefing(conn)
            wellness = _load_wellness(conn)
            chips = _load_chips(conn)
            recent = _load_recent_activities(conn)
            chat_history = _load_chat_history(conn)

            body = (
                '<div style="max-width:1200px;margin:0 auto;padding:20px;padding-bottom:100px;">'
                + render_coach_profile()
                + render_wellness_card(wellness)
                + '<div style="display:flex;gap:16px;flex-wrap:wrap;">'
                + '<div style="flex:1;min-width:280px;">'
                + render_recent_training(recent)
                + '</div>'
                + '<div style="flex:1;min-width:280px;">'
                + render_risk_summary(conn)
                + '</div></div>'
                + render_briefing_card(briefing_text)
                + render_chips(chips)
                + render_chat_section(chat_history)
                + '</div>'
            )
        finally:
            conn.close()
    except Exception as exc:
        body = (
            "<div class='card'><p style='color:var(--red);'>오류: "
            + _html.escape(str(exc))
            + "</p><p class='muted'>데이터 수집 중이거나 DB에 문제가 있을 수 있습니다.</p></div>"
        )

    return html_page("AI 코칭", body, active_tab="ai-coach")


# ── 채팅 라우트 ──────────────────────────────────────────────────────


@ai_coach_bp.route("/ai-coach/chat", methods=["POST"])
def ai_coach_chat():
    """사용자 메시지 수신 → AI 응답 생성 → 저장 → 리다이렉트."""
    dbp = db_path()
    if not dbp or not dbp.exists():
        return redirect("/ai-coach")

    user_msg = request.form.get("message", "").strip()
    chip_id = request.form.get("chip_id", "").strip() or None

    if not user_msg and not chip_id:
        return redirect("/ai-coach")

    # 칩 클릭이면 기본 메시지 설정
    if chip_id and not user_msg:
        from src.ai.suggestions import CHIP_REGISTRY
        chip_info = CHIP_REGISTRY.get(chip_id, {})
        user_msg = chip_info.get("label", chip_id)

    try:
        from src.ai.chat_engine import chat
        from src.utils.config import load_config

        conn = sqlite3.connect(str(dbp))
        try:
            config = load_config()
            conn.execute(
                "INSERT INTO chat_messages (role, content, chip_id) VALUES ('user', ?, ?)",
                (user_msg, chip_id),
            )
            ai_response = chat(conn, user_msg, config=config, chip_id=chip_id)
            ai_model = config.get("ai", {}).get("provider", "rule")
            conn.execute(
                "INSERT INTO chat_messages (role, content, chip_id, ai_model) VALUES ('assistant', ?, ?, ?)",
                (ai_response, chip_id, ai_model),
            )
            conn.commit()
        finally:
            conn.close()
    except Exception:
        pass

    return redirect("/ai-coach")


@ai_coach_bp.route("/ai-coach/prompt", methods=["GET"])
def ai_coach_get_prompt():
    """현재 컨텍스트로 프롬프트 생성 → JSON 반환 (복사용)."""
    from flask import jsonify
    dbp = db_path()
    if not dbp or not dbp.exists():
        return jsonify({"prompt": "데이터가 없습니다."})

    try:
        from src.ai.briefing import build_briefing_prompt
        conn = sqlite3.connect(str(dbp))
        try:
            prompt = build_briefing_prompt(conn)
        finally:
            conn.close()
        return jsonify({"prompt": prompt})
    except Exception as exc:
        return jsonify({"prompt": f"프롬프트 생성 실패: {exc}"})


@ai_coach_bp.route("/ai-coach/paste-response", methods=["POST"])
def ai_coach_paste_response():
    """사용자가 외부 AI 응답을 붙여넣기 → 저장."""
    dbp = db_path()
    if not dbp or not dbp.exists():
        return redirect("/ai-coach")

    response_text = request.form.get("ai_response", "").strip()
    if not response_text:
        return redirect("/ai-coach")

    try:
        conn = sqlite3.connect(str(dbp))
        try:
            conn.execute(
                "INSERT INTO chat_messages (role, content, ai_model) VALUES ('assistant', ?, 'genspark_manual')",
                (response_text,),
            )
            conn.commit()
        finally:
            conn.close()
    except Exception:
        pass

    return redirect("/ai-coach")


def _load_chat_history(conn: sqlite3.Connection, limit: int = 20) -> list[dict]:
    """최근 채팅 히스토리 로드."""
    try:
        rows = conn.execute(
            "SELECT role, content, chip_id, ai_model, created_at "
            "FROM chat_messages ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [
            {"role": r[0], "content": r[1], "chip_id": r[2], "ai_model": r[3], "time": r[4]}
            for r in reversed(rows)
        ]
    except Exception:
        return []

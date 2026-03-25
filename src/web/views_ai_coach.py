"""AI 코칭 뷰 — Flask Blueprint.

/ai-coach : 일일 브리핑 + 추천 칩 + 웰니스 컨텍스트
"""
from __future__ import annotations

import html as _html
import json
import sqlite3

from flask import Blueprint

from src.web.helpers import (
    db_path, fmt_pace, html_page, no_data_card,
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
    if utrs_val is not None:
        grade = (
            "고강도 훈련 최적" if utrs_val >= 85
            else "정상 훈련 가능" if utrs_val >= 70
            else "볼륨 감소 권장" if utrs_val >= 55
            else "완전 휴식 권장"
        )
        parts.append(f"UTRS <strong>{int(utrs_val)}/100</strong> — {grade}")
    if cirs_val is not None:
        risk = "안전" if cirs_val <= 25 else "주의" if cirs_val <= 50 else "경고" if cirs_val <= 75 else "위험"
        parts.append(f"CIRS <strong>{int(cirs_val)}/100</strong> — {risk}")
    if acwr_val is not None:
        status = acwr_json.get("status", "")
        status_ko = {"safe": "적정", "caution": "주의", "danger": "위험", "low": "부족"}.get(status, "")
        parts.append(f"ACWR <strong>{acwr_val:.2f}</strong>" + (f" — {status_ko}" if status_ko else ""))
    if lsi_val is not None:
        parts.append(f"LSI <strong>{lsi_val:.1f}</strong>" + (" ⚠️ 부하 급증" if lsi_val > 1.5 else ""))
    if di_val is not None:
        parts.append(f"내구성(DI) <strong>{int(di_val)}/100</strong>")
    if darp_val is not None:
        from src.web.helpers import fmt_duration
        parts.append(f"DARP 하프 예측 <strong>{fmt_duration(int(darp_val))}</strong>")

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


# ── 렌더링 ─────────────────────────────────────────────────────────────


def _render_coach_profile() -> str:
    return (
        '<div style="background:linear-gradient(135deg,rgba(0,212,255,0.1),rgba(0,255,136,0.1));'
        'border-radius:20px;padding:24px;margin-bottom:20px;display:flex;align-items:center;gap:20px;'
        'border:1px solid rgba(0,212,255,0.3)">'
        '<div style="width:64px;height:64px;background:linear-gradient(135deg,#00d4ff,#00ff88);'
        'border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:32px">'
        '🤖</div>'
        '<div><h2 style="font-size:18px;margin:0 0 4px">RunPulse AI 코치</h2>'
        '<p style="font-size:13px;color:rgba(255,255,255,0.6);margin:0">'
        '개인 맞춤형 훈련 분석 및 조언</p></div></div>'
    )


def _render_briefing_card(briefing_text: str | None) -> str:
    if not briefing_text:
        return no_data_card("오늘의 브리핑", "메트릭 데이터가 수집되면 브리핑이 생성됩니다")
    return (
        '<div class="card" style="border-left:4px solid #00d4ff;margin-bottom:16px;">'
        '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">'
        '<h3 style="margin:0;">오늘의 브리핑</h3>'
        '<span style="font-size:0.75rem;color:var(--muted);">메트릭 기반 자동 생성</span></div>'
        f'<div style="font-size:0.92rem;line-height:1.7;color:rgba(255,255,255,0.9)">'
        f'{briefing_text}</div></div>'
    )


def _render_wellness_card(wellness: dict) -> str:
    """오늘 웰니스 요약 카드."""
    if not wellness:
        return ""
    items = []
    if "body_battery" in wellness:
        bb = wellness["body_battery"]
        color = "#00ff88" if bb >= 60 else "#ffaa00" if bb >= 30 else "#ff4444"
        items.append(("🔋", "바디배터리", f"{bb}", color))
    if "sleep_score" in wellness:
        ss = wellness["sleep_score"]
        color = "#00ff88" if ss >= 70 else "#ffaa00" if ss >= 40 else "#ff4444"
        items.append(("😴", "수면", f"{int(ss)}", color))
    if "hrv_value" in wellness:
        items.append(("💓", "HRV", f"{int(wellness['hrv_value'])}ms", "#00d4ff"))
    if "resting_hr" in wellness:
        items.append(("❤️", "안정심박", f"{int(wellness['resting_hr'])}bpm", "#00d4ff"))
    if "stress_avg" in wellness:
        st = wellness["stress_avg"]
        color = "#00ff88" if st <= 30 else "#ffaa00" if st <= 60 else "#ff4444"
        items.append(("😰", "스트레스", f"{int(st)}", color))

    if not items:
        return ""

    cells = "".join(
        f"<div style='text-align:center;min-width:60px;'>"
        f"<div style='font-size:1.1rem;'>{icon}</div>"
        f"<div style='font-size:0.72rem;color:var(--muted);margin:2px 0;'>{label}</div>"
        f"<div style='font-size:1rem;font-weight:bold;color:{color};'>{val}</div></div>"
        for icon, label, val, color in items
    )
    return (
        f"<div class='card' style='margin-bottom:16px;'>"
        f"<h3 style='margin:0 0 12px;'>오늘 컨디션</h3>"
        f"<div style='display:flex;justify-content:space-around;flex-wrap:wrap;gap:8px;'>"
        f"{cells}</div></div>"
    )


def _render_chips(chips: list[dict]) -> str:
    """추천 칩 목록."""
    if not chips:
        return ""
    html_parts = []
    for chip in chips:
        label = _html.escape(chip.get("label", ""))
        html_parts.append(
            f'<button style="background:rgba(0,212,255,0.1);border:1px solid rgba(0,212,255,0.3);'
            f'border-radius:24px;padding:10px 18px;color:rgba(255,255,255,0.9);'
            f'font-size:0.85rem;cursor:pointer;white-space:nowrap;">{label}</button>'
        )
    return (
        '<div class="card" style="margin-bottom:16px;">'
        '<h3 style="margin:0 0 12px;">추천</h3>'
        '<div style="display:flex;flex-wrap:wrap;gap:10px;">'
        + "".join(html_parts)
        + '</div>'
        '<p class="muted" style="margin:8px 0 0;font-size:0.75rem;">'
        'v0.3에서 칩 클릭 시 AI 대화가 시작됩니다.</p></div>'
    )


def _render_chat_placeholder() -> str:
    """채팅 인터페이스 placeholder."""
    return (
        '<div class="card" style="margin-bottom:16px;">'
        '<h3 style="margin:0 0 12px;">대화</h3>'
        '<div style="background:rgba(255,255,255,0.03);border-radius:16px;'
        'padding:40px;text-align:center;min-height:120px;'
        'display:flex;flex-direction:column;align-items:center;justify-content:center;">'
        '<span style="font-size:1.5rem;margin-bottom:8px;">💬</span>'
        '<p class="muted" style="margin:0;font-size:0.9rem;">대화형 AI 코칭</p>'
        '<p class="muted" style="margin:4px 0 0;font-size:0.78rem;">v0.3에서 추가됩니다</p></div></div>'
    )


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

            body = (
                '<div style="max-width:1200px;margin:0 auto;padding:20px;padding-bottom:100px;">'
                + _render_coach_profile()
                + _render_wellness_card(wellness)
                + _render_briefing_card(briefing_text)
                + _render_chips(chips)
                + _render_chat_placeholder()
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

"""AI 코칭 뷰 — Flask Blueprint.

/ai-coach : 일일 브리핑 + 추천 칩 + 웰니스 컨텍스트
"""
from __future__ import annotations

import html as _html
import json
import sqlite3

from flask import Blueprint

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
                + render_chat_section()
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

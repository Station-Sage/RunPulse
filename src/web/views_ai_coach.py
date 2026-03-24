"""Sprint 5 · V2-7-1 — AI Coaching UI Blueprint.

참고 디자인: design/app-UI/ai_coaching.html
"""
from __future__ import annotations
import json
import sqlite3
from flask import Blueprint
from src.web.helpers import (
    html_page, bottom_nav, no_data_card, fmt_pace, db_path,
)

ai_coach_bp = Blueprint("ai_coach", __name__)



def _safe_json(raw):
    if not raw:
        return {}
    try:
        return json.loads(raw) if isinstance(raw, str) else raw
    except (json.JSONDecodeError, TypeError):
        return {}


def _load_metric(conn, name):
    cur = conn.execute(
        "SELECT metric_value, metric_json FROM computed_metrics "
        "WHERE metric_name=? ORDER BY date DESC LIMIT 1", (name,))
    row = cur.fetchone()
    if not row:
        return None, {}
    return row[0], _safe_json(row[1])


def _generate_briefing(conn):
    """src/ai/briefing.py 연동 시도, 실패 시 메트릭 기반 간이 브리핑."""
    utrs_val, utrs_json = _load_metric(conn, "utrs")
    cirs_val, cirs_json = _load_metric(conn, "cirs")
    darp_val, darp_json = _load_metric(conn, "darp_half")
    di_val, _ = _load_metric(conn, "di")

    try:
        from src.ai.briefing import generate_daily_briefing
        ctx = {
            "utrs": utrs_val, "cirs": cirs_val,
            "darp": darp_val, "di": di_val,
        }
        result = generate_daily_briefing(ctx)
        if result:
            return result
    except (ImportError, Exception):
        pass

    parts = []
    if utrs_val is not None:
        grade = "고강도 훈련 최적" if utrs_val >= 85 else "정상 훈련 가능" if utrs_val >= 70 else "볼륨 감소 권장" if utrs_val >= 55 else "완전 휴식 권장"
        parts.append(f"오늘의 UTRS는 <strong>{int(utrs_val)}/100</strong>으로, {grade} 상태입니다.")
    if cirs_val is not None:
        risk = "안전" if cirs_val <= 25 else "주의" if cirs_val <= 50 else "경고" if cirs_val <= 75 else "위험"
        parts.append(f"CIRS 부상 위험도는 <strong>{int(cirs_val)}/100</strong>으로 {risk} 범위입니다.")
    if darp_val is not None:
        from src.web.helpers import fmt_duration
        parts.append(f"DARP 하프마라톤 예측: <strong>{fmt_duration(int(darp_val))}</strong>")
    if di_val is not None:
        parts.append(f"내구성 지수(DI): <strong>{int(di_val)}/100</strong>")
    if not parts:
        return None
    return "<p>" + "</p><p>".join(parts) + "</p>"


def _render_coach_profile():
    return (
        '<div style="background:linear-gradient(135deg,rgba(0,212,255,0.1),rgba(0,255,136,0.1));'
        'border-radius:20px;padding:24px;margin:20px 0;display:flex;align-items:center;gap:20px;'
        'border:1px solid rgba(0,212,255,0.3)">'
        '<div style="width:80px;height:80px;background:linear-gradient(135deg,#00d4ff,#00ff88);'
        'border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:40px">🤖</div>'
        '<div><h2 style="font-size:20px;margin-bottom:8px">RunPulse AI 코치</h2>'
        '<p style="font-size:14px;color:rgba(255,255,255,0.7)">개인 맞춤형 훈련 분석 및 조언</p>'
        '<div style="display:flex;align-items:center;gap:8px;margin-top:8px">'
        '<span style="width:8px;height:8px;background:#00ff88;border-radius:50%;'
        'animation:pulse 2s infinite;display:inline-block"></span>'
        '<span style="font-size:14px;color:#00ff88">온라인</span></div></div></div>'
    )


def _render_briefing_card(briefing_text):
    if not briefing_text:
        return no_data_card("오늘의 브리핑", "메트릭 데이터가 수집되면 브리핑이 생성됩니다")
    return (
        '<div style="margin:20px 0">'
        '<div style="font-size:18px;margin-bottom:16px;display:flex;align-items:center;gap:10px">'
        '<span style="width:4px;height:20px;background:linear-gradient(135deg,#00d4ff,#00ff88);'
        'border-radius:2px;display:inline-block"></span>오늘의 브리핑</div>'
        '<div style="background:rgba(255,255,255,0.05);border-radius:20px;padding:24px;'
        'border-left:4px solid #00d4ff">'
        '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">'
        '<span style="font-size:12px;color:rgba(255,255,255,0.6)">자동 생성 브리핑</span>'
        '<div style="display:flex;gap:8px">'
        '<button onclick="location.reload()" style="background:rgba(255,255,255,0.1);border:none;'
        'color:#fff;padding:8px 16px;border-radius:20px;cursor:pointer;font-size:12px">🔄 재생성</button>'
        '</div></div>'
        f'<div style="font-size:15px;line-height:1.6;color:rgba(255,255,255,0.9)">{briefing_text}</div>'
        '</div></div>'
    )


def _render_recommendation_chips(conn):
    utrs_val, _ = _load_metric(conn, "utrs")
    cirs_val, _ = _load_metric(conn, "cirs")
    di_val, _ = _load_metric(conn, "di")
    fearp_val, fearp_json = _load_metric(conn, "fearp")

    chips = []
    if utrs_val is not None:
        if utrs_val >= 70:
            chips.append(("💪", "회복", f"UTRS {int(utrs_val)} — 정상 훈련 가능"))
        else:
            chips.append(("💪", "회복", f"UTRS {int(utrs_val)} — 가벼운 조깅 권장"))
    if di_val is not None:
        chips.append(("⚡", "훈련", f"DI {int(di_val)} — 내구성 {'양호' if di_val >= 70 else '개선 필요'}"))
    if fearp_val is not None:
        chips.append(("🌡️", "FEARP", f"환경 보정 페이스: {fmt_pace(fearp_val)}/km"))
    if cirs_val is not None:
        if cirs_val > 40:
            chips.append(("⚠️", "부상", f"CIRS {int(cirs_val)} — 훈련량 감소 권장"))
        else:
            chips.append(("⚠️", "부상", f"CIRS {int(cirs_val)} — 안전 범위"))

    if not chips:
        return ""

    html = (
        '<div style="margin:20px 0">'
        '<div style="font-size:18px;margin-bottom:16px;display:flex;align-items:center;gap:10px">'
        '<span style="width:4px;height:20px;background:linear-gradient(135deg,#00d4ff,#00ff88);'
        'border-radius:2px;display:inline-block"></span>추천 칩</div>'
        '<div style="display:flex;flex-wrap:wrap;gap:12px">'
    )
    for icon, label, text in chips:
        html += (
            f'<div style="background:rgba(0,212,255,0.1);border:1px solid rgba(0,212,255,0.3);'
            f'border-radius:24px;padding:12px 20px;display:flex;align-items:center;gap:8px">'
            f'<span style="font-size:18px">{icon}</span>'
            f'<span style="font-size:14px">{text}</span></div>'
        )
    html += '</div></div>'
    return html


def _render_quick_questions():
    questions = [
        "오늘 훈련 강도는?",
        "내구성 지수가 떨어졌어요",
        "마라톤 준비도 확인",
        "FEARP 보정 방법",
    ]
    html = (
        '<div style="margin:20px 0">'
        '<div style="font-size:18px;margin-bottom:16px;display:flex;align-items:center;gap:10px">'
        '<span style="width:4px;height:20px;background:linear-gradient(135deg,#00d4ff,#00ff88);'
        'border-radius:2px;display:inline-block"></span>대화</div>'
        '<div style="background:rgba(255,255,255,0.05);border-radius:20px;padding:20px;min-height:200px">'
        '<div style="text-align:center;padding:40px;color:rgba(255,255,255,0.5)">'
        '<p style="font-size:16px;margin-bottom:8px">💬 대화형 AI 코칭</p>'
        '<p style="font-size:14px">v0.3에서 대화형 코칭이 추가됩니다</p></div></div>'
        '<div style="display:flex;gap:8px;margin-top:12px;overflow-x:auto;padding-bottom:8px">'
    )
    for q in questions:
        html += (
            f'<button style="background:rgba(255,255,255,0.1);border:none;color:rgba(255,255,255,0.8);'
            f'padding:8px 16px;border-radius:16px;font-size:13px;white-space:nowrap;cursor:pointer">'
            f'"{q}"</button>'
        )
    html += '</div></div>'
    return html


@ai_coach_bp.route("/ai-coach")
def ai_coach_page():
    dbp = db_path()
    if not dbp:
        body = no_data_card("AI 코치", "데이터베이스를 찾을 수 없습니다")
        return html_page("AI 코칭", body + bottom_nav("ai-coach"))

    conn = sqlite3.connect(dbp)
    try:
        briefing_text = _generate_briefing(conn)
        body = (
            '<div style="max-width:1200px;margin:0 auto;padding:20px;padding-bottom:100px">'
            '<div style="display:flex;align-items:center;padding:20px 0;'
            'border-bottom:1px solid rgba(255,255,255,0.1)">'
            '<span style="font-size:20px;font-weight:bold">AI 코칭</span></div>'
            + _render_coach_profile()
            + _render_briefing_card(briefing_text)
            + _render_recommendation_chips(conn)
            + _render_quick_questions()
            + '</div>'
        )
    finally:
        conn.close()

    return html_page("AI 코칭", body + bottom_nav("ai-coach"))

"""AI 코칭 페이지 렌더링 카드 — views_ai_coach.py에서 분리.

300줄 규칙 준수를 위해 렌더링 헬퍼를 별도 모듈로 분리.
"""
from __future__ import annotations

import html as _html
import sqlite3

from src.web.helpers import fmt_pace, fmt_duration, no_data_card


def render_coach_profile() -> str:
    """AI 코치 프로필 헤더."""
    return (
        '<style>@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.5}}</style>'
        '<div style="background:linear-gradient(135deg,rgba(0,212,255,0.1),rgba(0,255,136,0.1));'
        'border-radius:20px;padding:24px;margin-bottom:20px;display:flex;align-items:center;gap:20px;'
        'border:1px solid rgba(0,212,255,0.3)">'
        '<div style="width:80px;height:80px;background:linear-gradient(135deg,#00d4ff,#00ff88);'
        'border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:40px">'
        '🤖</div>'
        '<div><h2 style="font-size:20px;margin:0 0 8px">RunPulse AI 코치</h2>'
        '<p style="font-size:14px;color:rgba(255,255,255,0.7);margin:0 0 8px">'
        '개인 맞춤형 훈련 분석 및 조언</p>'
        '<div style="display:flex;align-items:center;gap:8px">'
        '<span style="width:8px;height:8px;background:#00ff88;border-radius:50%;'
        'animation:pulse 2s infinite;display:inline-block"></span>'
        '<span style="font-size:14px;color:#00ff88">온라인</span></div></div></div>'
    )


def render_briefing_card(briefing_text: str | None) -> str:
    """오늘의 브리핑 카드."""
    from datetime import datetime
    if not briefing_text:
        return no_data_card("오늘의 브리핑", "메트릭 데이터가 수집되면 브리핑이 생성됩니다")
    now_str = datetime.now().strftime("%Y년 %m월 %d일 %H:%M")
    return (
        '<div class="card" style="border-left:4px solid #00d4ff;margin-bottom:16px;">'
        '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;flex-wrap:wrap;gap:8px">'
        '<h3 style="margin:0;">오늘의 브리핑</h3>'
        '<div style="display:flex;align-items:center;gap:8px;">'
        f'<span style="font-size:0.75rem;color:var(--muted);">{now_str}</span>'
        '<button onclick="location.reload()" style="background:rgba(255,255,255,0.1);border:none;color:#fff;'
        'padding:6px 12px;border-radius:16px;cursor:pointer;font-size:0.75rem;">재생성</button>'
        '<button onclick="if(navigator.clipboard){navigator.clipboard.writeText(document.querySelector('
        "'.briefing-body').innerText).then(function(){alert('복사됨');});}\" "
        'style="background:rgba(255,255,255,0.1);border:none;color:#fff;'
        'padding:6px 12px;border-radius:16px;cursor:pointer;font-size:0.75rem;">공유</button>'
        '</div></div>'
        f'<div class="briefing-body" style="font-size:0.92rem;line-height:1.7;color:rgba(255,255,255,0.9)">'
        f'{briefing_text}</div></div>'
    )


def render_wellness_card(wellness: dict) -> str:
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


def render_chips(chips: list[dict]) -> str:
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


def render_chat_section() -> str:
    """채팅 인터페이스 (v0.3 대비 레이아웃 + 샘플 메시지)."""
    ai_avatar = (
        '<div style="width:40px;height:40px;background:linear-gradient(135deg,#00d4ff,#00ff88);'
        'border-radius:50%;display:flex;align-items:center;justify-content:center;flex-shrink:0;'
        'font-size:18px">🤖</div>'
    )
    return (
        '<div class="card" style="margin-bottom:16px;">'
        '<h3 style="margin:0 0 12px;">대화</h3>'
        '<div style="background:rgba(255,255,255,0.03);border-radius:16px;padding:20px;min-height:160px;">'
        f'<div style="display:flex;gap:12px;margin-bottom:16px">{ai_avatar}'
        '<div style="background:rgba(0,212,255,0.1);border:1px solid rgba(0,212,255,0.3);'
        'border-radius:16px;padding:12px 16px;max-width:75%">'
        '<p style="font-size:14px;line-height:1.5;margin:0">안녕하세요! RunPulse AI 코치입니다. '
        '오늘의 훈련 계획이나 메트릭에 대해 궁금한 점이 있으신가요?</p>'
        '<div style="font-size:11px;color:rgba(255,255,255,0.5);margin-top:4px">자동 생성</div>'
        '</div></div>'
        '</div>'
        '<div style="display:flex;gap:12px;align-items:center;margin-top:12px">'
        '<input type="text" placeholder="AI 코치에게 질문하세요..." disabled '
        'style="flex:1;background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.2);'
        'border-radius:24px;padding:12px 20px;color:#fff;font-size:14px;outline:none;opacity:0.5"/>'
        '<button disabled style="width:48px;height:48px;background:linear-gradient(135deg,#00d4ff,#00ff88);'
        'border:none;border-radius:50%;color:#fff;font-size:20px;cursor:not-allowed;opacity:0.5" '
        'title="v0.3에서 활성화">➤</button></div>'
        '<div style="display:flex;gap:8px;margin-top:12px;overflow-x:auto;padding-bottom:4px">'
        '<button disabled style="background:rgba(255,255,255,0.1);border:none;color:rgba(255,255,255,0.6);'
        'padding:8px 16px;border-radius:16px;font-size:13px;white-space:nowrap;cursor:not-allowed">'
        '"오늘 훈련 강도는?"</button>'
        '<button disabled style="background:rgba(255,255,255,0.1);border:none;color:rgba(255,255,255,0.6);'
        'padding:8px 16px;border-radius:16px;font-size:13px;white-space:nowrap;cursor:not-allowed">'
        '"마라톤 준비도 확인"</button>'
        '<button disabled style="background:rgba(255,255,255,0.1);border:none;color:rgba(255,255,255,0.6);'
        'padding:8px 16px;border-radius:16px;font-size:13px;white-space:nowrap;cursor:not-allowed">'
        '"FEARP 보정 방법"</button></div>'
        '<p class="muted" style="margin:8px 0 0;font-size:0.72rem;text-align:center;">'
        'v0.3에서 대화형 AI 코칭이 활성화됩니다</p></div>'
    )


def render_recent_training(activities: list[dict]) -> str:
    """최근 훈련 요약 카드."""
    if not activities:
        return ""
    items = ""
    for a in activities:
        km = f"{a['km']:.1f}km" if a.get("km") else "-"
        dur = fmt_duration(int(a["sec"])) if a.get("sec") else "-"
        pace = fmt_pace(a["pace"]) if a.get("pace") else "-"
        items += (
            f"<div style='display:flex;justify-content:space-between;padding:8px 0;"
            f"border-bottom:1px solid rgba(255,255,255,0.08);font-size:0.85rem;'>"
            f"<span style='color:var(--muted);'>{a['date']}</span>"
            f"<span>{km}</span><span>{dur}</span>"
            f"<span style='color:#00d4ff;'>{pace}/km</span></div>"
        )
    return (
        '<div class="card" style="margin-bottom:16px;">'
        '<h3 style="margin:0 0 12px;">최근 훈련</h3>' + items + '</div>'
    )


def render_risk_summary(conn: sqlite3.Connection) -> str:
    """리스크 요약 카드 — CIRS, ACWR, LSI."""
    cirs_row = conn.execute(
        "SELECT metric_value FROM computed_metrics WHERE metric_name='CIRS' ORDER BY date DESC LIMIT 1"
    ).fetchone()
    acwr_row = conn.execute(
        "SELECT metric_value FROM computed_metrics WHERE metric_name='ACWR' ORDER BY date DESC LIMIT 1"
    ).fetchone()
    lsi_row = conn.execute(
        "SELECT metric_value FROM computed_metrics WHERE metric_name='LSI' ORDER BY date DESC LIMIT 1"
    ).fetchone()

    items = []
    if cirs_row and cirs_row[0] is not None:
        v = int(cirs_row[0])
        color = "#00ff88" if v <= 25 else "#ffaa00" if v <= 50 else "#ff8844" if v <= 75 else "#ff4444"
        items.append(("부상 위험(CIRS)", f"{v}/100", color))
    if acwr_row and acwr_row[0] is not None:
        v = float(acwr_row[0])
        color = "#ffaa00" if v < 0.8 or v > 1.3 else "#00ff88"
        items.append(("ACWR", f"{v:.2f}", color))
    if lsi_row and lsi_row[0] is not None:
        v = float(lsi_row[0])
        color = "#ff4444" if v > 1.5 else "#ffaa00" if v > 1.0 else "#00ff88"
        items.append(("부하 스파이크(LSI)", f"{v:.1f}", color))

    if not items:
        return ""
    cells = "".join(
        f"<div style='text-align:center;min-width:80px;'>"
        f"<div style='font-size:0.72rem;color:var(--muted);margin-bottom:4px;'>{label}</div>"
        f"<div style='font-size:1.1rem;font-weight:bold;color:{color};'>{val}</div></div>"
        for label, val, color in items
    )
    return (
        '<div class="card" style="margin-bottom:16px;border-left:4px solid #ff4444;">'
        '<h3 style="margin:0 0 12px;">리스크 요약</h3>'
        f'<div style="display:flex;justify-content:space-around;flex-wrap:wrap;gap:8px;">'
        f'{cells}</div></div>'
    )

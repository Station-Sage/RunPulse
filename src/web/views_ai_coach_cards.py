"""AI 코칭 페이지 렌더링 카드 — views_ai_coach.py에서 분리.

300줄 규칙 준수를 위해 렌더링 헬퍼를 별도 모듈로 분리.
"""
from __future__ import annotations

import html as _html
import re
import sqlite3

from src.web.helpers import fmt_pace, fmt_duration, no_data_card


def _md_to_html(text: str) -> str:
    """간이 마크다운→HTML 변환 (볼드+헤딩+리스트+코드블록 제거+줄바꿈)."""
    # 코드블록(```...```) 제거 (JSON 노출 방지)
    text = re.sub(r"```[\s\S]*?```", "", text)
    # 헤딩 ### → bold
    text = re.sub(r"^#{1,4}\s*(.+)$", r"<strong>\1</strong>", text, flags=re.MULTILINE)
    # 볼드 **text**
    text = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", text)
    # 리스트 아이템 - text → 불릿
    text = re.sub(r"^[-*]\s+", "• ", text, flags=re.MULTILINE)
    # 번호 리스트 1. text
    text = re.sub(r"^(\d+)\.\s+", r"\1. ", text, flags=re.MULTILINE)
    text = text.replace("\n", "<br>")
    return text


def _parse_followup(text: str) -> tuple[str, list[str]]:
    """AI 응답에서 추천질문 추출. 여러 형식 지원."""
    # 형식 1: [추천: Q1 | Q2 | Q3]
    m = re.search(r"\[추천:\s*(.+?)\]\s*$", text, re.MULTILINE)
    if m:
        questions = [q.strip() for q in m.group(1).split("|") if q.strip()]
        return text[:m.start()].rstrip(), questions

    # 형식 2: ```json {"suggestions": [...]} ``` (Gemini가 자주 사용)
    m = re.search(r'```json\s*\{[^}]*"suggestions"\s*:\s*\[([^\]]+)\][^}]*\}\s*```', text, re.DOTALL)
    if m:
        try:
            items = re.findall(r'"([^"]+)"', m.group(1))
            if items:
                return text[:m.start()].rstrip(), items[:3]
        except Exception:
            pass

    # 형식 3: JSON 블록이 응답 끝에 있을 때 (코드블록 없이)
    m = re.search(r'\{\s*"suggestions"\s*:\s*\[([^\]]+)\]\s*\}\s*$', text, re.DOTALL)
    if m:
        try:
            items = re.findall(r'"([^"]+)"', m.group(1))
            if items:
                return text[:m.start()].rstrip(), items[:3]
        except Exception:
            pass

    return text, []


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
    """오늘의 브리핑 카드 — 재생성은 AJAX."""
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
        '<a href="/ai-coach?refresh=1" style="background:rgba(255,255,255,0.1);border:none;color:#fff;'
        'padding:6px 12px;border-radius:16px;font-size:0.75rem;text-decoration:none;">재생성</a>'
        '<button onclick="if(navigator.clipboard){navigator.clipboard.writeText(document.querySelector('
        "'.briefing-body').innerText).then(function(){alert('복사됨');});}\" "
        'style="background:rgba(255,255,255,0.1);border:none;color:#fff;'
        'padding:6px 12px;border-radius:16px;cursor:pointer;font-size:0.75rem;">공유</button>'
        '</div></div>'
        f'<div class="briefing-body" style="font-size:0.92rem;line-height:1.7;color:rgba(255,255,255,0.9)">'
        f'{briefing_text}</div></div>'
    )


def render_wellness_card(wellness: dict) -> str:
    """오늘 웰니스 요약 카드 — 수면시간, HRV 상태색 포함."""
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
        label = "수면"
        if "sleep_hours" in wellness:
            h = wellness["sleep_hours"]
            label = f"수면 ({h:.1f}h)"
        items.append(("😴", label, f"{int(ss)}점", color))
    if "hrv_value" in wellness:
        hrv = int(wellness["hrv_value"])
        color = "#00ff88" if hrv >= 50 else "#ffaa00" if hrv >= 30 else "#ff4444"
        items.append(("💓", "HRV", f"{hrv} ms", color))
    if "resting_hr" in wellness:
        rhr = int(wellness["resting_hr"])
        color = "#00ff88" if rhr <= 55 else "#ffaa00" if rhr <= 70 else "#ff4444"
        items.append(("❤️", "안정심박", f"{rhr} bpm", color))
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
    """추천 칩 목록 — 클릭 시 AI 채팅 트리거."""
    if not chips:
        return ""
    html_parts = []
    for chip in chips:
        label = _html.escape(chip.get("label", ""))
        chip_id = _html.escape(chip.get("id", ""))
        html_parts.append(
            f'<form method="POST" action="/ai-coach/chat#chatCard" style="margin:0;display:inline;">'
            f'<input type="hidden" name="chip_id" value="{chip_id}"/>'
            f'<button type="submit" style="background:rgba(0,212,255,0.1);border:1px solid rgba(0,212,255,0.3);'
            f'border-radius:24px;padding:10px 18px;color:rgba(255,255,255,0.9);'
            f'font-size:0.85rem;cursor:pointer;white-space:nowrap;">{label}</button></form>'
        )
    return (
        '<div class="card" style="margin-bottom:16px;">'
        '<h3 style="margin:0 0 12px;">추천</h3>'
        '<div style="display:flex;flex-wrap:wrap;gap:10px;">'
        + "".join(html_parts)
        + '</div></div>'
    )


def render_chat_section(chat_history: list[dict] | None = None,
                        chips: list[dict] | None = None) -> str:
    """채팅 인터페이스 — 히스토리 + 빠른 질문(칩 연동) + 외부 AI + 전체화면."""
    ai_avatar = (
        '<div style="width:36px;height:36px;background:linear-gradient(135deg,#00d4ff,#00ff88);'
        'border-radius:50%;display:flex;align-items:center;justify-content:center;flex-shrink:0;'
        'font-size:16px">🤖</div>'
    )
    user_avatar = (
        '<div style="width:36px;height:36px;background:rgba(255,255,255,0.2);'
        'border-radius:50%;display:flex;align-items:center;justify-content:center;flex-shrink:0;'
        'font-size:16px">🏃</div>'
    )

    # 채팅 히스토리 렌더링
    messages_html = ""
    followup_chips_html = ""  # 마지막 AI 응답의 추천 질문
    if chat_history:
        last_ai_idx = -1
        for i, msg in enumerate(chat_history):
            if msg.get("role") == "assistant":
                last_ai_idx = i

        for i, msg in enumerate(chat_history):
            role = msg.get("role", "user")
            raw_content = msg.get("content", "")
            time_str = msg.get("time", "")[:19] if msg.get("time") else ""
            # 서버 시간을 data 속성으로 저장, JS에서 로컬 변환
            time_html = (
                f'<span class="chat-time" data-utc="{_html.escape(time_str)}">{time_str[:16]}</span>'
                if time_str else ""
            )
            model = msg.get("ai_model", "")
            provider_badge = ""
            if role == "assistant" and model and model != "rule":
                provider_badge = (
                    f'<span style="font-size:9px;color:var(--cyan);margin-left:6px;">'
                    f'via {_html.escape(model)}</span>'
                )

            # 추천 질문 파싱 (마지막 AI 메시지만)
            followups: list[str] = []
            if role == "assistant" and i == last_ai_idx:
                display_text, followups = _parse_followup(raw_content)
                content = _md_to_html(_html.escape(display_text))
            else:
                content = _md_to_html(_html.escape(raw_content))

            if role == "assistant":
                messages_html += (
                    f'<div style="display:flex;gap:10px;margin-bottom:12px">{ai_avatar}'
                    '<div style="background:rgba(0,212,255,0.1);border:1px solid rgba(0,212,255,0.3);'
                    'border-radius:16px;padding:10px 14px;max-width:80%">'
                    f'<div style="font-size:13px;line-height:1.6;color:rgba(255,255,255,0.9)">{content}</div>'
                    f'<div style="font-size:10px;color:rgba(255,255,255,0.4);margin-top:4px">'
                    f'{time_html}{provider_badge}</div>'
                    '</div></div>'
                )
                # 추천 질문 플로팅 칩
                if followups:
                    fu_btns = "".join(
                        f'<form method="POST" action="/ai-coach/chat#chatCard" style="margin:0;display:inline;">'
                        f'<input type="hidden" name="message" value="{_html.escape(q)}"/>'
                        f'<button type="submit" style="background:rgba(0,212,255,0.08);'
                        f'border:1px solid rgba(0,212,255,0.25);border-radius:16px;padding:6px 14px;'
                        f'color:var(--cyan);font-size:0.78rem;cursor:pointer;white-space:nowrap;">'
                        f'{_html.escape(q)}</button></form>'
                        for q in followups[:3]
                    )
                    followup_chips_html = (
                        '<div style="display:flex;gap:6px;flex-wrap:wrap;margin:4px 0 8px 46px;">'
                        + fu_btns + '</div>'
                    )
            else:
                messages_html += (
                    f'<div style="display:flex;gap:10px;margin-bottom:12px;flex-direction:row-reverse">{user_avatar}'
                    '<div style="background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.2);'
                    'border-radius:16px;padding:10px 14px;max-width:80%">'
                    f'<div style="font-size:13px;line-height:1.6">{content}</div>'
                    f'<div style="font-size:10px;color:rgba(255,255,255,0.4);margin-top:4px;text-align:right">{time_html}</div>'
                    '</div></div>'
                )
        # 추천질문 칩은 메시지 영역 하단에 배치
        messages_html += followup_chips_html
    else:
        messages_html = (
            f'<div style="display:flex;gap:10px;margin-bottom:12px">{ai_avatar}'
            '<div style="background:rgba(0,212,255,0.1);border:1px solid rgba(0,212,255,0.3);'
            'border-radius:16px;padding:10px 14px;max-width:80%">'
            '<div style="font-size:13px;line-height:1.6;color:rgba(255,255,255,0.9)">'
            '안녕하세요! RunPulse AI 코치입니다. '
            '훈련이나 메트릭에 대해 궁금한 점을 질문해주세요.</div></div></div>'
        )

    # 빠른 질문 — 칩 시스템 연동 (없으면 기본 3개)
    quick_items = []
    if chips:
        for c in chips[:5]:
            label = _html.escape(c.get("label", ""))
            cid = _html.escape(c.get("id", ""))
            quick_items.append(
                f'<form method="POST" action="/ai-coach/chat#chatCard" style="margin:0;display:inline;">'
                f'<input type="hidden" name="chip_id" value="{cid}"/>'
                f'<button type="submit" style="background:rgba(255,255,255,0.1);border:none;'
                f'color:rgba(255,255,255,0.8);padding:8px 16px;border-radius:16px;font-size:12px;'
                f'white-space:nowrap;cursor:pointer;">{label}</button></form>'
            )
    if not quick_items:
        for q in ["오늘 훈련 강도는?", "회복 상태 분석", "이번 주 훈련 리뷰"]:
            quick_items.append(
                f'<form method="POST" action="/ai-coach/chat#chatCard" style="margin:0;display:inline;">'
                f'<input type="hidden" name="message" value="{q}"/>'
                f'<button type="submit" style="background:rgba(255,255,255,0.1);border:none;'
                f'color:rgba(255,255,255,0.8);padding:8px 16px;border-radius:16px;font-size:12px;'
                f'white-space:nowrap;cursor:pointer;">{q}</button></form>'
            )
    quick_btns = "".join(quick_items)

    return (
        '<div id="chatCard" class="card" style="margin-bottom:16px;transition:all 0.3s;">'
        '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">'
        '<h3 style="margin:0;">대화</h3>'
        '<button onclick="toggleChatFullscreen()" id="chatFsBtn" '
        'style="background:rgba(255,255,255,0.1);border:none;color:var(--muted);'
        'padding:4px 10px;border-radius:8px;font-size:0.75rem;cursor:pointer;">⛶ 전체화면</button></div>'
        f'<div id="chatBox" style="background:rgba(255,255,255,0.03);border-radius:16px;'
        f'padding:16px;min-height:160px;max-height:400px;overflow-y:auto;transition:max-height 0.3s;">'
        f'{messages_html}</div>'
        '<form id="chatForm" method="POST" action="/ai-coach/chat#chatCard" '
        'style="display:flex;gap:10px;align-items:center;margin-top:12px" '
        'onsubmit="return sendChat(event)">'
        '<input id="chatInput" type="text" name="message" placeholder="AI 코치에게 질문하세요..." maxlength="500" '
        'style="flex:1;background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.2);'
        'border-radius:24px;padding:12px 20px;color:#fff;font-size:14px;outline:none"/>'
        '<button id="chatSendBtn" type="submit" style="width:48px;height:48px;background:linear-gradient(135deg,#00d4ff,#00ff88);'
        'border:none;border-radius:50%;color:#000;font-size:20px;cursor:pointer;font-weight:bold">➤</button>'
        '</form>'
        f'<div style="display:flex;gap:8px;margin-top:10px;overflow-x:auto;padding-bottom:4px">'
        f'{quick_btns}</div>'
        # 외부 AI 연동 섹션
        '<details style="margin-top:12px;">'
        '<summary style="cursor:pointer;font-size:0.8rem;color:var(--muted);list-style:none;">'
        '🔗 외부 AI 연동 (프롬프트 복사 → 붙여넣기)</summary>'
        '<div style="margin-top:8px;padding:10px;background:rgba(255,255,255,0.03);border-radius:12px;">'
        '<p style="font-size:0.75rem;color:var(--muted);margin:0 0 8px;">'
        '① 프롬프트 복사 → ② 외부 AI에 붙여넣기 → ③ 응답을 아래에 저장</p>'
        '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:8px;">'
        '<button onclick="fetch(\'/ai-coach/prompt\').then(r=>r.json()).then(d=>'
        '{navigator.clipboard.writeText(d.prompt).then(()=>alert(\'프롬프트가 복사되었습니다.\'))})" '
        'style="background:rgba(0,212,255,0.15);color:var(--cyan);border:1px solid rgba(0,212,255,0.3);'
        'border-radius:12px;padding:6px 14px;font-size:0.78rem;cursor:pointer;">📋 프롬프트 복사</button>'
        '<a href="https://www.genspark.ai/agents?type=ai_chat" target="_blank" '
        'style="background:rgba(255,170,0,0.15);color:#ffaa00;border:1px solid rgba(255,170,0,0.3);'
        'border-radius:12px;padding:6px 14px;font-size:0.78rem;text-decoration:none;">Genspark</a>'
        '<a href="https://chatgpt.com" target="_blank" '
        'style="background:rgba(255,255,255,0.08);color:var(--muted);'
        'border-radius:12px;padding:6px 14px;font-size:0.78rem;text-decoration:none;">ChatGPT</a>'
        '<a href="https://claude.ai" target="_blank" '
        'style="background:rgba(255,255,255,0.08);color:var(--muted);'
        'border-radius:12px;padding:6px 14px;font-size:0.78rem;text-decoration:none;">Claude</a>'
        '</div>'
        '<form method="POST" action="/ai-coach/paste-response" style="display:flex;gap:8px;">'
        '<textarea name="ai_response" placeholder="AI 응답을 여기에 붙여넣으세요..." rows="3" '
        'style="flex:1;background:rgba(255,255,255,0.08);border:1px solid rgba(255,255,255,0.15);'
        'border-radius:12px;padding:10px;color:#fff;font-size:13px;resize:vertical;"></textarea>'
        '<button type="submit" style="align-self:flex-end;background:var(--cyan);color:#000;'
        'border:none;padding:8px 14px;border-radius:12px;font-size:13px;cursor:pointer;font-weight:600;">저장</button>'
        '</form>'
        '</div></details>'
        # 고급 도구 섹션
        '<details style="margin-top:8px;">'
        '<summary style="cursor:pointer;font-size:0.8rem;color:var(--muted);list-style:none;">'
        '🖥️ 고급 연동 (ngrok / MCP)</summary>'
        '<div style="margin-top:8px;padding:10px;background:rgba(255,255,255,0.03);border-radius:12px;'
        'font-size:0.78rem;">'
        '<div style="margin-bottom:12px;">'
        '<div style="font-weight:600;color:var(--cyan);margin-bottom:4px;">ngrok 터널링</div>'
        '<p style="color:var(--muted);margin:0 0 6px;">'
        'RunPulse를 외부에서 접근 가능하게 (Genspark Custom Agent 등):</p>'
        '<div style="position:relative;">'
        '<pre id="ngrokCmd" style="background:rgba(0,0,0,0.3);padding:8px 12px;border-radius:8px;'
        'font-size:0.75rem;overflow-x:auto;margin:0;color:#00ff88;white-space:pre-wrap;">'
        '# Termux에서\n'
        'pkg install ngrok\n'
        'ngrok http 18080\n'
        '# → https://xxxx.ngrok.io (외부 접근 URL)</pre>'
        '<button onclick="navigator.clipboard.writeText(document.getElementById(\'ngrokCmd\').innerText)'
        '.then(()=>this.textContent=\'✓\')" style="position:absolute;top:4px;right:4px;'
        'background:rgba(255,255,255,0.1);border:none;color:var(--muted);padding:2px 8px;'
        'border-radius:4px;font-size:0.7rem;cursor:pointer;">복사</button></div>'
        '<p style="color:var(--muted);margin:4px 0 0;font-size:0.72rem;">'
        'Genspark Custom Agent에 API URL로 등록하면 AI가 직접 데이터 조회 가능</p></div>'
        '<div>'
        '<div style="font-weight:600;color:var(--cyan);margin-bottom:4px;">MCP 서버 (Claude Desktop/CLI)</div>'
        '<p style="color:var(--muted);margin:0 0 6px;">PC에서 Claude Desktop 사용 시:</p>'
        '<div style="position:relative;">'
        '<pre id="mcpCmd" style="background:rgba(0,0,0,0.3);padding:8px 12px;border-radius:8px;'
        'font-size:0.75rem;overflow-x:auto;margin:0;color:#00ff88;white-space:pre-wrap;">'
        'python src/mcp_server.py\n'
        '# claude_desktop_config.json에 등록</pre>'
        '<button onclick="navigator.clipboard.writeText(document.getElementById(\'mcpCmd\').innerText)'
        '.then(()=>this.textContent=\'✓\')" style="position:absolute;top:4px;right:4px;'
        'background:rgba(255,255,255,0.1);border:none;color:var(--muted);padding:2px 8px;'
        'border-radius:4px;font-size:0.7rem;cursor:pointer;">복사</button></div>'
        '<p style="color:var(--muted);margin:4px 0 0;font-size:0.72rem;">'
        'Claude Desktop에서 러닝 데이터 직접 조회 가능 (10개 도구)</p>'
        '</div></div></details>'
        # AJAX 채팅 + 전체화면 토글 + 스크롤
        '<script>'
        'var cb=document.getElementById("chatBox");if(cb)cb.scrollTop=cb.scrollHeight;'
        # 서버 시간 → 클라이언트 로컬 시간 변환
        'document.querySelectorAll(".chat-time").forEach(function(el){'
        '  var utc=el.dataset.utc;if(!utc)return;'
        '  try{var d=new Date(utc);'
        '  el.textContent=d.toLocaleString("ko-KR",{month:"2-digit",day:"2-digit",hour:"2-digit",minute:"2-digit"});'
        '  }catch(e){}'
        '});'
        # AJAX 채팅 전송
        'function sendChat(e){'
        '  e.preventDefault();'
        '  var inp=document.getElementById("chatInput");'
        '  var msg=inp.value.trim();'
        '  if(!msg)return false;'
        '  var box=document.getElementById("chatBox");'
        '  var btn=document.getElementById("chatSendBtn");'
        # 사용자 메시지 즉시 표시
        '  box.innerHTML+='
        '    \'<div style="display:flex;gap:10px;margin-bottom:12px;flex-direction:row-reverse">'
        '    <div style="width:36px;height:36px;background:rgba(255,255,255,0.2);border-radius:50%;'
        '    display:flex;align-items:center;justify-content:center;flex-shrink:0;font-size:16px">🏃</div>'
        '    <div style="background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.2);'
        '    border-radius:16px;padding:10px 14px;max-width:80%">'
        '    <div style="font-size:13px;line-height:1.6">\'+msg.replace(/</g,"&lt;")+\'</div>'
        '    </div></div>\';'
        # 로딩 표시
        '  box.innerHTML+='
        '    \'<div id="aiLoading" style="display:flex;gap:10px;margin-bottom:12px">'
        '    <div style="width:36px;height:36px;background:linear-gradient(135deg,#00d4ff,#00ff88);'
        '    border-radius:50%;display:flex;align-items:center;justify-content:center;flex-shrink:0;font-size:16px">🤖</div>'
        '    <div style="background:rgba(0,212,255,0.1);border:1px solid rgba(0,212,255,0.3);'
        '    border-radius:16px;padding:10px 14px">'
        '    <div style="font-size:13px;color:var(--cyan);">생성 중'
        '    <span class="dots" style="animation:dotPulse 1.5s infinite">...</span></div>'
        '    </div></div>\';'
        '  box.scrollTop=box.scrollHeight;'
        '  inp.value="";btn.disabled=true;'
        # fetch로 전송
        '  var fd=new FormData();fd.append("message",msg);'
        '  fetch("/ai-coach/chat-async",{method:"POST",body:fd})'
        '  .then(function(r){return r.json();})'
        '  .then(function(d){'
        '    var el=document.getElementById("aiLoading");if(el)el.remove();'
        '    box.innerHTML+='
        '      \'<div style="display:flex;gap:10px;margin-bottom:12px">'
        '      <div style="width:36px;height:36px;background:linear-gradient(135deg,#00d4ff,#00ff88);'
        '      border-radius:50%;display:flex;align-items:center;justify-content:center;flex-shrink:0;font-size:16px">🤖</div>'
        '      <div style="background:rgba(0,212,255,0.1);border:1px solid rgba(0,212,255,0.3);'
        '      border-radius:16px;padding:10px 14px;max-width:80%">'
        '      <div style="font-size:13px;line-height:1.6;color:rgba(255,255,255,0.9)">\'+d.response+\'</div>'
        '      <div style="font-size:10px;color:rgba(255,255,255,0.4);margin-top:4px">\''
        '        +new Date().toLocaleString("ko-KR",{month:"2-digit",day:"2-digit",hour:"2-digit",minute:"2-digit"})'
        '        +\' <span style="color:var(--cyan);">\'+d.provider+\'</span></div>'
        '      </div></div>\';'
        '    box.scrollTop=box.scrollHeight;btn.disabled=false;'
        '  }).catch(function(){'
        '    var el=document.getElementById("aiLoading");if(el)el.remove();'
        '    box.innerHTML+=\'<div style="color:var(--red);font-size:12px;margin:8px 0;">응답 생성 실패. 다시 시도해주세요.</div>\';'
        '    btn.disabled=false;'
        '  });'
        '  return false;'
        '}'
        # 전체화면 토글
        'function toggleChatFullscreen(){'
        '  var card=document.getElementById("chatCard");'
        '  var box=document.getElementById("chatBox");'
        '  var btn=document.getElementById("chatFsBtn");'
        '  if(card.dataset.fs==="1"){'
        '    card.style.cssText="margin-bottom:16px;transition:all 0.3s;";'
        '    box.style.maxHeight="400px";'
        '    btn.textContent="⛶ 전체화면";'
        '    card.dataset.fs="0";'
        '    document.body.style.overflow="";'
        '  }else{'
        '    card.style.cssText="position:fixed;top:0;left:0;right:0;bottom:0;z-index:9999;'
        '      margin:0;border-radius:0;overflow-y:auto;background:var(--bg);transition:all 0.3s;'
        '      padding:16px;display:flex;flex-direction:column;";'
        '    box.style.maxHeight="none";box.style.flex="1";'
        '    btn.textContent="✕ 원래대로";'
        '    card.dataset.fs="1";'
        '    document.body.style.overflow="hidden";'
        '    box.scrollTop=box.scrollHeight;'
        '  }'
        '}'
        '</script>'
        '<style>@keyframes dotPulse{0%,100%{opacity:1}50%{opacity:0.3}}</style>'
        '</div>'
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

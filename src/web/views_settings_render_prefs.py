"""설정 페이지 렌더 헬퍼 — 훈련 환경설정 + AI + 프롬프트 관리.

views_settings.py에서 분리 (2026-03-29).
"""
from __future__ import annotations

import html as _html


def _render_training_prefs_section() -> str:
    """훈련 환경 설정 섹션 (휴식 요일, 일회성 차단 날짜, 인터벌 설정)."""
    import json
    import sqlite3
    from src.db_setup import get_db_path

    prefs = {"rest_weekdays_mask": 0, "blocked_dates": "[]",
             "interval_rep_m": 1000, "max_q_days": 0}
    try:
        dbp = get_db_path()
        if dbp and dbp.exists():
            conn = sqlite3.connect(str(dbp))
            row = conn.execute(
                "SELECT rest_weekdays_mask, blocked_dates, interval_rep_m, max_q_days "
                "FROM user_training_prefs LIMIT 1"
            ).fetchone()
            conn.close()
            if row:
                prefs = {"rest_weekdays_mask": row[0] or 0,
                         "blocked_dates": row[1] or "[]",
                         "interval_rep_m": row[2] or 1000,
                         "max_q_days": row[3] or 0}
    except Exception:
        pass

    mask = int(prefs["rest_weekdays_mask"])
    try:
        blocked_list = json.loads(prefs["blocked_dates"]) if prefs["blocked_dates"] else []
    except Exception:
        blocked_list = []
    blocked_str = ", ".join(blocked_list)
    rep_m = int(prefs["interval_rep_m"])
    max_q = int(prefs["max_q_days"])

    days = ["월", "화", "수", "목", "금", "토", "일"]
    day_checks = ""
    for i, dname in enumerate(days):
        bit = 1 << i
        checked = "checked" if (mask & bit) else ""
        day_checks += (
            f"<label style='display:flex;align-items:center;gap:4px;cursor:pointer;'>"
            f"<input type='checkbox' name='rest_day_{i}' value='{bit}' {checked} "
            f"style='width:16px;height:16px;'> {dname}</label>"
        )

    std_distances = [200, 300, 400, 600, 800, 1000, 1200, 1600, 2000]
    std_opts = "".join(
        f"<option value='{d}' {'selected' if d == rep_m else ''}>{d}m</option>"
        for d in std_distances
    )
    is_custom = rep_m not in std_distances
    custom_selected = "selected" if is_custom else ""

    return f"""
<div class='card' id='training-prefs-section'>
  <h2 style='margin:0 0 0.8rem;font-size:0.95rem;'>훈련 환경 설정</h2>
  <p class='muted' style='font-size:0.82rem;margin:0 0 1rem;'>
    훈련 계획 자동 생성 시 반영됩니다. 휴식일로 지정된 날은 계획에서 제외됩니다.
  </p>
  <form method='post' action='/settings/training-prefs'>

    <div style='margin-bottom:1.2rem;'>
      <label style='font-size:0.88rem;font-weight:600;display:block;margin-bottom:0.5rem;'>
        정기 휴식 요일 (매주 반복)
      </label>
      <div style='display:flex;gap:12px;flex-wrap:wrap;'>
        {day_checks}
      </div>
    </div>

    <div style='margin-bottom:1.2rem;'>
      <label style='font-size:0.88rem;font-weight:600;display:block;margin-bottom:0.4rem;'>
        일회성 차단 날짜 (쉼표 구분, YYYY-MM-DD)
      </label>
      <input type='text' name='blocked_dates' value='{_html.escape(blocked_str)}'
        placeholder='예: 2026-04-05, 2026-05-01'
        style='width:100%;padding:0.4rem;background:var(--card);border:1px solid var(--card-border);
               color:var(--text);border-radius:4px;font-size:0.88rem;box-sizing:border-box;'>
    </div>

    <div style='display:flex;gap:1.5rem;flex-wrap:wrap;margin-bottom:1.2rem;'>
      <div>
        <label style='font-size:0.88rem;font-weight:600;display:block;margin-bottom:0.4rem;'>
          인터벌 기본 반복 거리
          <span class='muted' style='font-weight:normal;font-size:0.78rem;'>
            (Buchheit &amp; Laursen 2013 — 200~2000m, 비표준 입력 가능)
          </span>
        </label>
        <div style='display:flex;gap:8px;align-items:center;'>
          <select id='rep-select' name='interval_rep_m_select'
            onchange='syncRepM(this.value)'
            style='padding:0.35rem;background:var(--card);border:1px solid var(--card-border);
                   color:var(--text);border-radius:4px;'>
            {std_opts}
            <option value='custom' {custom_selected}>직접 입력</option>
          </select>
          <input type='number' id='rep-custom' name='interval_rep_m'
            value='{rep_m}' min='100' max='5000' step='10'
            style='width:90px;padding:0.35rem;background:var(--card);
                   border:1px solid var(--card-border);color:var(--text);
                   border-radius:4px;{"display:none;" if not is_custom else ""}'
            placeholder='예: 320'>
          <span class='muted' style='font-size:0.82rem;'>m</span>
        </div>
      </div>

      <div>
        <label style='font-size:0.88rem;font-weight:600;display:block;margin-bottom:0.4rem;'>
          주간 최대 Q-day 수
          <span class='muted' style='font-weight:normal;font-size:0.78rem;'>(0=자동)</span>
        </label>
        <input type='number' name='max_q_days' value='{max_q}' min='0' max='4'
          style='width:70px;padding:0.35rem;background:var(--card);
                 border:1px solid var(--card-border);color:var(--text);border-radius:4px;'>
      </div>
    </div>

    <button type='submit'
      style='background:var(--cyan);color:#000;border:none;padding:0.4rem 1.4rem;
             border-radius:6px;font-weight:600;cursor:pointer;font-size:0.88rem;'>
      저장
    </button>
  </form>
  <script>
  function syncRepM(val) {{
    const custom = document.getElementById('rep-custom');
    if (val === 'custom') {{
      custom.style.display = '';
      custom.focus();
    }} else {{
      custom.style.display = 'none';
      custom.value = val;
    }}
  }}
  document.addEventListener('DOMContentLoaded', function() {{
    const sel = document.getElementById('rep-select');
    const cust = document.getElementById('rep-custom');
    if (sel && cust && sel.value !== 'custom') {{
      cust.value = sel.value;
    }}
  }});
  </script>
</div>"""


def _render_ai_section(config: dict) -> str:
    """AI 코치 설정 섹션."""
    ai_cfg = config.get("ai", {})
    provider = ai_cfg.get("provider", "rule")
    gemini_key = ai_cfg.get("gemini_api_key", "")
    groq_key = ai_cfg.get("groq_api_key", "")
    claude_key = ai_cfg.get("claude_api_key", "")
    openai_key = ai_cfg.get("openai_api_key", "")
    gemini_masked = "****" + gemini_key[-6:] if len(gemini_key) > 10 else ("설정됨" if gemini_key else "미설정")
    groq_masked = "****" + groq_key[-6:] if len(groq_key) > 10 else ("설정됨" if groq_key else "미설정")
    claude_masked = "****" + claude_key[-6:] if len(claude_key) > 10 else ("설정됨" if claude_key else "미설정")
    openai_masked = "****" + openai_key[-6:] if len(openai_key) > 10 else ("설정됨" if openai_key else "미설정")

    provider_options = ""
    for val, label in [("rule", "규칙 기반 (API 불필요)"), ("gemini", "Google Gemini (무료)"), ("groq", "Groq (무료, Llama 3.3)"), ("genspark", "Genspark (수동 복사/붙여넣기)"), ("claude", "Claude (Anthropic)"), ("openai", "ChatGPT (OpenAI)")]:
        sel = " selected" if val == provider else ""
        provider_options += f"<option value='{val}'{sel} style='background:#1a2035;color:#e0e6f0;'>{label}</option>"

    return f"""
<div class='card'>
  <h2 style='margin-bottom:0.5rem;'>AI 코치 설정</h2>
  <p class='muted' style='font-size:0.82rem;margin-bottom:0.6rem;'>
    AI 코치, 브리핑, 훈련 추천, 메트릭 해석에 사용할 AI를 선택합니다.
  </p>
  <div style='font-size:0.75rem;color:var(--muted);margin-bottom:0.6rem;line-height:1.6;'>
    💡 <strong>Gemini</strong> (무료, 일 1,500회) · <strong>Groq</strong> (무료, 일 14,400회) 추천<br>
    Claude/ChatGPT는 유료. 규칙 기반은 API 없이 동작.
  </div>
  <form method='post' action='/settings/ai' style='display:flex;flex-direction:column;gap:0.6rem;'>
    <label style='font-size:0.88rem;'>
      AI 제공자
      <select name='ai_provider' style='display:block;margin-top:0.2rem;padding:0.4rem;border-radius:4px;
        border:1px solid rgba(255,255,255,0.2);background:rgba(255,255,255,0.07);color:inherit;width:100%;'>
        {provider_options}
      </select>
    </label>
    <label style='font-size:0.88rem;'>
      Gemini API 키 <span class='muted' style='font-size:0.78rem;'>({gemini_masked})</span>
      <input type='password' name='gemini_api_key' placeholder='AIza...'
        style='display:block;margin-top:0.2rem;padding:0.4rem;border-radius:4px;
        border:1px solid rgba(255,255,255,0.2);background:rgba(255,255,255,0.07);color:inherit;width:100%;'>
    </label>
    <label style='font-size:0.88rem;'>
      Groq API 키 <span class='muted' style='font-size:0.78rem;'>({groq_masked})</span>
      <input type='password' name='groq_api_key' placeholder='gsk_...'
        style='display:block;margin-top:0.2rem;padding:0.4rem;border-radius:4px;
        border:1px solid rgba(255,255,255,0.2);background:rgba(255,255,255,0.07);color:inherit;width:100%;'>
    </label>
    <label style='font-size:0.88rem;'>
      Claude API 키 <span class='muted' style='font-size:0.78rem;'>({claude_masked})</span>
      <input type='password' name='claude_api_key' placeholder='sk-ant-...'
        style='display:block;margin-top:0.2rem;padding:0.4rem;border-radius:4px;
        border:1px solid rgba(255,255,255,0.2);background:rgba(255,255,255,0.07);color:inherit;width:100%;'>
    </label>
    <label style='font-size:0.88rem;'>
      OpenAI API 키 <span class='muted' style='font-size:0.78rem;'>({openai_masked})</span>
      <input type='password' name='openai_api_key' placeholder='sk-...'
        style='display:block;margin-top:0.2rem;padding:0.4rem;border-radius:4px;
        border:1px solid rgba(255,255,255,0.2);background:rgba(255,255,255,0.07);color:inherit;width:100%;'>
    </label>
    <button type='submit'
      style='align-self:flex-start;padding:0.45rem 1.2rem;background:var(--cyan);color:#000;
      border:none;border-radius:4px;cursor:pointer;font-weight:bold;'>저장</button>
  </form>
</div>"""


def _render_prompt_management(config: dict) -> str:
    """AI 프롬프트 관리 섹션."""
    from src.ai.prompt_config import get_all_prompts
    prompts = get_all_prompts(config)
    rows = ""
    for key, info in prompts.items():
        is_custom = info.get("is_custom")
        badge = " <span style='color:var(--cyan);font-size:0.7rem;'>수정됨</span>" if is_custom else ""
        rows += (
            f"<div style='border-bottom:1px solid rgba(255,255,255,0.06);padding:8px 0;'>"
            f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
            f"<strong style='font-size:0.82rem;'>{info['description']}{badge}</strong>"
            f"<span class='muted' style='font-size:0.7rem;'>max {info['max_tokens']} tokens</span></div>"
            f"<textarea name='prompt_{key}' rows='2' "
            f"onfocus='this.rows=10;this.style.borderColor=\"var(--cyan)\"' "
            f"onblur='this.rows=2;this.style.borderColor=\"rgba(255,255,255,0.1)\"' "
            f"style='width:100%;margin-top:4px;background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);"
            f"border-radius:8px;padding:6px 8px;color:var(--fg);font-size:0.75rem;resize:vertical;"
            f"transition:all 0.2s;'>"
            f"{info['template']}</textarea></div>"
        )
    return f"""
<details style='margin-bottom:16px;'>
<summary style='cursor:pointer;background:rgba(255,255,255,0.05);border-radius:12px;
padding:12px 16px;font-size:14px;font-weight:600;list-style:none;'>
🔧 AI 프롬프트 관리</summary>
<div class='card' style='margin-top:8px;'>
  <p class='muted' style='font-size:0.78rem;margin-bottom:0.5rem;'>
    각 카드에서 AI에게 보내는 프롬프트를 수정할 수 있습니다.
    {{context}}는 자동으로 현재 데이터로 치환됩니다.
  </p>
  <form method='post' action='/settings/prompts'>
    {rows}
    <div style='display:flex;gap:0.5rem;margin-top:0.5rem;'>
      <button type='submit'
        style='padding:0.4rem 1rem;background:var(--cyan);color:#000;border:none;border-radius:4px;cursor:pointer;font-weight:bold;'>
        저장</button>
      <button type='button' onclick="if(confirm('모든 프롬프트를 기본값으로 복원합니까?'))location.href='/settings/prompts-reset'"
        style='padding:0.4rem 1rem;background:rgba(255,255,255,0.1);color:var(--fg);border:1px solid rgba(255,255,255,0.2);border-radius:4px;cursor:pointer;'>
        기본값 복원</button>
    </div>
  </form>
</div></details>"""

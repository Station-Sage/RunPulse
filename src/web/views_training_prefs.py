"""훈련 환경 설정 카드 렌더러 — 훈련탭 내 Collapsible 섹션.

Settings 탭에서 이전 (SCHEMA_VERSION 3.1).
form action: POST /training/prefs
"""
from __future__ import annotations

import html as _html
import json
import sqlite3


_DAYS = ["월", "화", "수", "목", "금", "토", "일"]
_STD_DISTANCES = [200, 300, 400, 600, 800, 1000, 1200, 1600, 2000]


def _load_prefs(conn: sqlite3.Connection) -> dict:
    """user_training_prefs 로드. 없으면 기본값."""
    try:
        row = conn.execute(
            """SELECT rest_weekdays_mask, blocked_dates, interval_rep_m,
                      max_q_days, long_run_weekday_mask
               FROM user_training_prefs LIMIT 1"""
        ).fetchone()
    except sqlite3.OperationalError:
        row = None

    if row:
        return {
            "rest_weekdays_mask":    int(row[0] or 0),
            "blocked_dates":         row[1] or "[]",
            "interval_rep_m":        int(row[2] or 1000),
            "max_q_days":            int(row[3] or 0),
            "long_run_weekday_mask": int(row[4] or 0) if len(row) > 4 else 0,
        }
    return {
        "rest_weekdays_mask": 0, "blocked_dates": "[]",
        "interval_rep_m": 1000, "max_q_days": 0, "long_run_weekday_mask": 0,
    }


def _day_checkboxes(mask: int, name_prefix: str, label_suffix: str = "") -> str:
    """요일 체크박스 HTML 생성."""
    html = ""
    for i, dname in enumerate(_DAYS):
        bit = 1 << i
        checked = "checked" if (mask & bit) else ""
        html += (
            f"<label style='display:flex;align-items:center;gap:4px;"
            f"cursor:pointer;user-select:none;'>"
            f"<input type='checkbox' name='{name_prefix}{i}' value='{bit}' {checked} "
            f"style='width:16px;height:16px;accent-color:var(--cyan);'>"
            f" {dname}{label_suffix}</label>"
        )
    return html


def render_training_prefs_collapsed(conn: sqlite3.Connection) -> str:
    """훈련 환경 설정 — Collapsible 카드 (훈련탭 하단).

    Args:
        conn: SQLite 연결.

    Returns:
        HTML 문자열.
    """
    prefs = _load_prefs(conn)
    rest_mask = prefs["rest_weekdays_mask"]
    long_mask = prefs["long_run_weekday_mask"]
    rep_m     = prefs["interval_rep_m"]
    max_q     = prefs["max_q_days"]

    try:
        blocked_list: list[str] = json.loads(prefs["blocked_dates"])
    except Exception:
        blocked_list = []
    blocked_str = ", ".join(blocked_list)

    # 요일 체크박스
    rest_day_checks = _day_checkboxes(rest_mask, "rest_day_")
    long_day_checks = _day_checkboxes(long_mask, "long_day_")

    # 인터벌 거리 select
    std_opts = "".join(
        f"<option value='{d}' {'selected' if d == rep_m else ''}>{d}m</option>"
        for d in _STD_DISTANCES
    )
    is_custom = rep_m not in _STD_DISTANCES
    std_opts += f"<option value='custom' {'selected' if is_custom else ''}>직접 입력</option>"

    # 활성 설정 요약 (summary 줄에 표시)
    rest_days_ko = [_DAYS[i] for i in range(7) if rest_mask & (1 << i)]
    rest_summary = ", ".join(rest_days_ko) if rest_days_ko else "없음"
    long_days_ko = [_DAYS[i] for i in range(7) if long_mask & (1 << i)]
    long_summary = ", ".join(long_days_ko) if long_days_ko else "자동"

    return f"""
<details id='training-prefs-details' style='margin-top:8px;'>
  <summary style='cursor:pointer;list-style:none;padding:12px 16px;
    background:var(--card);border:1px solid var(--card-border);border-radius:12px;
    display:flex;justify-content:space-between;align-items:center;user-select:none;'>
    <span style='font-weight:600;font-size:0.9rem;'>⚙️ 훈련 환경 설정</span>
    <span class='muted' style='font-size:0.78rem;'>
      휴식일: {_html.escape(rest_summary)} · 롱런: {_html.escape(long_summary)} · 인터벌: {rep_m}m
    </span>
  </summary>

  <div class='card' style='border-radius:0 0 12px 12px;border-top:none;margin-top:0;'>
    <p class='muted' style='font-size:0.82rem;margin:0 0 1rem;'>
      훈련 계획 자동 생성 시 반영됩니다.
    </p>
    <form method='post' action='/training/prefs' id='training-prefs-form'>

      <div style='margin-bottom:1.2rem;'>
        <label style='font-size:0.88rem;font-weight:600;display:block;margin-bottom:0.5rem;'>
          정기 휴식 요일 (매주 반복)
        </label>
        <div style='display:flex;gap:12px;flex-wrap:wrap;'>
          {rest_day_checks}
        </div>
      </div>

      <div style='margin-bottom:1.2rem;'>
        <label style='font-size:0.88rem;font-weight:600;display:block;margin-bottom:0.5rem;'>
          롱런 요일 <span class='muted' style='font-weight:normal;font-size:0.78rem;'>(0=플래너 자동 선택)</span>
        </label>
        <div style='display:flex;gap:12px;flex-wrap:wrap;'>
          {long_day_checks}
        </div>
      </div>

      <div style='margin-bottom:1.2rem;'>
        <label style='font-size:0.88rem;font-weight:600;display:block;margin-bottom:0.4rem;'>
          일회성 쉬는 날 <span class='muted' style='font-weight:normal;font-size:0.78rem;'>(쉼표 구분, YYYY-MM-DD)</span>
        </label>
        <input type='text' name='blocked_dates' value='{_html.escape(blocked_str)}'
          placeholder='예: 2026-04-05, 2026-05-01'
          style='width:100%;padding:0.4rem;background:var(--input-bg,#1a2035);
                 border:1px solid var(--card-border);color:var(--text);
                 border-radius:4px;font-size:0.88rem;box-sizing:border-box;'>
      </div>

      <div style='display:flex;gap:1.5rem;flex-wrap:wrap;margin-bottom:1.2rem;'>
        <div>
          <label style='font-size:0.88rem;font-weight:600;display:block;margin-bottom:0.4rem;'>
            인터벌 기본 반복 거리
            <span class='muted' style='font-weight:normal;font-size:0.78rem;'>
              (Buchheit &amp; Laursen 2013 기준)
            </span>
          </label>
          <div style='display:flex;gap:8px;align-items:center;'>
            <select id='prefs-rep-select' name='interval_rep_m_select'
              onchange='trainingPrefsRepSync(this.value)'
              style='padding:0.35rem;background:var(--input-bg,#1a2035);
                     border:1px solid var(--card-border);color:var(--text);border-radius:4px;'>
              {std_opts}
            </select>
            <input type='number' id='prefs-rep-custom' name='interval_rep_m'
              value='{rep_m}' min='100' max='5000' step='10'
              style='width:90px;padding:0.35rem;background:var(--input-bg,#1a2035);
                     border:1px solid var(--card-border);color:var(--text);border-radius:4px;
                     {"" if is_custom else "display:none;"}'
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
            style='width:70px;padding:0.35rem;background:var(--input-bg,#1a2035);
                   border:1px solid var(--card-border);color:var(--text);border-radius:4px;'>
        </div>
      </div>

      <button type='submit'
        style='background:var(--cyan);color:#000;border:none;padding:0.4rem 1.4rem;
               border-radius:6px;font-weight:600;cursor:pointer;font-size:0.88rem;'>
        저장
      </button>
    </form>
  </div>
</details>

<script>
function trainingPrefsRepSync(val) {{
  const custom = document.getElementById('prefs-rep-custom');
  if (val === 'custom') {{
    custom.style.display = '';
    custom.focus();
  }} else {{
    custom.style.display = 'none';
    custom.value = val;
  }}
}}
document.addEventListener('DOMContentLoaded', function() {{
  const sel = document.getElementById('prefs-rep-select');
  const cust = document.getElementById('prefs-rep-custom');
  if (sel && cust && sel.value !== 'custom') {{
    cust.value = sel.value;
  }}
}});
</script>
"""

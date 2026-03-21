"""동기화 카드 UI 컴포넌트 — 기본(마지막 동기화 이후) / 기간 2탭."""
from __future__ import annotations

import html as _html

_SOURCE_OPTS = """
      <option value="all">전체 (연동된 서비스)</option>
      <option value="garmin">Garmin</option>
      <option value="strava">Strava</option>
      <option value="intervals">Intervals.icu</option>
      <option value="runalyze">Runalyze</option>
"""

_SELECT_STYLE = (
    "padding:0.35rem 0.6rem; border-radius:4px; border:1px solid #ccc;"
    " background:var(--card-bg); color:var(--fg);"
)
_BTN_STYLE = (
    "padding:0.35rem 1rem; background:#0066cc; color:#fff;"
    " border:none; border-radius:4px; cursor:pointer;"
)


_SOURCES_KOR = {
    "garmin": "Garmin",
    "strava": "Strava",
    "intervals": "Intervals",
    "runalyze": "Runalyze",
}
_ALL_SOURCES = list(_SOURCES_KOR.keys())


def _last_sync_line(last_sync: dict[str, str | None] | None) -> str:
    """소스별 마지막 동기화 시점 한 줄 HTML."""
    if not last_sync:
        return ""
    parts = []
    for src in _ALL_SOURCES:
        val = last_sync.get(src)
        label = _SOURCES_KOR[src]
        ts = _html.escape(val) if val else "미동기화"
        parts.append(f"{label}: {ts}")
    return (
        f"<p style='margin:0.45rem 0 0; font-size:0.78rem; color:var(--muted);'>"
        f"({' / '.join(parts)})"
        f"</p>"
    )


def _sync_state_banner(sync_states: dict | None) -> str:
    """서비스별 cooldown / 실행 중 / 오류 상태 배너 HTML.

    Args:
        sync_states: get_all_states() 반환값.
    """
    if not sync_states:
        return ""
    lines = []
    for src in _ALL_SOURCES:
        s = sync_states.get(src, {})
        label = _SOURCES_KOR[src]
        if s.get("is_running"):
            lines.append(
                f"<span style='color:#0066cc;'>⏳ {label}: 동기화 진행 중...</span>"
            )
        elif s.get("cooldown_sec"):
            from src.utils.sync_policy import _fmt_duration
            lines.append(
                f"<span style='color:#856404;'>⏱️ {label}: "
                f"{_fmt_duration(s['cooldown_sec'])} 후 동기화 가능</span>"
            )
        elif s.get("last_error"):
            err = _html.escape(str(s["last_error"])[:60])
            lines.append(f"<span style='color:#c0392b;'>⚠️ {label}: {err}</span>")
    if not lines:
        return ""
    joined = " &nbsp;|&nbsp; ".join(lines)
    return (
        f"<p style='margin:0.5rem 0 0; font-size:0.78rem; line-height:1.6;'>{joined}</p>"
    )


def sync_card_html(
    last_sync: dict[str, str | None] | None = None,
    sync_states: dict | None = None,
) -> str:
    """기본 동기화 + 기간 동기화 2탭 카드 HTML (AJAX 제출).

    Args:
        last_sync: last_sync_info() 반환값.
        sync_states: get_all_states() 반환값.
    """
    last_sync_html = _last_sync_line(last_sync)
    state_banner = _sync_state_banner(sync_states)
    return f"""
<div class="card" id="sync-card" style="border-color:#b3d9ff;">
  <h2 style="margin-bottom:0.75rem;">동기화</h2>
  <div style="display:flex; gap:0; border-bottom:2px solid var(--card-border); margin-bottom:1rem;">
    <button id="stab-basic" onclick="switchSyncTab('basic')"
      style="padding:0.4rem 1rem; border:none; border-bottom:2px solid #0066cc;
             margin-bottom:-2px; background:none; cursor:pointer;
             font-size:0.9rem; color:#0066cc; font-weight:600;">
      기본 동기화
    </button>
    <button id="stab-hist" onclick="switchSyncTab('hist')"
      style="padding:0.4rem 1rem; border:none; background:none;
             cursor:pointer; font-size:0.9rem; color:var(--muted);">
      기간 동기화
    </button>
  </div>

  <!-- 기본 동기화 패널 -->
  <div id="spanel-basic">
    <div style="display:flex; flex-wrap:wrap; gap:0.5rem; align-items:center;">
      <select id="basic-source" style="{_SELECT_STYLE}">{_SOURCE_OPTS}</select>
      <span class="muted" style="font-size:0.85rem;">마지막 동기화 이후 신규 기록</span>
      <button id="sbtn-basic" onclick="doSync('basic')" style="{_BTN_STYLE}">&#9654; 동기화</button>
    </div>
    {last_sync_html}
    {state_banner}
  </div>

  <!-- 기간 동기화 패널 -->
  <div id="spanel-hist" style="display:none;">
    <div style="display:flex; flex-wrap:wrap; gap:0.5rem; align-items:flex-end; margin-bottom:0.6rem;">
      <select id="hist-source" style="{_SELECT_STYLE}">{_SOURCE_OPTS}</select>
      <label style="display:flex; flex-direction:column; font-size:0.82rem; color:var(--muted);">
        시작일
        <input type="date" id="hist-from"
          style="padding:0.3rem 0.5rem; border-radius:4px; border:1px solid #ccc;
                 background:var(--card-bg); color:var(--fg);">
      </label>
      <label style="display:flex; flex-direction:column; font-size:0.82rem; color:var(--muted);">
        종료일 <span style="font-size:0.75rem;">(생략 시 오늘)</span>
        <input type="date" id="hist-to"
          style="padding:0.3rem 0.5rem; border-radius:4px; border:1px solid #ccc;
                 background:var(--card-bg); color:var(--fg);">
      </label>
      <button id="sbtn-hist" onclick="doSync('hist')" style="{_BTN_STYLE}">&#9654; 기간 동기화</button>
    </div>
    <label style="display:flex; align-items:center; gap:0.4rem; font-size:0.82rem; color:var(--muted); margin-bottom:0.4rem; cursor:pointer;">
      <input type="checkbox" id="hist-bg-mode" style="cursor:pointer;">
      백그라운드 자동 동기화 (API 부하 제어 — 배치 단위 순차 처리)
    </label>
  </div>

  <!-- 백그라운드 동기화 진행 섹션 -->
  <div id="bg-progress-section" style="display:none; margin-top:0.8rem; border-top:1px solid var(--card-border); padding-top:0.8rem;">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.4rem;">
      <span id="bg-progress-title" style="font-weight:600; font-size:0.9rem;"></span>
      <span id="bg-progress-pct" style="font-size:0.85rem; color:var(--muted);"></span>
    </div>
    <!-- 진행 바 -->
    <div style="background:var(--row-border); border-radius:4px; height:10px; overflow:hidden; margin-bottom:0.5rem;">
      <div id="bg-progress-bar" style="height:100%; background:#0066cc; border-radius:4px; width:0%; transition:width 0.4s;"></div>
    </div>
    <p id="bg-progress-detail" style="margin:0.25rem 0; font-size:0.82rem; color:var(--muted);"></p>
    <p id="bg-rate-info" style="margin:0.25rem 0; font-size:0.8rem; color:var(--muted);"></p>
    <p id="bg-error-info" style="margin:0.25rem 0; font-size:0.8rem; color:#c0392b; display:none;"></p>
    <div style="display:flex; gap:0.5rem; margin-top:0.5rem; flex-wrap:wrap;">
      <button id="bg-btn-pause" onclick="bgSyncPause()"
        style="padding:0.3rem 0.8rem; border-radius:4px; border:1px solid #ccc;
               background:none; cursor:pointer; font-size:0.82rem; display:none;">
        &#9646;&#9646; 일시중지
      </button>
      <button id="bg-btn-stop" onclick="bgSyncStop()"
        style="padding:0.3rem 0.8rem; border-radius:4px; border:1px solid #c0392b;
               color:#c0392b; background:none; cursor:pointer; font-size:0.82rem; display:none;">
        &#9632; 중지
      </button>
      <button id="bg-btn-resume" onclick="bgSyncResume()"
        style="padding:0.3rem 0.8rem; border-radius:4px; background:#0066cc;
               color:#fff; border:none; cursor:pointer; font-size:0.82rem; display:none;">
        &#9654; Resume
      </button>
    </div>
  </div>
</div>

<!-- 동기화 결과 모달 -->
<div id="sync-modal"
  style="display:none; position:fixed; inset:0; background:rgba(0,0,0,0.55);
         z-index:1000; align-items:center; justify-content:center;">
  <div style="background:var(--card-bg); border-radius:10px; padding:1.5rem 1.8rem;
              max-width:440px; width:90%; box-shadow:0 8px 32px rgba(0,0,0,0.25);">
    <div id="sync-modal-body"></div>
    <button onclick="document.getElementById('sync-modal').style.display='none'"
      style="margin-top:1rem; padding:0.4rem 1.2rem; cursor:pointer;
             border-radius:4px; border:1px solid #ccc;
             background:var(--card-bg); color:var(--fg);">
      닫기
    </button>
  </div>
</div>
"""

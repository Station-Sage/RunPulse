"""웹 뷰 공통 헬퍼 함수."""
from __future__ import annotations

import html as _html
from pathlib import Path

from src.utils.config import load_config

# 상단 드롭다운 nav 제거 — 하단 탭 + 페이지 내 서브링크로 대체

_CSS = """
    /* ── RunPulse v0.2 다크 테마 (ui-spec.md 기준) ── */
    :root {
        --bg: #1a1a2e; --bg2: #16213e; --bg3: #0f3460;
        --fg: #fff;
        --secondary: rgba(255,255,255,0.7);
        --muted: rgba(255,255,255,0.5);
        --card-bg: rgba(255,255,255,0.05);
        --card-border: rgba(255,255,255,0.1);
        --pre-bg: rgba(255,255,255,0.05);
        --th-bg: rgba(255,255,255,0.08);
        --row-border: rgba(255,255,255,0.08);
        --label-color: rgba(255,255,255,0.6);
        --nav-bg: rgba(26,26,46,0.95);
        --nav-border: rgba(255,255,255,0.1);
        --nav-hover: rgba(255,255,255,0.08);
        --cyan: #00d4ff;
        --green: #00ff88;
        --orange: #ffaa00;
        --red: #ff4444;
    }
    * { box-sizing: border-box; }
    body {
        font-family: 'Noto Sans KR', 'Inter', -apple-system, sans-serif;
        margin: 0; padding: 0; line-height: 1.5;
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        background-attachment: fixed;
        color: var(--fg); min-height: 100vh;
    }
    a { color: var(--cyan); text-decoration: none; }
    a:visited { color: var(--cyan); opacity: 0.85; }
    a:hover { text-decoration: underline; opacity: 1; }
    /* ── 스티키 헤더 ── */
    header {
        position: sticky; top: 0; z-index: 200;
        background: var(--nav-bg); backdrop-filter: blur(10px);
        border-bottom: 1px solid var(--nav-border);
        padding: 0.4rem 1rem; display: flex; align-items: center;
    }
    header .brand {
        font-weight: bold; font-size: 1rem;
        text-decoration: none; color: var(--cyan);
    }
    /* ── 콘텐츠 ── */
    main { max-width: 980px; margin: 0 auto; padding: 1.5rem 1rem 6rem; }
    pre { white-space: pre-wrap; word-break: break-word;
          background: var(--pre-bg); padding: 1rem; border-radius: 8px;
          overflow-x: auto; border: 1px solid var(--card-border);
          color: var(--secondary); }
    code { background: var(--pre-bg); padding: 0.15rem 0.35rem;
           border-radius: 4px; color: var(--cyan); font-size: 0.9em; }
    table { border-collapse: collapse; width: 100%; margin: 1rem 0; }
    th, td { border: 1px solid var(--card-border); padding: 0.5rem;
             text-align: left; vertical-align: top; }
    th { background: var(--th-bg); color: var(--secondary); }
    .muted { color: var(--muted); }
    /* ── 툴팁 (터치/호버) ── */
    .rp-tip { position: relative; cursor: help; border-bottom: 1px dotted rgba(255,255,255,0.3); }
    .rp-tip .rp-tip-text {
        visibility: hidden; opacity: 0;
        position: absolute; z-index: 100; bottom: 125%; left: 50%;
        transform: translateX(-50%);
        background: rgba(22,33,62,0.95); color: rgba(255,255,255,0.9);
        border: 1px solid var(--card-border); border-radius: 12px;
        padding: 10px 14px; font-size: 0.78rem; line-height: 1.5;
        width: max-content; max-width: 280px;
        pointer-events: none; transition: opacity 0.2s;
        box-shadow: 0 4px 12px rgba(0,0,0,0.4);
    }
    .rp-tip:hover .rp-tip-text,
    .rp-tip:focus .rp-tip-text,
    .rp-tip.active .rp-tip-text { visibility: visible; opacity: 1; pointer-events: auto; }
    .card { border: 1px solid var(--card-border); border-radius: 20px;
            padding: 1.2rem; margin: 1rem 0;
            background: var(--card-bg); backdrop-filter: blur(10px); }
    .card:hover { transform: translateY(-2px); transition: transform 0.2s; }
    .cards-row { display: flex; flex-wrap: wrap; gap: 1rem; margin: 1rem 0; }
    .cards-row > .card { flex: 1; min-width: 210px; margin: 0; }
    .score-badge { display: inline-block; padding: 0.2rem 0.8rem;
                   border-radius: 20px; font-weight: bold; font-size: 1.05rem; }
    .grade-excellent { background: rgba(0,255,136,0.15); color: var(--green);
                       border: 1px solid rgba(0,255,136,0.3); }
    .grade-good      { background: rgba(0,212,255,0.15); color: var(--cyan);
                       border: 1px solid rgba(0,212,255,0.3); }
    .grade-moderate  { background: rgba(255,170,0,0.15);  color: var(--orange);
                       border: 1px solid rgba(255,170,0,0.3); }
    .grade-poor      { background: rgba(255,68,68,0.15);   color: var(--red);
                       border: 1px solid rgba(255,68,68,0.3); }
    .grade-unknown   { background: rgba(255,255,255,0.05); color: var(--muted);
                       border: 1px solid var(--card-border); }
    .mrow { display: flex; justify-content: space-between; padding: 0.25rem 0;
            border-bottom: 1px solid var(--row-border); }
    .mrow:last-child { border-bottom: none; }
    .mlabel { color: var(--label-color); font-size: 0.9rem; }
    .mval   { font-weight: 500; color: var(--secondary); }
    h1 { margin-top: 0; font-size: 1.4rem; color: var(--fg); }
    h2 { margin-top: 0; font-size: 1.1rem; color: var(--secondary); }
    h3 { color: var(--secondary); }
    input, select, textarea {
        font-family: inherit;
        background: rgba(255,255,255,0.08); color: var(--fg);
        border: 1px solid var(--card-border); border-radius: 6px;
        padding: 0.4rem 0.7rem;
    }
    button {
        font-family: inherit; cursor: pointer;
        background: rgba(255,255,255,0.1); color: var(--fg);
        border: 1px solid var(--card-border); border-radius: 6px;
        padding: 0.4rem 0.8rem;
    }
    button:hover { background: rgba(255,255,255,0.18); }
    input:focus, select:focus, textarea:focus { outline: 2px solid var(--cyan); }
    label { color: var(--secondary); }
    .section-title {
        font-size: 1rem; font-weight: 600; color: var(--secondary);
        margin: 1.5rem 0 0.5rem; padding-left: 0.8rem;
        border-left: 4px solid var(--cyan);
    }
    /* ── 하단 7탭 네비게이션 ── */
    .bottom-nav {
        position: fixed; bottom: 0; left: 0; right: 0; z-index: 100;
        background: rgba(26,26,46,0.96); backdrop-filter: blur(10px);
        border-top: 1px solid rgba(255,255,255,0.1); padding: 4px 0;
    }
    .nav-items {
        max-width: 720px; margin: 0 auto; display: flex;
        justify-content: space-around;
    }
    .nav-item-tab {
        display: flex; flex-direction: column; align-items: center;
        padding: 6px 8px; text-decoration: none;
        color: var(--muted); min-width: 44px;
        border-radius: 8px; transition: color 0.2s;
    }
    .nav-item-tab:hover { color: var(--secondary); text-decoration: none; }
    .nav-item-tab.active { color: var(--cyan); }
    .nav-item-icon { font-size: 18px; line-height: 1; margin-bottom: 2px; }
    .nav-item-label { font-size: 10px; white-space: nowrap; }
    /* ── 모바일 반응형 ── */
    @media (max-width: 640px) {
        main { padding: 1rem 0.5rem 6rem; }
        .cards-row { flex-direction: column; }
        .cards-row > .card { min-width: unset; }
        table { font-size: 0.85rem; }
        th, td { padding: 0.3rem; }
        pre { font-size: 0.85rem; }
        h1 { font-size: 1.2rem; }
        .nav-item > a, .nav-item > span { padding: 0.45rem 0.5rem; font-size: 0.82rem; }
        .nav-item-tab { padding: 5px 4px; min-width: 36px; }
    }
"""


# ── 경로 헬퍼 ───────────────────────────────────────────────────────────
def project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def get_current_user_id() -> str:
    """현재 Flask 요청의 사용자 ID를 반환. 세션 없으면 'default'."""
    try:
        from flask import session
        return session.get("user_id", "default")
    except RuntimeError:
        # Flask 앱 컨텍스트 밖 (CLI 등)
        return "default"


def db_path(user_id: str | None = None) -> Path:
    """사용자별 running.db 경로. user_id 미지정 시 Flask 세션에서 추출."""
    from src.db_setup import get_db_path
    uid = user_id or get_current_user_id()
    return get_db_path(uid)


# ── HTML 조립 ───────────────────────────────────────────────────────────
def _build_nav() -> str:
    """상단 nav — 드롭다운 제거, 빈 문자열 반환. 하단 탭이 주 네비게이션."""
    return ""


def render_sub_nav(active: str = "report") -> str:
    """페이지 내 서브 네비게이션 (레포트/레이스/웰니스)."""
    items = [
        ("report", "📊 레포트", "/report"),
        ("race", "🏁 레이스 예측", "/race"),
        ("wellness", "💚 웰니스", "/wellness"),
    ]
    links = []
    for key, label, href in items:
        if key == active:
            style = "background:var(--cyan);color:#000;font-weight:600;"
        else:
            style = "background:rgba(255,255,255,0.07);color:var(--secondary);"
        links.append(
            f"<a href='{href}' style='{style}padding:0.4rem 0.9rem;"
            f"border-radius:20px;text-decoration:none;font-size:0.85rem;white-space:nowrap;'>{label}</a>"
        )
    return (
        "<div style='display:flex;gap:8px;margin-bottom:1rem;flex-wrap:wrap;'>"
        + "".join(links) + "</div>"
    )


_SYNC_JS = """
function switchSyncTab(t) {
  ['basic','hist'].forEach(function(id) {
    var tab = document.getElementById('stab-'+id);
    var panel = document.getElementById('spanel-'+id);
    if (!tab || !panel) return;
    var active = id === t;
    tab.style.borderBottom = active ? '2px solid #0066cc' : 'none';
    tab.style.color = active ? '#0066cc' : 'var(--muted)';
    tab.style.fontWeight = active ? '600' : 'normal';
    panel.style.display = active ? 'flex' : 'none';
  });
}

function _getCheckedSources(panel) {
  var chks = document.querySelectorAll('input[data-panel="' + panel + '"]:checked');
  var srcs = Array.from(chks).map(function(c) { return c.getAttribute('data-src'); });
  return srcs.length === 0 ? null : (srcs.length === 4 ? 'all' : srcs.join(','));
}

function toggleSyncSrc(panel, src, color) {
  var cid = panel + '-chk-' + src;
  var chk = document.getElementById(cid);
  if (!chk) return;
  var label = document.getElementById(cid + '-label');
  var icon = document.getElementById(cid + '-icon');
  chk.checked = !chk.checked;
  if (chk.checked) {
    label.style.background = color;
    label.style.color = '#fff';
    if (icon) icon.textContent = '✓';
  } else {
    label.style.background = 'transparent';
    label.style.color = color;
    if (icon) icon.textContent = '';
  }
  var allIcon = document.getElementById(panel + '-all-icon');
  if (allIcon) {
    var allChks = document.querySelectorAll('input[data-panel="' + panel + '"]');
    var allChecked = Array.from(allChks).every(function(c) { return c.checked; });
    allIcon.textContent = allChecked ? '전체 해제' : '전체 선택';
  }
}

function toggleAllSyncSrc(panel) {
  var allChks = document.querySelectorAll('input[data-panel="' + panel + '"]');
  var allChecked = Array.from(allChks).every(function(c) { return c.checked; });
  var services = [{src:'garmin',color:'#0055b3'},{src:'strava',color:'#FC4C02'},
                  {src:'intervals',color:'#00884e'},{src:'runalyze',color:'#7b2d8b'}];
  services.forEach(function(s) {
    var cid = panel + '-chk-' + s.src;
    var chk = document.getElementById(cid);
    if (!chk) return;
    var label = document.getElementById(cid + '-label');
    var icon = document.getElementById(cid + '-icon');
    chk.checked = !allChecked;
    if (!allChecked) {
      label.style.background = s.color; label.style.color = '#fff';
      if (icon) icon.textContent = '✓';
    } else {
      label.style.background = 'transparent'; label.style.color = s.color;
      if (icon) icon.textContent = '';
    }
  });
  var allIcon = document.getElementById(panel + '-all-icon');
  if (allIcon) allIcon.textContent = allChecked ? '전체 선택' : '전체 해제';
}

// 초기화: 기본 checked 상태에 맞게 스타일 적용
document.addEventListener('DOMContentLoaded', function() {
  ['basic','hist'].forEach(function(panel) {
    var services = [{src:'garmin',color:'#0055b3'},{src:'strava',color:'#FC4C02'},
                    {src:'intervals',color:'#00884e'},{src:'runalyze',color:'#7b2d8b'}];
    services.forEach(function(s) {
      var cid = panel + '-chk-' + s.src;
      var chk = document.getElementById(cid);
      if (!chk || !chk.checked) return;
      var label = document.getElementById(cid + '-label');
      if (label) { label.style.background = s.color; label.style.color = '#fff'; }
    });
  });
});

async function doSync(mode) {
  var btnId = mode === 'basic' ? 'sbtn-basic' : 'sbtn-hist';
  var btn = document.getElementById(btnId);
  if (!btn) return;
  var source = _getCheckedSources(mode === 'basic' ? 'basic' : 'hist');
  if (!source) { alert('서비스를 하나 이상 선택하세요.'); return; }

  // 기간 동기화 + BG 모드 체크
  if (mode === 'hist') {
    var from = (document.getElementById('hist-from') || {}).value || '';
    if (!from) { alert('시작일을 입력하세요.'); return; }
    var bgMode = (document.getElementById('hist-bg-mode') || {}).checked;
    if (bgMode) {
      var srcs = source === 'all'
        ? ['garmin','strava','intervals','runalyze']
        : source.split(',');
      await startBgSyncMulti(srcs, from, (document.getElementById('hist-to') || {}).value || '');
      return;
    }
  }

  var fd = new FormData();
  fd.append('mode', mode);
  fd.append('source', source);
  if (mode === 'hist') {
    var from2 = (document.getElementById('hist-from') || {}).value || '';
    fd.append('from_date', from2);
    var to2 = (document.getElementById('hist-to') || {}).value || '';
    if (to2) fd.append('to_date', to2);
  }
  var orig = btn.textContent;
  btn.disabled = true; btn.textContent = '동기화 중\u2026';
  try {
    var resp = await fetch('/trigger-sync', {method: 'POST', body: fd});
    var data = await resp.json();
    var failed = data.results.filter(function(r) { return !r.ok && !r.skipped; });
    var succeeded = data.results.filter(function(r) { return r.ok; });
    if (failed.length === 0) {
      syncToast('\u2705 동기화 완료 \u2014 활동 ' + data.total_count + '개 업데이트', 'success');
      setTimeout(function() { location.reload(); }, 2200);
    } else if (succeeded.length > 0) {
      syncToast('\u26a0\ufe0f 일부 동기화 완료 \u2014 활동 ' + data.total_count + '개', 'warn');
      syncModal(data);
    } else {
      syncModal(data);
    }
  } catch(e) {
    syncToast('\u274c 요청 실패: ' + e.message, 'error');
  } finally {
    btn.disabled = false; btn.textContent = orig;
  }
}

function syncToast(msg, type) {
  var colors = {
    success: {bg:'#d4edda', fg:'#155724', border:'#28a745'},
    warn:    {bg:'#fff3cd', fg:'#856404', border:'#ffc107'},
    error:   {bg:'#f8d7da', fg:'#721c24', border:'#dc3545'}
  };
  var c = colors[type] || colors.error;
  var el = document.createElement('div');
  el.style.cssText = 'position:fixed;bottom:1.5rem;right:1.5rem;z-index:2000;'
    + 'padding:0.75rem 1.25rem;border-radius:8px;font-size:0.9rem;'
    + 'box-shadow:0 4px 16px rgba(0,0,0,0.18);max-width:340px;'
    + 'border-left:4px solid '+c.border+';background:'+c.bg+';color:'+c.fg+';';
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(function() { if (el.parentNode) el.parentNode.removeChild(el); }, 4500);
}

function syncModal(data) {
  var body = document.getElementById('sync-modal-body');
  if (!body) return;
  var h = '<h3 style="margin-top:0;">동기화 결과</h3>';
  (data.results || []).forEach(function(r) {
    var icon = r.ok ? '\u2705' : (r.skipped ? '\u23ed\ufe0f' : '\u274c');
    var detail = r.ok ? ('활동 ' + r.count + '개') : (r.error || '오류');
    h += '<div style="margin:0.4rem 0;"><strong>' + icon + ' ' + r.source
      + '</strong>: <span style="color:var(--muted);font-size:0.88rem;">'
      + detail + '</span></div>';
  });
  body.innerHTML = h;
  document.getElementById('sync-modal').style.display = 'flex';
}

// ── 백그라운드 동기화 ────────────────────────────────────────────────────
var _bgPollTimer = null;
var _bgActiveSources = [];  // 현재 활성 서비스 목록

async function startBgSyncMulti(srcs, fromDate, toDate) {
  var started = [];
  for (var i = 0; i < srcs.length; i++) {
    var fd = new FormData();
    fd.append('source', srcs[i]);
    fd.append('from_date', fromDate);
    if (toDate) fd.append('to_date', toDate);
    try {
      var resp = await fetch('/bg-sync/start', {method: 'POST', body: fd});
      var data = await resp.json();
      if (data.ok) started.push(srcs[i]);
    } catch(e) { /* ignore per-service error */ }
  }
  if (started.length === 0) { syncToast('\u274c 시작 실패', 'error'); return; }
  _bgActiveSources = started;
  syncToast('\u25b6 백그라운드 동기화 시작 (' + started.join(', ') + ')', 'success');
  bgShowProgress();
  bgStartPollingAll(started);
}

function bgStartPollingAll(sources) {
  if (_bgPollTimer) clearInterval(_bgPollTimer);
  _bgPollTimer = setInterval(function() { bgPollAll(sources); }, 3000);
  bgPollAll(sources);
}

async function bgPollAll(sources) {
  try {
    var statuses = await Promise.all(sources.map(function(src) {
      return fetch('/bg-sync/status?source=' + encodeURIComponent(src))
        .then(function(r) { return r.json(); })
        .catch(function() { return {active: false}; });
    }));
    var active = statuses.filter(function(d) { return d.active; });
    if (active.length === 0) {
      bgStopPolling();
      bgHideProgress();
      // 서비스들이 completed → active:false 전환 (bgPollAll이 실행 중이었다면 완료 의미)
      if (_bgActiveSources.length > 0) {
        syncToast('\u2705 기간 동기화 완료', 'success');
        setTimeout(function() { location.reload(); }, 2500);
      }
      return;
    }
    bgUpdateAllUI(active);
    var allDone = active.every(function(d) {
      return d.status === 'completed' || d.status === 'stopped';
    });
    if (allDone) {
      bgStopPolling();
      var total = active.reduce(function(s, d) { return s + (d.synced_count || 0); }, 0);
      syncToast('\u2705 기간 동기화 완료 \u2014 활동 ' + total + '개', 'success');
      setTimeout(function() { location.reload(); }, 2500);
    }
  } catch(e) { /* 네트워크 오류 — 다음 polling에서 재시도 */ }
}

function bgStopPolling() {
  if (_bgPollTimer) { clearInterval(_bgPollTimer); _bgPollTimer = null; }
}

function bgShowProgress() {
  var sec = document.getElementById('bg-progress-section');
  if (sec) sec.style.display = 'block';
}

function bgHideProgress() {
  var sec = document.getElementById('bg-progress-section');
  if (sec) sec.style.display = 'none';
}

function bgUpdateAllUI(statuses) {
  bgShowProgress();
  var svcKor = {garmin:'Garmin', strava:'Strava', intervals:'Intervals.icu', runalyze:'Runalyze'};
  var statusKor = {running:'동기화 중', paused:'일시중지', stopped:'중지됨',
                   rate_limited:'API 한도 대기', completed:'완료', pending:'대기 중'};
  var svcColors = {running:'#0066cc', paused:'#856404', stopped:'#888',
                   rate_limited:'#856404', completed:'#28a745', pending:'#888'};

  var container = document.getElementById('bg-jobs-container');
  if (!container) return;
  container.innerHTML = '';

  var anyRunning = false, anyPaused = false, anyResumable = false;
  statuses.forEach(function(d) {
    var isRunning = d.status === 'running' || d.status === 'pending';
    var isPaused = d.status === 'paused' || d.status === 'stopped';
    var isRL = d.status === 'rate_limited';
    if (isRunning) anyRunning = true;
    if (isPaused) anyPaused = true;
    if (isPaused || isRL) anyResumable = true;

    var svcName = svcKor[d.service] || d.service;
    var statusText = statusKor[d.status] || d.status;
    var barColor = svcColors[d.status] || '#0066cc';
    var pct = d.progress_pct || 0;
    var detailTxt = d.current_from ? (d.current_from + ' ~ ' + (d.current_to || '')) : '';
    var errHtml = (d.last_error && d.status !== 'rate_limited')
      ? '<span style="color:#c0392b; font-size:0.78rem;"> \u26a0\ufe0f ' + d.last_error.substring(0,60) + '</span>'
      : '';
    var rlHtml = isRL && d.retry_after_sec > 0
      ? '<span style="color:#856404; font-size:0.78rem;"> \u231b ' + Math.ceil(d.retry_after_sec/60) + '\ubd84 \ub300\uae30</span>'
      : '';

    container.innerHTML +=
      '<div style="margin-bottom:0.6rem;">' +
        '<div style="display:flex; justify-content:space-between; font-size:0.84rem; margin-bottom:2px;">' +
          '<span><strong>' + svcName + '</strong> \u2014 <span style="color:' + barColor + ';">' + statusText + '</span>' + errHtml + rlHtml + '</span>' +
          '<span style="color:var(--muted);">' + pct + '% (' + d.synced_count + '\uac1c)</span>' +
        '</div>' +
        '<div style="background:var(--row-border); border-radius:3px; height:7px; overflow:hidden;">' +
          '<div style="height:100%; background:' + barColor + '; border-radius:3px; width:' + pct + '%; transition:width 0.4s;"></div>' +
        '</div>' +
        (detailTxt ? '<div style="font-size:0.76rem; color:var(--muted); margin-top:2px;">' + detailTxt + '</div>' : '') +
      '</div>';
  });

  var btnPause = document.getElementById('bg-btn-pause');
  var btnStop = document.getElementById('bg-btn-stop');
  var btnResume = document.getElementById('bg-btn-resume');
  if (btnPause) btnPause.style.display = anyRunning ? 'inline-block' : 'none';
  if (btnStop) btnStop.style.display = (anyRunning || anyPaused) ? 'inline-block' : 'none';
  if (btnResume) btnResume.style.display = anyResumable ? 'inline-block' : 'none';
}

async function bgSyncPause() {
  for (var i = 0; i < _bgActiveSources.length; i++) {
    var fd = new FormData(); fd.append('source', _bgActiveSources[i]);
    await fetch('/bg-sync/pause', {method: 'POST', body: fd});
  }
}

async function bgSyncStop() {
  var btn = document.getElementById('bg-btn-stop');
  if (btn) { btn.disabled = true; btn.textContent = '중지 중...'; }
  for (var i = 0; i < _bgActiveSources.length; i++) {
    var fd = new FormData(); fd.append('source', _bgActiveSources[i]);
    await fetch('/bg-sync/stop', {method: 'POST', body: fd});
  }
  bgStopPolling();
  bgHideProgress();
  _bgActiveSources = [];
  syncToast('\u23f9 동기화 중지됨', 'info');
}

async function bgSyncResume() {
  var resumed = [];
  for (var i = 0; i < _bgActiveSources.length; i++) {
    var fd = new FormData(); fd.append('source', _bgActiveSources[i]);
    var resp = await fetch('/bg-sync/resume', {method: 'POST', body: fd});
    var data = await resp.json();
    if (data.ok) resumed.push(_bgActiveSources[i]);
  }
  if (resumed.length > 0) {
    syncToast('\u25b6 동기화 재개 (' + resumed.join(', ') + ')', 'success');
    bgStartPollingAll(_bgActiveSources);
  } else {
    syncToast('\u274c 재개 실패', 'error');
  }
}

// 페이지 로드 시 활성 BG 작업 복구 (새로고침 후에도 진행 표시)
(function() {
  var sources = ['garmin', 'strava', 'intervals', 'runalyze'];
  var active = [];
  Promise.all(sources.map(function(src) {
    return fetch('/bg-sync/status?source=' + src)
      .then(function(r) { return r.json(); })
      .then(function(d) { if (d.active && d.status !== 'completed' && d.status !== 'stopped') active.push(src); })
      .catch(function(){});
  })).then(function() {
    if (active.length > 0) {
      _bgActiveSources = active;
      bgShowProgress();
      bgStartPollingAll(active);
    }
  });
})();
"""


_ECHARTS_CDN = "https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"
_FONTS_CDN = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR'
    ':wght@300;400;500;700&family=Inter:wght@400;600&display=swap" rel="stylesheet">'
)

# ── 7탭 하단 네비게이션 ──────────────────────────────────────────────────────
_BOTTOM_NAV_TABS = [
    ("dashboard",   "🏠", "홈",     "/dashboard"),
    ("activities",  "🏃", "활동",   "/activities"),
    ("report",      "📊", "레포트", "/report"),
    ("training",    "🗓️", "훈련",   "/training"),
    ("ai-coach",    "🤖", "AI코치", "/ai-coach"),
    ("settings",    "⚙️", "설정",   "/settings"),
]
_BOTTOM_NAV_DEV = ("dev", "🛠️", "개발자", "/dev")


def bottom_nav(active_tab: str, dev_mode: bool = False) -> str:
    """7탭 하단 고정 네비게이션 HTML.

    Args:
        active_tab: 현재 활성 탭 키 (예: 'dashboard').
        dev_mode: True 이면 개발자 탭 노출.
    """
    tabs = list(_BOTTOM_NAV_TABS)
    if dev_mode:
        tabs.append(_BOTTOM_NAV_DEV)
    items = []
    for tab_key, icon, label, href in tabs:
        cls = "nav-item-tab active" if tab_key == active_tab else "nav-item-tab"
        items.append(
            f'<a class="{cls}" href="{href}">'
            f'<span class="nav-item-icon">{icon}</span>'
            f'<span class="nav-item-label">{label}</span>'
            f'</a>'
        )
    return (
        "<nav class='bottom-nav'>"
        "<div class='nav-items'>" + "".join(items) + "</div>"
        "</nav>"
    )


def html_page(
    title: str,
    body: str,
    extra_head: str = "",
    active_tab: str = "",
    dev_mode: bool | None = None,
) -> str:
    """전체 HTML 페이지 생성 (스티키 헤더 + 드롭다운 nav + 하단 7탭 nav 포함).

    Args:
        title: 페이지 제목.
        body: main 영역 HTML.
        extra_head: <head> 내 추가 태그 (스크립트/스타일).
        active_tab: 하단 7탭 nav 활성 탭 키. 빈 문자열이면 nav 미표시.
        dev_mode: True/False 명시 또는 None(config에서 자동 읽기).
    """
    if dev_mode is None:
        try:
            dev_mode = bool(load_config().get("dev_mode", True))
        except Exception:
            dev_mode = True
    bottom = bottom_nav(active_tab, dev_mode) if active_tab else ""
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#1a1a2e">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
  <link rel="manifest" href="/static/manifest.json">
  <link rel="icon" type="image/png" sizes="192x192" href="/static/icons/icon-192.png">
  <link rel="apple-touch-icon" href="/static/icons/icon-192-maskable.png">
  <title>{_html.escape(title)} — RunPulse</title>
  {_FONTS_CDN}
  <style>{_CSS}</style>
  <script src="{_ECHARTS_CDN}"></script>
  {extra_head}
</head>
<body>
  <header>
    <a class="brand" href="/">RunPulse</a>
  </header>
  <main>
    <h1>{_html.escape(title)}</h1>
    {body}
  </main>
  {bottom}
  <script>{_SYNC_JS}</script>
  <script>
  if('serviceWorker' in navigator){{navigator.serviceWorker.register('/static/sw.js').catch(function(){{}});}}
  document.addEventListener('click',function(e){{var t=e.target.closest('.rp-tip');document.querySelectorAll('.rp-tip.active').forEach(function(el){{if(el!==t)el.classList.remove('active')}});if(t)t.classList.toggle('active');}});
  </script>
</body>
</html>"""


def make_table(headers: list[str], rows: list[tuple]) -> str:
    """HTML 테이블 생성."""
    if not rows:
        return "<p class='muted'>(데이터 없음)</p>"
    head = "".join(f"<th>{_html.escape(str(h))}</th>" for h in headers)
    body_rows = [
        "<tr>" + "".join(f"<td>{_html.escape(str(v))}</td>" for v in row) + "</tr>"
        for row in rows
    ]
    return (
        f"<table><thead><tr>{head}</tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody></table>"
    )


def metric_row(label: str, value, unit: str = "") -> str:
    """라벨-값 한 줄 렌더링."""
    v = "—" if value is None else f"{value}{unit}"
    return (
        f"<div class='mrow'>"
        f"<span class='mlabel'>{_html.escape(label)}</span>"
        f"<span class='mval'>{_html.escape(str(v))}</span>"
        f"</div>"
    )


def score_badge(grade: str | None, score) -> str:
    """점수 + 등급 배지 HTML."""
    grade_class = {
        "excellent": "grade-excellent",
        "good": "grade-good",
        "moderate": "grade-moderate",
        "poor": "grade-poor",
    }.get(grade or "", "grade-unknown")
    score_text = "—" if score is None else str(score)
    grade_kor = {
        "excellent": "최상", "good": "좋음", "moderate": "보통", "poor": "부족"
    }.get(grade or "", grade or "—")
    return (
        f"<span class='score-badge {grade_class}'>"
        f"{_html.escape(score_text)} ({_html.escape(grade_kor)})"
        f"</span>"
    )


def readiness_badge(score) -> str:
    """훈련 준비도 점수 배지 (0-100)."""
    if score is None:
        return "<span class='score-badge grade-unknown'>— (데이터 없음)</span>"
    s = float(score)
    if s >= 70:
        cls, label = "grade-excellent", "준비 완료"
    elif s >= 50:
        cls, label = "grade-good", "양호"
    elif s >= 30:
        cls, label = "grade-moderate", "보통"
    else:
        cls, label = "grade-poor", "회복 필요"
    return (
        f"<span class='score-badge {cls}'>"
        f"{_html.escape(str(score))} ({_html.escape(label)})"
        f"</span>"
    )


def fmt_min(seconds) -> str:
    """초 → 분(시간) 형식 문자열."""
    if seconds is None:
        return "—"
    try:
        m = int(seconds) // 60
        h, rem = divmod(m, 60)
        return f"{h}h {rem}m" if h else f"{m}분"
    except Exception:
        return str(seconds)


def fmt_duration(seconds) -> str:
    """초 → h m s 형식 문자열."""
    if seconds is None:
        return "—"
    try:
        total = int(seconds)
        h, rem = divmod(total, 3600)
        m, s = divmod(rem, 60)
        if h:
            return f"{h}h {m}m {s}s"
        if m:
            return f"{m}m {s}s"
        return f"{s}s"
    except Exception:
        return str(seconds)


def safe_str(value, default: str = "—") -> str:
    return default if value is None else str(value)


def connected_services() -> set[str]:
    """현재 연결된 서비스 이름 집합 반환 (연결 확인 후).

    Returns:
        {"garmin", "strava", ...} — ok인 서비스만 포함.
    """
    try:
        from src.sync.garmin import check_garmin_connection
        from src.sync.strava import check_strava_connection
        from src.sync.intervals import check_intervals_connection
        from src.sync.runalyze import check_runalyze_connection
        cfg = load_config()
        checkers = {
            "garmin":    check_garmin_connection,
            "strava":    check_strava_connection,
            "intervals": check_intervals_connection,
            "runalyze":  check_runalyze_connection,
        }
        return {src for src, chk in checkers.items() if chk(cfg).get("ok")}
    except Exception:
        return set()


def tooltip(label: str, description: str) -> str:
    """터치/호버 시 설명이 표시되는 인라인 툴팁.

    Args:
        label: 표시 텍스트 (예: 'UTRS').
        description: 툴팁 설명 텍스트.
    """
    return (
        f"<span class='rp-tip' tabindex='0'>{_html.escape(label)}"
        f"<span class='rp-tip-text'>{_html.escape(description)}</span></span>"
    )


# 메트릭 설명 사전
METRIC_DESCRIPTIONS: dict[str, str] = {
    "UTRS": "통합 훈련 준비도 (0~100). 웰니스·피트니스·부하를 종합. 70+ 고강도 가능, 40 미만 휴식 권장",
    "CIRS": "복합 부상 위험 지수 (0~100). ACWR·Monotony·부하 스파이크 종합. 25 이하 안전, 50+ 주의",
    "ACWR": "급성:만성 부하 비율. 0.8~1.3 적정(Sweet Spot), 1.5+ 부상 위험, 0.8 미만 훈련 부족",
    "RTTI": "달리기 내성 지수 (%). 100=적정 훈련량, 100+ 과부하, 70 미만 여유",
    "LSI": "부하 스파이크. 1.0 이하 안정, 1.5+ 급격한 부하 증가 주의",
    "Monotony": "훈련 단조로움. 2.0+ 위험 (매일 비슷한 부하), 1.5 이하 적정",
    "Strain": "훈련 부담 = 주간TRIMP × Monotony. Monotony 높을 때 Strain도 급증",
    "TSB": "훈련 스트레스 밸런스 = CTL-ATL. 양수=신선, 음수=피로 축적, -10~+10 적정",
    "VDOT": "Jack Daniels VO2Max 추정치. 레이스 기록 기반 유산소 능력 지표",
    "MarathonShape": "마라톤 훈련 완성도 (%). 주간 거리+장거리런 대비 VDOT 기준 달성률",
    "EF": "효율 계수 = 속도/심박. 같은 HR에서 더 빠르면 EF↑ → 체력 향상",
    "Decoupling": "심박-페이스 분리율(%). 5% 이하면 유산소 기반 양호, 10%+ 지구력 부족",
    "TIDS": "훈련 강도 분포. Z1-2(저강도)/Z3(중강도)/Z4-5(고강도) 비율",
    "DI": "내구성 지수. 장거리 러닝에서 후반부 페이스 유지 능력",
    "DARP": "내구성 보정 레이스 예측. DI 반영한 실제 레이스 완주 시간 예측",
    "RMR": "러너 성숙도 레이더. 유산소용량/역치강도/지구력/동작효율성/회복력 5축",
    "FEARP": "환경 보정 페이스. 기온·습도·고도를 반영한 실질 페이스",
}


def no_data_card(metric_name: str, reason: str = "데이터 수집 중") -> str:
    """데이터 없을 때 graceful 카드."""
    return (
        f"<div class='card' style='text-align:center;padding:1.5rem;'>"
        f"<p style='font-size:1.8rem;margin:0;'>📊</p>"
        f"<p style='margin:0.5rem 0 0.2rem;font-weight:600;'>{_html.escape(metric_name)}</p>"
        f"<p class='muted' style='margin:0;font-size:0.88rem;'>{_html.escape(reason)}</p>"
        f"</div>"
    )


# SVG 헬퍼는 helpers_svg.py로 분리 — 하위 호환을 위해 re-export
from .helpers_svg import svg_semicircle_gauge, svg_radar_chart  # noqa: F401


def fmt_pace(pace_sec_km) -> str:
    """초/km → M:SS/km 포맷."""
    if pace_sec_km is None:
        return "—"
    try:
        total = int(pace_sec_km)
        m, s = divmod(total, 60)
        return f"{m}'{s:02d}\""
    except Exception:
        return str(pace_sec_km)


def last_sync_info(sources: list[str]) -> dict[str, str | None]:
    """소스별 마지막 동기화 시점(start_time 기준) 반환.

    Returns:
        {"garmin": "2026-03-20 14:30", "strava": None, ...}
    """
    import sqlite3
    dpath = db_path()
    if not dpath.exists():
        return {s: None for s in sources}
    result: dict[str, str | None] = {}
    try:
        with sqlite3.connect(str(dpath)) as conn:
            for src in sources:
                row = conn.execute(
                    "SELECT MAX(start_time) FROM activity_summaries WHERE source = ?",
                    (src,),
                ).fetchone()
                val = row[0] if row and row[0] else None
                result[src] = str(val)[:16].replace("T", " ") if val else None
    except Exception:
        result = {s: None for s in sources}
    return result

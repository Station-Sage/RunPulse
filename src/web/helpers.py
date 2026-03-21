"""웹 뷰 공통 헬퍼 함수."""
from __future__ import annotations

import html as _html
from pathlib import Path

from src.utils.config import load_config

# ── 내비게이션 그룹 구조 ──────────────────────────────────────────────
# (label, href_or_None, [(sub_label, sub_href), ...])
_NAV_GROUPS = [
    ("홈", "/", []),
    ("훈련 데이터", None, [
        ("활동 목록", "/activities"),
        ("활동 심층 분석", "/activity/deep"),
        ("회복·웰니스", "/wellness"),
    ]),
    ("분석", None, [
        ("Today", "/analyze/today"),
        ("Full Report", "/analyze/full"),
        ("Race 준비도", "/analyze/race?date=2026-06-01&distance=42.195"),
    ]),
    ("⚙️ 설정", None, [
        ("연동 설정", "/settings"),
        ("동기화", "/sync-status"),
        ("Config", "/config"),
    ]),
    ("🔧 개발자", None, [
        ("DB", "/db"),
        ("Payloads", "/payloads"),
        ("Import", "/import"),
    ]),
]

_CSS = """
    /* ── 기본 스타일 ── */
    :root {
        --bg: #fff; --fg: #111; --muted: #666;
        --card-bg: #fafafa; --card-border: #ddd;
        --pre-bg: #f5f5f5; --th-bg: #f0f0f0;
        --row-border: #eee; --label-color: #555;
        --nav-bg: #fff; --nav-border: #e0e0e0;
        --nav-hover: #f0f0f0; --dropdown-bg: #fff;
    }
    @media (prefers-color-scheme: dark) {
        :root {
            --bg: #1a1a1a; --fg: #e8e8e8; --muted: #999;
            --card-bg: #242424; --card-border: #444;
            --pre-bg: #2a2a2a; --th-bg: #2e2e2e;
            --row-border: #333; --label-color: #aaa;
            --nav-bg: #1a1a1a; --nav-border: #333;
            --nav-hover: #2e2e2e; --dropdown-bg: #242424;
        }
        a { color: #7ab8ff; }
        a:visited { color: #b39ddb; }
        .grade-excellent { background: #1a4d1a !important; color: #6fcf6f !important; }
        .grade-good      { background: #0d3055 !important; color: #79c0ff !important; }
        .grade-moderate  { background: #4a3800 !important; color: #f0c040 !important; }
        .grade-poor      { background: #4d0f0f !important; color: #f08080 !important; }
        .grade-unknown   { background: #333    !important; color: #aaa    !important; }
    }
    /* ── 스티키 헤더 & 네비게이션 ── */
    body {
        font-family: sans-serif; max-width: none; margin: 0;
        padding: 0; line-height: 1.5;
        background: var(--bg); color: var(--fg);
    }
    header {
        position: sticky; top: 0; z-index: 200;
        background: var(--nav-bg);
        border-bottom: 1px solid var(--nav-border);
        padding: 0 1rem;
    }
    header .brand {
        font-weight: bold; font-size: 1rem; padding: 0.5rem 0.4rem;
        display: inline-block; text-decoration: none; color: var(--fg);
    }
    nav { display: flex; flex-wrap: wrap; align-items: center; gap: 0; }
    .nav-item { position: relative; }
    .nav-item > a, .nav-item > span {
        display: inline-block; padding: 0.55rem 0.75rem;
        white-space: nowrap; text-decoration: none; color: var(--fg);
        font-size: 0.9rem; cursor: pointer; border-radius: 4px;
    }
    .nav-item > a:hover, .nav-item > span:hover,
    .nav-item:hover > span { background: var(--nav-hover); }
    .nav-item > span::after { content: " ▾"; font-size: 0.7rem; opacity: 0.7; }
    /* 드롭다운 */
    .dropdown-menu {
        display: none; position: absolute; top: 100%; left: 0;
        background: var(--dropdown-bg); border: 1px solid var(--nav-border);
        border-radius: 6px; min-width: 160px; box-shadow: 0 4px 12px rgba(0,0,0,0.12);
        z-index: 300; padding: 0.25rem 0;
    }
    .nav-item:hover .dropdown-menu { display: block; }
    .dropdown-menu a {
        display: block; padding: 0.45rem 1rem;
        text-decoration: none; color: var(--fg); font-size: 0.88rem;
    }
    .dropdown-menu a:hover { background: var(--nav-hover); }
    main { max-width: 980px; margin: 0 auto; padding: 1.5rem 1rem; }
    pre { white-space: pre-wrap; word-break: break-word; background: var(--pre-bg);
          padding: 1rem; border-radius: 8px; overflow-x: auto; }
    code { background: var(--pre-bg); padding: 0.15rem 0.35rem; border-radius: 4px; }
    table { border-collapse: collapse; width: 100%; margin: 1rem 0; }
    th, td { border: 1px solid var(--card-border); padding: 0.5rem;
             text-align: left; vertical-align: top; }
    th { background: var(--th-bg); }
    .muted { color: var(--muted); }
    .card { border: 1px solid var(--card-border); border-radius: 8px;
            padding: 1rem; margin: 1rem 0; background: var(--card-bg); }
    .cards-row { display: flex; flex-wrap: wrap; gap: 1rem; margin: 1rem 0; }
    .cards-row > .card { flex: 1; min-width: 210px; margin: 0; }
    .score-badge { display: inline-block; padding: 0.2rem 0.8rem;
                   border-radius: 20px; font-weight: bold; font-size: 1.05rem; }
    .grade-excellent { background: #c8f7c5; color: #1a7a17; }
    .grade-good      { background: #d4edff; color: #0056b3; }
    .grade-moderate  { background: #fff3cd; color: #856404; }
    .grade-poor      { background: #ffd6d6; color: #c0392b; }
    .grade-unknown   { background: #eee;    color: #555; }
    .mrow { display: flex; justify-content: space-between; padding: 0.25rem 0;
            border-bottom: 1px solid var(--row-border); }
    .mrow:last-child { border-bottom: none; }
    .mlabel { color: var(--label-color); font-size: 0.9rem; }
    .mval   { font-weight: 500; }
    h1 { margin-top: 0; }
    h2 { margin-top: 0; }
    /* ── 모바일 반응형 ── */
    @media (max-width: 640px) {
        main { padding: 1rem 0.5rem; }
        .cards-row { flex-direction: column; }
        .cards-row > .card { min-width: unset; }
        table { font-size: 0.85rem; }
        th, td { padding: 0.3rem; }
        pre { font-size: 0.85rem; }
        h1 { font-size: 1.3rem; }
        .nav-item > a, .nav-item > span { padding: 0.45rem 0.5rem; font-size: 0.82rem; }
    }
"""


# ── 경로 헬퍼 ───────────────────────────────────────────────────────────
def project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def db_path() -> Path:
    config = load_config()
    db_value = config.get("database", {}).get("path")
    if db_value:
        return Path(db_value).expanduser()
    return project_root() / "running.db"


# ── HTML 조립 ───────────────────────────────────────────────────────────
def _build_nav() -> str:
    """그룹 드롭다운 네비게이션 HTML 빌드."""
    items = []
    for label, href, children in _NAV_GROUPS:
        if not children:
            items.append(
                f'<div class="nav-item"><a href="{href}">{_html.escape(label)}</a></div>'
            )
        else:
            links = "".join(
                f'<a href="{child_href}">{_html.escape(child_label)}</a>'
                for child_label, child_href in children
            )
            items.append(
                f'<div class="nav-item">'
                f'<span>{_html.escape(label)}</span>'
                f'<div class="dropdown-menu">{links}</div>'
                f'</div>'
            )
    return "".join(items)


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

async function doSync(mode) {
  var btnId = mode === 'basic' ? 'sbtn-basic' : 'sbtn-hist';
  var btn = document.getElementById(btnId);
  if (!btn) return;
  var srcId = mode === 'basic' ? 'basic-source' : 'hist-source';
  var source = (document.getElementById(srcId) || {}).value || 'all';

  // 기간 동기화 + BG 모드 체크
  if (mode === 'hist') {
    var from = (document.getElementById('hist-from') || {}).value || '';
    if (!from) { alert('시작일을 입력하세요.'); return; }
    var bgMode = (document.getElementById('hist-bg-mode') || {}).checked;
    if (bgMode && source !== 'all') {
      await startBgSync(source, from, (document.getElementById('hist-to') || {}).value || '');
      return;
    }
    if (bgMode && source === 'all') {
      alert('백그라운드 자동 동기화는 서비스를 하나씩 선택하여 사용하세요.');
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
var _bgCurrentSource = null;

async function startBgSync(source, fromDate, toDate) {
  var fd = new FormData();
  fd.append('source', source);
  fd.append('from_date', fromDate);
  if (toDate) fd.append('to_date', toDate);
  try {
    var resp = await fetch('/bg-sync/start', {method: 'POST', body: fd});
    var data = await resp.json();
    if (!data.ok) { syncToast('\u274c 시작 실패: ' + (data.error || '오류'), 'error'); return; }
    _bgCurrentSource = source;
    syncToast('\u25b6 백그라운드 동기화 시작 (' + source + ')', 'success');
    bgShowProgress();
    bgStartPolling(source);
  } catch(e) {
    syncToast('\u274c 요청 실패: ' + e.message, 'error');
  }
}

function bgStartPolling(source) {
  if (_bgPollTimer) clearInterval(_bgPollTimer);
  _bgPollTimer = setInterval(function() { bgPollStatus(source); }, 3000);
  bgPollStatus(source);
}

async function bgPollStatus(source) {
  try {
    var resp = await fetch('/bg-sync/status?source=' + encodeURIComponent(source));
    var data = await resp.json();
    if (!data.active) { bgStopPolling(); bgHideProgress(); return; }
    bgUpdateUI(data);
    if (data.status === 'completed') {
      bgStopPolling();
      syncToast('\u2705 기간 동기화 완료 \u2014 활동 ' + data.synced_count + '개', 'success');
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

function bgUpdateUI(d) {
  bgShowProgress();
  var svcKor = {garmin:'Garmin', strava:'Strava', intervals:'Intervals.icu', runalyze:'Runalyze'};
  var title = document.getElementById('bg-progress-title');
  var pct = document.getElementById('bg-progress-pct');
  var bar = document.getElementById('bg-progress-bar');
  var detail = document.getElementById('bg-progress-detail');
  var rateInfo = document.getElementById('bg-rate-info');
  var errInfo = document.getElementById('bg-error-info');
  var btnPause = document.getElementById('bg-btn-pause');
  var btnStop = document.getElementById('bg-btn-stop');
  var btnResume = document.getElementById('bg-btn-resume');

  var svcName = svcKor[d.service] || d.service;
  var statusKor = {running:'동기화 중', paused:'일시중지', stopped:'중지됨',
                   rate_limited:'API 한도 대기', completed:'완료', pending:'대기 중'};
  if (title) title.textContent = svcName + ' \u2014 ' + (statusKor[d.status] || d.status);
  if (pct) pct.textContent = d.progress_pct + '% (' + d.completed_days + '/' + d.total_days + '일)';
  if (bar) bar.style.width = d.progress_pct + '%';

  var detailTxt = '';
  if (d.current_from && d.current_to) {
    detailTxt = '\ud604\uc7ac: ' + d.current_from + ' ~ ' + d.current_to;
  }
  detailTxt += ' \u00a0|\u00a0 \uc644\ub8cc: ' + d.synced_count + '\uac1c \ud65c\ub3d9';
  if (detail) detail.textContent = detailTxt;

  // API 요청 현황
  var rateTxt = 'API \uc694\uccad: \uc774\ubc88 \uc791\uc5c5 ' + d.req_count + '\ud68c'
    + ' | 15\ubd84 \ud55c\ub3c4 ' + d.rate_limit_15min + '\ud68c / \uc77c\uc77c ' + d.rate_limit_daily + '\ud68c';
  if (d.retry_after_sec && d.retry_after_sec > 0) {
    var mins = Math.ceil(d.retry_after_sec / 60);
    rateTxt += ' \u2014 \u231b ' + mins + '\ubd84 \ud6c4 \uc7ac\uac1c';
  }
  if (rateInfo) rateInfo.textContent = rateTxt;

  // 오류 표시
  if (d.last_error && d.status !== 'rate_limited') {
    if (errInfo) { errInfo.textContent = '\u26a0\ufe0f ' + d.last_error; errInfo.style.display = 'block'; }
  } else {
    if (errInfo) errInfo.style.display = 'none';
  }

  // 버튼 상태
  var isRunning = d.status === 'running' || d.status === 'pending';
  var isPaused = d.status === 'paused' || d.status === 'stopped';
  var isRateLimited = d.status === 'rate_limited';
  if (btnPause) btnPause.style.display = isRunning ? 'inline-block' : 'none';
  if (btnStop) btnStop.style.display = (isRunning || isPaused) ? 'inline-block' : 'none';
  if (btnResume) {
    btnResume.style.display = (isPaused || isRateLimited) ? 'inline-block' : 'none';
    btnResume.disabled = isRateLimited && d.retry_after_sec > 0;
    btnResume.title = isRateLimited ? 'API \ud55c\ub3c4 \ud574\uc81c \ud6c4 \uc0ac\uc6a9 \uac00\ub2a5' : '';
  }
}

async function bgSyncPause() {
  if (!_bgCurrentSource) return;
  var fd = new FormData(); fd.append('source', _bgCurrentSource);
  await fetch('/bg-sync/pause', {method: 'POST', body: fd});
}

async function bgSyncStop() {
  if (!_bgCurrentSource) return;
  var fd = new FormData(); fd.append('source', _bgCurrentSource);
  await fetch('/bg-sync/stop', {method: 'POST', body: fd});
  bgStopPolling();
}

async function bgSyncResume() {
  if (!_bgCurrentSource) return;
  var fd = new FormData(); fd.append('source', _bgCurrentSource);
  var resp = await fetch('/bg-sync/resume', {method: 'POST', body: fd});
  var data = await resp.json();
  if (data.ok) { syncToast('\u25b6 동기화 재개', 'success'); bgStartPolling(_bgCurrentSource); }
  else { syncToast('\u274c 재개 실패', 'error'); }
}

// 페이지 로드 시 활성 BG 작업 복구 (새로고침 후에도 진행 표시)
(function() {
  var sources = ['garmin', 'strava', 'intervals', 'runalyze'];
  sources.forEach(function(src) {
    fetch('/bg-sync/status?source=' + src).then(function(r) { return r.json(); }).then(function(d) {
      if (d.active && d.status !== 'completed' && d.status !== 'stopped') {
        _bgCurrentSource = src;
        bgUpdateUI(d);
        if (d.status === 'running' || d.status === 'rate_limited') bgStartPolling(src);
      }
    }).catch(function(){});
  });
})();
"""


def html_page(title: str, body: str) -> str:
    """전체 HTML 페이지 생성 (스티키 헤더 + 그룹 드롭다운 nav 포함)."""
    nav_html = _build_nav()
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_html.escape(title)} — RunPulse</title>
  <style>{_CSS}</style>
</head>
<body>
  <header>
    <a class="brand" href="/">RunPulse</a>
    <nav>{nav_html}</nav>
  </header>
  <main>
    <h1>{_html.escape(title)}</h1>
    {body}
  </main>
  <script>{_SYNC_JS}</script>
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

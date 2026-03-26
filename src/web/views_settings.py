"""서비스 연동 설정 뷰 — Blueprint.

/settings            : 전체 연동 상태 개요
/connect/garmin      : Garmin 연동 폼 (이메일/패스워드 → 토큰 저장)
/connect/garmin/mfa  : Garmin MFA 코드 입력 (2단계 로그인)
/connect/strava      : Strava OAuth2 시작 (→ strava.com 리다이렉트)
/connect/strava/callback : OAuth2 콜백 (code → token 교환 → 저장)
/connect/intervals   : Intervals.icu API 키 폼 (저장 + 연결 테스트)
/connect/runalyze    : Runalyze 토큰 폼 (저장 + 연결 테스트)
/connect/{service}/disconnect : 서비스 연동 해제
"""
from __future__ import annotations

import html as _html
import urllib.parse
import uuid
from pathlib import Path

import sqlite3

from flask import Blueprint, redirect, render_template, request, url_for

from src.sync.garmin import check_garmin_connection, _tokenstore_path
from src.sync.strava import check_strava_connection
from src.sync.intervals import check_intervals_connection
from src.sync.runalyze import check_runalyze_connection
from src.utils.config import load_config, update_service_config, save_config
from .helpers import db_path, metric_row, score_badge, last_sync_info
from .views_settings_hub import render_sync_overview, render_system_info

settings_bp = Blueprint("settings", __name__)

# Garmin MFA 대기 세션 (key → {mfa_needed, event, holder, result, email, tokenstore})
_pending_mfa: dict = {}


def _garmin_token_status_html(tokenstore) -> str:
    """garth 토큰 파일 존재·만료 여부를 HTML 배지로 반환."""
    oauth2_file = tokenstore / "oauth2_token.json"
    if not tokenstore.exists():
        return "<span class='score-badge grade-poor'>토큰 없음 — 로그인 필요</span>"
    if not oauth2_file.exists():
        return "<span class='score-badge grade-moderate'>디렉터리 존재, 토큰 파일 없음 — 로그인 필요</span>"
    try:
        import garth as _garth
        g = _garth.Client()
        g.load(str(tokenstore))
        tok = g.oauth2_token
        if tok is None:
            return "<span class='score-badge grade-poor'>토큰 파일 손상</span>"
        if tok.refresh_expired:
            return "<span class='score-badge grade-poor'>토큰 만료 — 재로그인 필요</span>"
        if tok.expired:
            return "<span class='score-badge grade-moderate'>access_token 만료 (refresh 유효, sync 시 자동 갱신)</span>"
        return "<span class='score-badge grade-good'>토큰 유효 ✓</span>"
    except Exception as e:
        return f"<span class='score-badge grade-poor'>토큰 읽기 실패: {_html.escape(str(e)[:60])}</span>"

# Strava OAuth2 설정
_STRAVA_AUTH_URL = "https://www.strava.com/oauth/authorize"
_STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"
_STRAVA_SCOPE = "read,activity:read_all"
_STRAVA_REDIRECT_PATH = "/connect/strava/callback"


# ── 상태 배지 렌더링 ────────────────────────────────────────────────
def _status_badge(ok: bool, status: str) -> str:
    """연결 상태 배지 HTML."""
    cls = "grade-good" if ok else "grade-poor"
    return f"<span class='score-badge {cls}'>{_html.escape(status)}</span>"


def _service_card(
    name: str,
    icon: str,
    status: dict,
    connect_url: str,
    disconnect_url: str | None = None,
    extra_html: str = "",
    last_sync: str | None = None,
) -> str:
    """서비스 연동 상태 카드 HTML."""
    badge = _status_badge(status["ok"], status["status"])
    detail = _html.escape(status.get("detail", ""))
    connect_label = "재연동" if status["ok"] else "연동하기"
    disconnect_btn = ""
    if disconnect_url and status["ok"]:
        disconnect_btn = (
            f"<form method='post' action='{disconnect_url}' style='display:inline'>"
            f"<button type='submit' style='margin-left:0.5rem; background:#fdd; border:1px solid #c00; border-radius:4px; padding:0.2rem 0.6rem; cursor:pointer;'>연동 해제</button>"
            f"</form>"
        )
    sync_html = (
        f"<p class='muted' style='font-size:0.8rem;margin:0.3rem 0 0;'>"
        f"마지막 동기화: {_html.escape(last_sync)}</p>"
        if last_sync else
        "<p class='muted' style='font-size:0.8rem;margin:0.3rem 0 0;'>동기화 기록 없음</p>"
    )
    return f"""
<div class='card'>
  <h2>{_html.escape(icon)} {_html.escape(name)}</h2>
  <p>{badge} <small class='muted'>{detail}</small></p>
  {sync_html}
  <div style='margin-top:0.6rem;'>
    <a href='{connect_url}'>
      <button style='padding:0.4rem 1rem; cursor:pointer;'>{connect_label}</button>
    </a>
    {disconnect_btn}
  </div>
  {extra_html}
</div>"""


def _estimate_profile() -> dict:
    """DB에서 사용자 프로필 추정값 계산."""
    import sqlite3
    from .helpers import db_path
    est: dict = {}
    try:
        dbp = db_path()
        if not dbp or not dbp.exists():
            return est
        with sqlite3.connect(str(dbp)) as conn:
            # 최대 HR: 전체 활동 중 최고 max_hr
            row = conn.execute("SELECT MAX(max_hr) FROM activity_summaries WHERE max_hr IS NOT NULL").fetchone()
            if row and row[0]:
                est["max_hr"] = int(row[0])
            # eFTP: computed_metrics에서
            row = conn.execute(
                "SELECT metric_value FROM computed_metrics WHERE metric_name='eFTP' "
                "AND activity_id IS NULL AND metric_value IS NOT NULL ORDER BY date DESC LIMIT 1"
            ).fetchone()
            if row and row[0]:
                est["eftp"] = int(row[0])
            # 주간 평균 거리: 최근 4주
            from datetime import date, timedelta
            start = (date.today() - timedelta(weeks=4)).isoformat()
            row = conn.execute(
                "SELECT COALESCE(SUM(distance_km), 0) FROM v_canonical_activities "
                "WHERE activity_type='running' AND DATE(start_time) >= ?",
                (start,),
            ).fetchone()
            if row and row[0]:
                est["weekly_km"] = round(float(row[0]) / 4, 1)
    except Exception:
        pass
    return est


def _render_user_profile_section(config: dict) -> str:
    """사용자 프로필 설정 섹션 + RunPulse 추정값."""
    u = config.get("user", {})
    max_hr = u.get("max_hr", 190)
    thr_pace = u.get("threshold_pace", 300)
    weekly_km = u.get("weekly_distance_target", 40.0)
    # threshold_pace: sec/km → mm:ss 표시
    thr_mm = int(thr_pace) // 60
    thr_ss = int(thr_pace) % 60

    # RunPulse 추정값
    est = _estimate_profile()
    est_parts = []
    if est.get("max_hr"):
        est_parts.append(f"최대HR <strong>{est['max_hr']}</strong>bpm")
    if est.get("eftp"):
        m, s = divmod(est["eftp"], 60)
        est_parts.append(f"역치 <strong>{m}:{s:02d}</strong>/km")
    if est.get("weekly_km"):
        est_parts.append(f"주간 <strong>{est['weekly_km']:.1f}</strong>km")
    est_note = (
        "<p style='font-size:0.8rem;color:var(--cyan);margin:0 0 0.6rem;'>"
        f"📊 RunPulse 추정: {' · '.join(est_parts)}</p>"
    ) if est_parts else ""

    return f"""
<div class='card'>
  <h2 style='margin-bottom:0.5rem;'>사용자 프로필</h2>
  {est_note}
  <form method='post' action='/settings/profile'
        style='display:grid;grid-template-columns:1fr 1fr;gap:0.8rem 1.5rem;'>
    <label style='display:flex;flex-direction:column;gap:0.3rem;font-size:0.88rem;'>
      최대 심박수 (bpm)
      <input type='number' name='max_hr' value='{max_hr}' min='120' max='230'
             style='padding:0.4rem;border-radius:4px;border:1px solid rgba(255,255,255,0.2);background:rgba(255,255,255,0.07);color:inherit;width:100%;'>
    </label>
    <label style='display:flex;flex-direction:column;gap:0.3rem;font-size:0.88rem;'>
      주간 목표 거리 (km)
      <input type='number' name='weekly_km' value='{weekly_km}' min='1' max='300' step='0.5'
             style='padding:0.4rem;border-radius:4px;border:1px solid rgba(255,255,255,0.2);background:rgba(255,255,255,0.07);color:inherit;width:100%;'>
    </label>
    <label style='display:flex;flex-direction:column;gap:0.3rem;font-size:0.88rem;'>
      역치 페이스 (분)
      <input type='number' name='threshold_pace_min' value='{thr_mm}' min='2' max='10'
             style='padding:0.4rem;border-radius:4px;border:1px solid rgba(255,255,255,0.2);background:rgba(255,255,255,0.07);color:inherit;width:100%;'>
    </label>
    <label style='display:flex;flex-direction:column;gap:0.3rem;font-size:0.88rem;'>
      역치 페이스 (초)
      <input type='number' name='threshold_pace_sec' value='{thr_ss}' min='0' max='59'
             style='padding:0.4rem;border-radius:4px;border:1px solid rgba(255,255,255,0.2);background:rgba(255,255,255,0.07);color:inherit;width:100%;'>
    </label>
    <div style='grid-column:1/-1;'>
      <button type='submit'
              style='padding:0.45rem 1.4rem;background:var(--cyan);color:#000;border:none;border-radius:4px;cursor:pointer;font-weight:bold;'>
        저장
      </button>
    </div>
  </form>
</div>"""


def _render_mapbox_section(config: dict) -> str:
    """지도 설정 섹션 (Leaflet + OSM)."""
    return """
<div class='card'>
  <h2 style='margin-bottom:0.5rem;'>지도 설정</h2>
  <p style='font-size:0.82rem;margin-bottom:0.4rem;'>
    <span style='color:var(--green);font-weight:600;'>✓ Leaflet + OpenStreetMap</span> 사용 중
  </p>
  <p class='muted' style='font-size:0.8rem;margin:0;'>
    활동 상세 페이지에서 GPS 경로 지도를 표시합니다. API 키 없이 무료로 동작합니다.
  </p>
</div>"""


def _render_ai_section(config: dict) -> str:
    """AI 코치 설정 섹션."""
    ai_cfg = config.get("ai", {})
    provider = ai_cfg.get("provider", "rule")
    claude_key = ai_cfg.get("claude_api_key", "")
    openai_key = ai_cfg.get("openai_api_key", "")
    claude_masked = "****" + claude_key[-6:] if len(claude_key) > 10 else ("설정됨" if claude_key else "미설정")
    openai_masked = "****" + openai_key[-6:] if len(openai_key) > 10 else ("설정됨" if openai_key else "미설정")

    provider_options = ""
    for val, label in [("rule", "규칙 기반 (API 불필요)"), ("claude", "Claude (Anthropic)"), ("openai", "ChatGPT (OpenAI)")]:
        sel = " selected" if val == provider else ""
        provider_options += f"<option value='{val}'{sel}>{label}</option>"

    return f"""
<div class='card'>
  <h2 style='margin-bottom:0.5rem;'>AI 코치 설정</h2>
  <p class='muted' style='font-size:0.82rem;margin-bottom:0.8rem;'>
    AI 코치 채팅에 사용할 AI 제공자를 선택합니다.
    규칙 기반은 API 키 없이 메트릭 데이터로 답변합니다.
  </p>
  <form method='post' action='/settings/ai' style='display:flex;flex-direction:column;gap:0.6rem;'>
    <label style='font-size:0.88rem;'>
      AI 제공자
      <select name='ai_provider' style='display:block;margin-top:0.2rem;padding:0.4rem;border-radius:4px;
        border:1px solid rgba(255,255,255,0.2);background:rgba(255,255,255,0.07);color:inherit;width:100%;'>
        {provider_options}
      </select>
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


# ── /settings — 전체 연동 상태 페이지 ──────────────────────────────
@settings_bp.get("/settings")
def settings_view() -> str:
    """서비스 연동 + 사용자 프로필 설정 허브."""
    config = load_config()

    garmin_status = check_garmin_connection(config)
    strava_status = check_strava_connection(config)
    intervals_status = check_intervals_connection(config)
    runalyze_status = check_runalyze_connection(config)

    tokenstore = _tokenstore_path(config)
    garmin_extra = f"<p class='muted' style='font-size:0.82rem;margin-top:0.3rem;'>토큰: <code>{_html.escape(str(tokenstore))}</code></p>"

    sync = last_sync_info(["garmin", "strava", "intervals", "runalyze"])

    msg = _html.escape(request.args.get("msg", ""))
    msg_html = f"<div class='card' style='border-color:#4caf50;'><p>{msg}</p></div>" if msg else ""

    statuses = {
        "garmin": garmin_status, "strava": strava_status,
        "intervals": intervals_status, "runalyze": runalyze_status,
    }
    sync_overview = render_sync_overview(statuses, sync)
    system_info = render_system_info(config)

    body = f"""
{msg_html}
{sync_overview}
<h2 style='margin:0.5rem 0 0.8rem;font-size:1rem;color:var(--muted);'>데이터 소스 연동</h2>
<div class='cards-row'>
  {_service_card("Garmin Connect", "⌚", garmin_status,
                 "/connect/garmin", "/connect/garmin/disconnect", garmin_extra,
                 last_sync=sync.get("garmin"))}
  {_service_card("Strava", "🏃", strava_status,
                 "/connect/strava", "/connect/strava/disconnect",
                 last_sync=sync.get("strava"))}
</div>
<div class='cards-row'>
  {_service_card("Intervals.icu", "📊", intervals_status,
                 "/connect/intervals", "/connect/intervals/disconnect",
                 last_sync=sync.get("intervals"))}
  {_service_card("Runalyze", "📈", runalyze_status,
                 "/connect/runalyze", "/connect/runalyze/disconnect",
                 last_sync=sync.get("runalyze"))}
</div>
{_render_user_profile_section(config)}
{_render_mapbox_section(config)}
{_render_ai_section(config)}
<hr>
<div class='card'>
  <h2>Strava 아카이브 임포트</h2>
  <p>Strava에서 내보낸 zip 파일을 임포트하거나, 기존 활동에 FIT/GPX 파일을 재연결합니다.<br>
  <small class='muted'>Settings → 데이터 내보내기(Export your data)에서 다운로드한 zip 파일을 사용합니다.</small></p>
  <a href='/import/strava-archive'>
    <button style='padding:0.4rem 1.2rem;background:var(--cyan);color:#000;border:none;border-radius:4px;cursor:pointer;font-weight:bold;'>
      아카이브 임포트
    </button>
  </a>
</div>
<div class='card' id='metrics-section'>
  <h2>메트릭 재계산</h2>
  <p>기존 DB 데이터를 기반으로 2차 메트릭(UTRS, CIRS, FEARP, RTTI, WLEI, TPDI 등)을 재계산합니다.<br>
  <small class='muted'>동기화 후 자동으로 실행되지만, 수동으로 강제 재계산할 때 사용합니다.</small></p>
  <form id='recompute-form' style='display:flex; align-items:center; gap:1rem; flex-wrap:wrap;'>
    <label>최근 <input type='number' id='recompute-days' value='90' min='1' max='365'
           style='width:60px; text-align:center;'> 일간 재계산</label>
    <button type='button' id='recompute-btn' onclick='startRecompute()'
      style='padding:0.4rem 1.2rem; background:#00d4ff; color:#000; border:none; border-radius:4px; cursor:pointer; font-weight:bold;'>
      재계산 시작
    </button>
  </form>
  <!-- 진행 섹션 -->
  <div id='recompute-progress' style='display:none; margin-top:1rem;'>
    <div style='display:flex; justify-content:space-between; font-size:0.85rem; margin-bottom:4px;'>
      <span id='recompute-status-text' style='color:var(--cyan);'>계산 중...</span>
      <span id='recompute-pct-text' style='color:var(--muted);'>0%</span>
    </div>
    <div style='background:var(--row-border); border-radius:4px; height:10px; overflow:hidden;'>
      <div id='recompute-bar' style='height:100%; background:#00d4ff; border-radius:4px; width:0%; transition:width 0.5s;'></div>
    </div>
    <div style='display:flex; justify-content:space-between; margin:0.4rem 0 0;'>
      <span id='recompute-detail' style='font-size:0.78rem; color:var(--muted);'></span>
      <span id='recompute-eta' style='font-size:0.78rem; color:var(--muted);'></span>
    </div>
  </div>
</div>
""" + """
<script>
function fmtEta(sec) {
  if (!sec || sec <= 0) return '';
  if (sec < 60) return Math.ceil(sec) + '초 남음';
  var m = Math.floor(sec / 60), s = Math.ceil(sec % 60);
  return m + '분 ' + (s > 0 ? s + '초' : '') + ' 남음';
}
function startRecompute() {
  var days = document.getElementById('recompute-days').value || 90;
  var btn = document.getElementById('recompute-btn');
  var startTime = Date.now() / 1000;
  btn.disabled = true; btn.textContent = '재계산 중...';
  document.getElementById('recompute-progress').style.display = 'block';
  document.getElementById('recompute-bar').style.width = '0%';
  document.getElementById('recompute-pct-text').textContent = '0%';
  document.getElementById('recompute-status-text').textContent = '시작 중...';
  document.getElementById('recompute-detail').textContent = '';
  document.getElementById('recompute-eta').textContent = '';

  // POST 시작
  var fd = new FormData(); fd.append('days', days);
  fetch('/metrics/recompute', {method:'POST', body:fd}).then(function() {
    // SSE 연결
    var es = new EventSource('/metrics/recompute-stream');
    es.onmessage = function(e) {
      var d = JSON.parse(e.data);
      var bar = document.getElementById('recompute-bar');
      var pct = d.pct || 0;
      if (bar) bar.style.width = pct + '%';
      var pctEl = document.getElementById('recompute-pct-text');
      if (pctEl) pctEl.textContent = pct + '%  (' + (d.completed||0) + '/' + (d.total||0) + '일)';
      var etaEl = document.getElementById('recompute-eta');
      var statusEl = document.getElementById('recompute-status-text');
      if (d.status === 'running') {
        if (statusEl) statusEl.textContent = '계산 중... ' + (d.current_date || '');
        var detailEl = document.getElementById('recompute-detail');
        if (detailEl) detailEl.textContent = d.current_date ? (d.current_date + ' 처리 완료') : '';
        // ETA 계산
        var completed = d.completed || 0, total = d.total || 0;
        if (completed > 0 && total > completed) {
          var elapsed = (d.started_at ? Date.now()/1000 - d.started_at : Date.now()/1000 - startTime);
          var remaining = (elapsed / completed) * (total - completed);
          if (etaEl) etaEl.textContent = fmtEta(remaining);
        }
      } else if (d.status === 'completed') {
        if (etaEl) etaEl.textContent = '';
        if (statusEl) { statusEl.textContent = '✅ 재계산 완료'; statusEl.style.color = 'var(--green)'; }
        if (bar) bar.style.background = 'var(--green)';
        btn.disabled = false; btn.textContent = '재계산 시작';
        es.close();
      } else if (d.status === 'error') {
        if (statusEl) { statusEl.textContent = '❌ 오류: ' + (d.error||''); statusEl.style.color = 'var(--red)'; }
        btn.disabled = false; btn.textContent = '재계산 시작';
        es.close();
      } else if (d.status === 'idle') {
        es.close();
      }
    };
    es.onerror = function() {
      // SSE 오류 시 폴링으로 fallback
      es.close();
      pollRecomputeStatus(btn);
    };
  }).catch(function(err) {
    document.getElementById('recompute-status-text').textContent = '❌ 요청 실패';
    btn.disabled = false; btn.textContent = '재계산 시작';
  });
}

function pollRecomputeStatus(btn) {
  var timer = setInterval(function() {
    fetch('/metrics/recompute-status').then(function(r){return r.json();}).then(function(d) {
      var pct = d.pct || 0;
      var bar = document.getElementById('recompute-bar');
      if (bar) bar.style.width = pct + '%';
      var pctEl = document.getElementById('recompute-pct-text');
      if (pctEl) pctEl.textContent = pct + '%';
      if (d.status === 'completed' || d.status === 'error' || d.status === 'idle') {
        clearInterval(timer);
        if (btn) { btn.disabled = false; btn.textContent = '재계산 시작'; }
      }
    }).catch(function(){ clearInterval(timer); });
  }, 1500);
}

// 페이지 로드 시 이미 진행 중이면 복구
(function() {
  fetch('/metrics/recompute-status').then(function(r){return r.json();}).then(function(d) {
    if (d.status === 'running') {
      document.getElementById('recompute-progress').style.display = 'block';
      var btn = document.getElementById('recompute-btn');
      if (btn) { btn.disabled = true; btn.textContent = '재계산 중...'; }
      var es = new EventSource('/metrics/recompute-stream');
      es.onmessage = function(e) {
        var d2 = JSON.parse(e.data);
        var bar = document.getElementById('recompute-bar');
        if (bar) bar.style.width = (d2.pct||0) + '%';
        if (d2.status !== 'running') { es.close(); if(btn){btn.disabled=false;btn.textContent='재계산 시작';} }
      };
      es.onerror = function(){ es.close(); };
    }
  }).catch(function(){});
})();
</script>
{system_info}
<p class='muted' style='font-size:0.85rem;'>
  연동 정보는 <code>config.json</code>에 저장됩니다. Garmin 토큰은 로컬 tokenstore에 별도 저장됩니다.
</p>"""
    return render_template("generic_page.html", title="서비스 연동 설정", body=body, active_tab="settings")


# ── Garmin 연동 ─────────────────────────────────────────────────────
@settings_bp.get("/connect/garmin")
def garmin_connect_view() -> str:
    """Garmin 연동 폼."""
    config = load_config()
    garmin_cfg = config.get("garmin", {})
    tokenstore = _tokenstore_path(config)
    current_email = _html.escape(garmin_cfg.get("email", ""))
    current_tokenstore = _html.escape(str(tokenstore))

    msg = _html.escape(request.args.get("msg", ""))
    msg_html = f"<div class='card' style='border-color:#f0c040;'><p>{msg}</p></div>" if msg else ""
    err = _html.escape(request.args.get("error", ""))
    err_html = f"<div class='card' style='border-color:#c0392b;'><p style='color:#c0392b;'>{err}</p></div>" if err else ""

    body = f"""
{err_html}{msg_html}
<div class='card'>
  <h2>Garmin Connect 연동</h2>
  <p>이메일/패스워드로 로그인하면 토큰이 로컬에 저장됩니다. 이후 재로그인 시 저장된 토큰을 우선 사용합니다.</p>
  <form method='post' action='/connect/garmin'>
    <table style='width:auto; border:none;'>
      <tr>
        <td style='border:none; padding:0.3rem 0.5rem;'><label>이메일:</label></td>
        <td style='border:none; padding:0.3rem 0.5rem;'>
          <input type='email' name='email' value='{current_email}' required style='width:260px;'>
        </td>
      </tr>
      <tr>
        <td style='border:none; padding:0.3rem 0.5rem;'><label>패스워드:</label></td>
        <td style='border:none; padding:0.3rem 0.5rem;'>
          <input type='password' name='password' placeholder='패스워드 입력' style='width:260px;'>
        </td>
      </tr>
      <tr>
        <td style='border:none; padding:0.3rem 0.5rem;'><label>토큰 저장 경로:</label></td>
        <td style='border:none; padding:0.3rem 0.5rem;'>
          <input type='text' name='tokenstore' value='{current_tokenstore}' style='width:260px;'>
          <small class='muted'>(기본: ~/.garth)</small>
        </td>
      </tr>
    </table>
    <div style='margin-top:1rem;'>
      <button type='submit' name='action' value='save'>저장만 하기</button>
      &nbsp;
      <button type='submit' name='action' value='save_and_test' style='background:#d4edff;'>저장 + 연결 테스트</button>
    </div>
  </form>
</div>
<div class='card'>
  <h3>토큰 저장소 상태</h3>
  <p>경로: <code>{current_tokenstore}</code></p>
  {_garmin_token_status_html(tokenstore)}
  <p class='muted' style='margin-top:0.5rem;'>
    <strong>MFA 흐름:</strong> "저장 + 연결 테스트" 클릭 시 토큰이 없으면 Garmin이 이메일/앱으로 인증 코드를 발송합니다.
    MFA 코드 입력 화면이 자동으로 나타납니다. 코드 입력 후 로그인이 완료되면 토큰이 저장되어 이후 sync 시 재인증 없이 사용됩니다.
  </p>
</div>"""
    return render_template("generic_page.html", title="Garmin 연동", body=body, active_tab="settings")


@settings_bp.post("/connect/garmin")
def garmin_connect_post():
    """Garmin 이메일/패스워드 저장 (+ 선택적으로 연결 테스트, MFA 2단계 지원)."""
    import threading
    import time as _time
    try:
        import garth as _garth
        from garth import sso as _sso
    except ImportError:
        _garth = None  # type: ignore[assignment]
        _sso = None  # type: ignore[assignment]

    email = request.form.get("email", "").strip()
    password = request.form.get("password", "").strip()
    tokenstore_str = request.form.get("tokenstore", "~/.garth").strip()
    action = request.form.get("action", "save")

    if not email:
        return redirect("/connect/garmin?error=" + urllib.parse.quote("이메일을 입력하세요."))

    updates: dict = {"email": email, "tokenstore": tokenstore_str}
    if password:
        updates["password"] = password
    update_service_config("garmin", updates)

    if action == "save":
        return redirect("/connect/garmin?msg=" + urllib.parse.quote("저장 완료. 다음 sync 시 자동 로그인됩니다."))

    # ── save_and_test: garth sso로 로그인 시도 ──
    if _garth is None or _sso is None:
        return redirect("/connect/garmin?error=" + urllib.parse.quote(
            "garth 라이브러리가 설치되지 않았습니다. pip install garth"))

    config = load_config()
    _pw = password or config.get("garmin", {}).get("password", "")
    if not _pw:
        return redirect("/connect/garmin?error=" + urllib.parse.quote("패스워드가 없습니다. 입력 후 다시 시도하세요."))

    tokenstore = Path(tokenstore_str).expanduser()

    try:
        g = _garth.Client()
        result = _sso.login(email, _pw, client=g, return_on_mfa=True)

        # MFA 필요한 경우
        if isinstance(result, tuple) and result[0] == "needs_mfa":
            key = str(uuid.uuid4())
            client_state = result[1]
            _pending_mfa[key] = {
                "client_state": client_state,
                "garth_client": g,
                "tokenstore": str(tokenstore),
                "email": email,
            }
            mfa_url = "/connect/garmin/mfa?" + urllib.parse.urlencode({
                "key": key,
                "tokenstore": tokenstore_str,
            })
            return redirect(mfa_url)

        # MFA 없이 성공: result는 (oauth1, oauth2) 튜플
        oauth1, oauth2 = result
        g.oauth1_token = oauth1
        g.oauth2_token = oauth2
        tokenstore.mkdir(parents=True, exist_ok=True)
        g.dump(str(tokenstore))
        return redirect("/connect/garmin?msg=" + urllib.parse.quote(
            f"연결 성공! 토큰이 {tokenstore_str}에 저장되었습니다."
        ))

    except ImportError:
        return redirect("/connect/garmin?error=" + urllib.parse.quote("garth 미설치. pip install garth"))
    except Exception as e:
        return redirect("/connect/garmin?error=" + urllib.parse.quote(f"로그인 실패: {str(e)[:200]}"))


@settings_bp.get("/connect/garmin/mfa")
def garmin_mfa_view():
    """Garmin MFA 코드 입력 폼."""
    key = request.args.get("key", "")
    tokenstore_str = request.args.get("tokenstore", "~/.garth")
    err = _html.escape(request.args.get("error", ""))
    err_html = f"<div class='card' style='border-color:#c0392b;'><p style='color:#c0392b;'>{err}</p></div>" if err else ""

    if not key or key not in _pending_mfa:
        return redirect("/connect/garmin?error=" + urllib.parse.quote(
            "MFA 세션이 만료되었거나 없습니다. 다시 시도하세요."
        ))

    body = f"""
{err_html}
<div class='card'>
  <h2>Garmin MFA 인증</h2>
  <p>Garmin 앱 또는 이메일로 전송된 6자리 인증 코드를 입력하세요.</p>
  <form method='post' action='/connect/garmin/mfa'>
    <input type='hidden' name='key' value='{_html.escape(key)}'>
    <input type='hidden' name='tokenstore' value='{_html.escape(tokenstore_str)}'>
    <table style='width:auto; border:none;'>
      <tr>
        <td style='border:none; padding:0.3rem 0.5rem;'><label>인증 코드:</label></td>
        <td style='border:none; padding:0.3rem 0.5rem;'>
          <input type='text' name='mfa_code' maxlength='8' autofocus
                 placeholder='123456' style='width:140px; font-size:1.2rem; letter-spacing:0.2rem;'>
        </td>
      </tr>
    </table>
    <div style='margin-top:1rem;'>
      <button type='submit' style='padding:0.5rem 1.5rem; font-size:1rem;'>인증 완료</button>
    </div>
  </form>
</div>
<div class='card'>
  <p class='muted'>코드를 받지 못했다면 Garmin 앱을 확인하거나 이메일을 다시 확인하세요.</p>
  <p class='muted'><a href='/connect/garmin'>← 처음부터 다시 시도</a></p>
</div>"""
    return render_template("generic_page.html", title="Garmin MFA 인증", body=body, active_tab="settings")


@settings_bp.post("/connect/garmin/mfa")
def garmin_mfa_submit():
    """Garmin MFA 코드 제출 → 로그인 완료."""
    try:
        from garth import sso as _sso
        import garth as _garth
    except ImportError:
        return redirect("/connect/garmin?error=" + urllib.parse.quote(
            "garth 라이브러리가 설치되지 않았습니다."))

    key = request.form.get("key", "")
    mfa_code = request.form.get("mfa_code", "").strip()
    tokenstore_str = request.form.get("tokenstore", "~/.garth")

    if not key or key not in _pending_mfa:
        return redirect("/connect/garmin?error=" + urllib.parse.quote("MFA 세션 만료. 다시 시도하세요."))
    if not mfa_code:
        mfa_url = "/connect/garmin/mfa?" + urllib.parse.urlencode({
            "key": key, "tokenstore": tokenstore_str, "error": "인증 코드를 입력하세요."
        })
        return redirect(mfa_url)

    pending = _pending_mfa.pop(key)
    try:
        g = pending["garth_client"]
        oauth1, oauth2 = _sso.resume_login(pending["client_state"], mfa_code)
        g.oauth1_token = oauth1
        g.oauth2_token = oauth2
        tokenstore = Path(pending["tokenstore"]).expanduser()
        tokenstore.mkdir(parents=True, exist_ok=True)
        g.dump(str(tokenstore))
        return redirect("/connect/garmin?msg=" + urllib.parse.quote(
            f"MFA 인증 성공! 토큰이 {tokenstore_str}에 저장되었습니다."
        ))
    except Exception as e:
        return redirect("/connect/garmin?error=" + urllib.parse.quote(f"MFA 인증 실패: {str(e)[:200]}"))


@settings_bp.post("/connect/garmin/disconnect")
def garmin_disconnect():
    """Garmin 연동 해제 (이메일/패스워드 삭제, tokenstore 유지)."""
    update_service_config("garmin", {"email": "", "password": ""})
    return redirect("/settings?msg=Garmin+연동+해제+완료")


# ── Strava OAuth2 연동 ──────────────────────────────────────────────
@settings_bp.get("/connect/strava")
def strava_connect_view() -> str:
    """Strava 연동 화면 — client_id/secret 입력 + OAuth 시작."""
    config = load_config()
    strava_cfg = config.get("strava", {})
    client_id = _html.escape(str(strava_cfg.get("client_id", "")))
    msg = _html.escape(request.args.get("msg", ""))
    msg_html = f"<div class='card' style='border-color:#4caf50;'><p>{msg}</p></div>" if msg else ""
    err = _html.escape(request.args.get("error", ""))
    err_html = f"<div class='card' style='border-color:#c0392b;'><p style='color:#c0392b;'>{err}</p></div>" if err else ""

    body = f"""
{err_html}{msg_html}
<div class='card'>
  <h2>Strava OAuth2 연동</h2>
  <p>Strava API 앱(client_id, client_secret)을 먼저 저장한 후 OAuth 인증을 시작하세요.</p>
  <form method='post' action='/connect/strava/save-app'>
    <table style='width:auto; border:none;'>
      <tr>
        <td style='border:none; padding:0.3rem 0.5rem;'><label>Client ID:</label></td>
        <td style='border:none; padding:0.3rem 0.5rem;'>
          <input type='text' name='client_id' value='{client_id}' required style='width:200px;'>
        </td>
      </tr>
      <tr>
        <td style='border:none; padding:0.3rem 0.5rem;'><label>Client Secret:</label></td>
        <td style='border:none; padding:0.3rem 0.5rem;'>
          <input type='password' name='client_secret' placeholder='변경하려면 입력' style='width:200px;'>
        </td>
      </tr>
    </table>
    <div style='margin-top:1rem;'>
      <button type='submit'>앱 정보 저장</button>
    </div>
  </form>
</div>
<div class='card'>
  <h3>OAuth2 인증 시작</h3>
  <p>위 앱 정보를 저장한 후 아래 버튼을 클릭하여 Strava 로그인 페이지로 이동합니다.</p>
  <a href='/connect/strava/oauth-start'>
    <button style='padding:0.4rem 1rem; background:#fc4c02; color:white; border:none; border-radius:4px; cursor:pointer;'>
      Strava로 로그인
    </button>
  </a>
  <p class='muted' style='font-size:0.85rem;'>
    콜백 URL: <code>http://localhost:18080{_STRAVA_REDIRECT_PATH}</code><br>
    Strava API 앱 설정에서 위 URL을 Authorized Callback Domain에 추가해야 합니다.
  </p>
</div>"""
    return render_template("generic_page.html", title="Strava 연동", body=body, active_tab="settings")


@settings_bp.post("/connect/strava/save-app")
def strava_save_app():
    """Strava client_id/secret 저장."""
    client_id = request.form.get("client_id", "").strip()
    client_secret = request.form.get("client_secret", "").strip()
    if not client_id:
        return redirect("/connect/strava?error=" + urllib.parse.quote("Client ID를 입력하세요."))

    updates: dict = {"client_id": client_id}
    if client_secret:
        updates["client_secret"] = client_secret
    update_service_config("strava", updates)
    return redirect("/connect/strava?msg=" + urllib.parse.quote("앱 정보 저장 완료."))


@settings_bp.get("/connect/strava/oauth-start")
def strava_oauth_start():
    """Strava OAuth2 인증 시작 — strava.com으로 리다이렉트."""
    config = load_config()
    strava_cfg = config.get("strava", {})
    client_id = strava_cfg.get("client_id", "")
    if not client_id:
        return redirect("/connect/strava?error=" + urllib.parse.quote("Client ID를 먼저 저장하세요."))

    params = {
        "client_id": client_id,
        "redirect_uri": f"http://localhost:18080{_STRAVA_REDIRECT_PATH}",
        "response_type": "code",
        "approval_prompt": "auto",
        "scope": _STRAVA_SCOPE,
    }
    auth_url = _STRAVA_AUTH_URL + "?" + urllib.parse.urlencode(params)
    return redirect(auth_url)


@settings_bp.get("/connect/strava/callback")
def strava_oauth_callback():
    """Strava OAuth2 콜백 — code → token 교환 → 저장."""
    import httpx
    error = request.args.get("error")
    if error:
        return redirect("/connect/strava?error=" + urllib.parse.quote(f"OAuth 오류: {error}"))

    code = request.args.get("code", "")
    if not code:
        return redirect("/connect/strava?error=" + urllib.parse.quote("인증 코드가 없습니다."))

    config = load_config()
    strava_cfg = config.get("strava", {})
    client_id = strava_cfg.get("client_id", "")
    client_secret = strava_cfg.get("client_secret", "")

    if not client_id or not client_secret:
        return redirect("/connect/strava?error=" + urllib.parse.quote("Client ID/Secret 미설정."))

    # authorization_code → access_token 교환
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.post(_STRAVA_TOKEN_URL, data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "grant_type": "authorization_code",
            })
            resp.raise_for_status()
            token_data = resp.json()
    except Exception as e:
        return redirect("/connect/strava?error=" + urllib.parse.quote(f"토큰 교환 실패: {e}"))

    update_service_config("strava", {
        "access_token": token_data.get("access_token", ""),
        "refresh_token": token_data.get("refresh_token", ""),
        "expires_at": token_data.get("expires_at", 0),
    })
    return redirect("/connect/strava?msg=" + urllib.parse.quote("Strava 연동 완료! 토큰이 저장되었습니다."))


@settings_bp.post("/connect/strava/disconnect")
def strava_disconnect():
    """Strava 연동 해제."""
    update_service_config("strava", {"access_token": "", "refresh_token": "", "expires_at": 0})
    return redirect("/settings")


# ── Intervals.icu 연동 ──────────────────────────────────────────────
@settings_bp.get("/connect/intervals")
def intervals_connect_view() -> str:
    """Intervals.icu API 키 입력 폼."""
    config = load_config()
    intervals_cfg = config.get("intervals", {})
    athlete_id = _html.escape(str(intervals_cfg.get("athlete_id", "")))
    msg = _html.escape(request.args.get("msg", ""))
    msg_html = f"<div class='card' style='border-color:#4caf50;'><p>{msg}</p></div>" if msg else ""
    err = _html.escape(request.args.get("error", ""))
    err_html = f"<div class='card' style='border-color:#c0392b;'><p style='color:#c0392b;'>{err}</p></div>" if err else ""

    body = f"""
{err_html}{msg_html}
<div class='card'>
  <h2>Intervals.icu 연동</h2>
  <p>
    <a href='https://intervals.icu/settings' target='_blank' rel='noopener'>
      <button style='padding:0.4rem 1rem; background:#e35300; color:#fff; border:none; border-radius:4px; cursor:pointer; margin-bottom:0.5rem;'>
        ↗ Intervals.icu 설정 페이지 열기
      </button>
    </a>
  </p>
  <p class='muted' style='font-size:0.85rem;'>설정 → Profile → API 탭 → API Key 복사 후 아래에 붙여넣으세요.</p>
  <form method='post' action='/connect/intervals'>
    <table style='width:auto; border:none;'>
      <tr>
        <td style='border:none; padding:0.3rem 0.5rem;'><label>Athlete ID:</label></td>
        <td style='border:none; padding:0.3rem 0.5rem;'>
          <input type='text' name='athlete_id' value='{athlete_id}' required
                 placeholder='예: i12345' style='width:200px;'>
          <small class='muted'>(URL의 /athlete/i12345 부분)</small>
        </td>
      </tr>
      <tr>
        <td style='border:none; padding:0.3rem 0.5rem;'><label>API Key:</label></td>
        <td style='border:none; padding:0.3rem 0.5rem;'>
          <input type='password' name='api_key' placeholder='API 키 입력' required style='width:200px;'>
        </td>
      </tr>
    </table>
    <div style='margin-top:1rem;'>
      <button type='submit' name='action' value='save'>저장만 하기</button>
      &nbsp;
      <button type='submit' name='action' value='save_and_test' style='background:#d4edff;'>저장 + 연결 테스트</button>
    </div>
  </form>
</div>"""
    return render_template("generic_page.html", title="Intervals.icu 연동", body=body, active_tab="settings")


@settings_bp.post("/connect/intervals")
def intervals_connect_post():
    """Intervals.icu API 키 저장 + 연결 테스트."""
    athlete_id = request.form.get("athlete_id", "").strip()
    api_key = request.form.get("api_key", "").strip()
    action = request.form.get("action", "save")

    if not athlete_id or not api_key:
        return redirect("/connect/intervals?error=" + urllib.parse.quote("athlete_id와 API 키를 모두 입력하세요."))

    update_service_config("intervals", {"athlete_id": athlete_id, "api_key": api_key})

    if action == "save":
        return redirect("/connect/intervals?msg=" + urllib.parse.quote("저장 완료."))

    # 연결 테스트
    config = load_config()
    result = check_intervals_connection(config)
    if result["ok"]:
        return redirect("/connect/intervals?msg=" + urllib.parse.quote(f"연결 성공: {result['detail']}"))
    return redirect("/connect/intervals?error=" + urllib.parse.quote(f"연결 실패 [{result['status']}]: {result['detail']}"))


@settings_bp.post("/connect/intervals/disconnect")
def intervals_disconnect():
    """Intervals.icu 연동 해제."""
    update_service_config("intervals", {"athlete_id": "", "api_key": ""})
    return redirect("/settings")


# ── Runalyze 연동 ───────────────────────────────────────────────────
@settings_bp.get("/connect/runalyze")
def runalyze_connect_view() -> str:
    """Runalyze 토큰 입력 폼."""
    msg = _html.escape(request.args.get("msg", ""))
    msg_html = f"<div class='card' style='border-color:#4caf50;'><p>{msg}</p></div>" if msg else ""
    err = _html.escape(request.args.get("error", ""))
    err_html = f"<div class='card' style='border-color:#c0392b;'><p style='color:#c0392b;'>{err}</p></div>" if err else ""

    body = f"""
{err_html}{msg_html}
<div class='card'>
  <h2>Runalyze 연동</h2>
  <p>
    <a href='https://runalyze.com/settings/personal-api' target='_blank' rel='noopener'>
      <button style='padding:0.4rem 1rem; background:#2980b9; color:#fff; border:none; border-radius:4px; cursor:pointer; margin-bottom:0.5rem;'>
        ↗ Runalyze API 토큰 페이지 열기
      </button>
    </a>
  </p>
  <p class='muted' style='font-size:0.85rem;'>설정 → Account → Personal API → 토큰 복사 후 아래에 붙여넣으세요.</p>
  <form method='post' action='/connect/runalyze'>
    <table style='width:auto; border:none;'>
      <tr>
        <td style='border:none; padding:0.3rem 0.5rem;'><label>API Token:</label></td>
        <td style='border:none; padding:0.3rem 0.5rem;'>
          <input type='password' name='token' placeholder='Personal API 토큰 입력' required style='width:280px;'>
        </td>
      </tr>
    </table>
    <div style='margin-top:1rem;'>
      <button type='submit' name='action' value='save'>저장만 하기</button>
      &nbsp;
      <button type='submit' name='action' value='save_and_test' style='background:#d4edff;'>저장 + 연결 테스트</button>
    </div>
  </form>
</div>
<div class='card'>
  <h3>토큰 발급 방법</h3>
  <ol>
    <li>runalyze.com에 로그인</li>
    <li>Settings → Personal API 이동</li>
    <li>"Generate new token" 클릭</li>
    <li>생성된 토큰을 위 입력창에 붙여넣기</li>
  </ol>
  <p class='muted'>토큰이 만료되거나 오류가 발생하면 Runalyze에서 재발급하세요.</p>
</div>"""
    return render_template("generic_page.html", title="Runalyze 연동", body=body, active_tab="settings")


@settings_bp.post("/connect/runalyze")
def runalyze_connect_post():
    """Runalyze 토큰 저장 + 연결 테스트."""
    token = request.form.get("token", "").strip()
    action = request.form.get("action", "save")

    if not token:
        return redirect("/connect/runalyze?error=" + urllib.parse.quote("토큰을 입력하세요."))

    update_service_config("runalyze", {"token": token})
    # 이전 403 오류로 인한 동기화 차단 해제 (새 토큰 저장 시 자동 클리어)
    from src.utils.sync_state import clear_retry_after
    clear_retry_after("runalyze")

    if action == "save":
        return redirect("/connect/runalyze?msg=" + urllib.parse.quote("저장 완료."))

    # 연결 테스트
    config = load_config()
    result = check_runalyze_connection(config)
    if result["ok"]:
        return redirect("/connect/runalyze?msg=" + urllib.parse.quote(f"연결 성공: {result['detail']}"))
    return redirect("/connect/runalyze?error=" + urllib.parse.quote(f"연결 실패 [{result['status']}]: {result['detail']}"))


@settings_bp.post("/connect/runalyze/disconnect")
def runalyze_disconnect():
    """Runalyze 연동 해제."""
    update_service_config("runalyze", {"token": ""})
    return redirect("/settings")


# ── 메트릭 재계산 ────────────────────────────────────────────────────

# 재계산 진행 상태 (스레드 안전 — 단일 딕셔너리 교체)
import threading as _threading
_recompute_state: dict = {"status": "idle"}
_recompute_lock = _threading.Lock()


def _set_recompute_state(**kwargs) -> None:
    with _recompute_lock:
        _recompute_state.update(kwargs)


@settings_bp.post("/metrics/recompute")
def metrics_recompute():
    """기존 DB 데이터 기반 2차 메트릭 일괄 재계산 (백그라운드 + SSE 진행)."""
    from src.metrics import engine as metrics_engine

    with _recompute_lock:
        if _recompute_state.get("status") == "running":
            return redirect("/settings?msg=재계산이 이미 진행 중입니다.")

    try:
        days = int(request.form.get("days", 90))
        days = max(1, min(days, 365))
    except (ValueError, TypeError):
        days = 90

    import time as _time
    _set_recompute_state(status="running", days=days, completed=0, total=days,
                         current_date="", pct=0, error=None,
                         started_at=_time.time())

    def _on_progress(date_str: str, completed: int, total: int) -> None:
        pct = round(completed / total * 100, 1) if total > 0 else 0
        _set_recompute_state(completed=completed, total=total,
                             current_date=date_str, pct=pct)

    def _run() -> None:
        try:
            with sqlite3.connect(str(db_path())) as conn:
                metrics_engine.recompute_all(conn, days=days, on_progress=_on_progress)
            _set_recompute_state(status="completed", pct=100)
        except Exception as exc:
            _set_recompute_state(status="error", error=str(exc)[:200])

    _threading.Thread(target=_run, daemon=True, name="metrics-recompute").start()
    return redirect("/settings#metrics-section")


@settings_bp.get("/metrics/recompute-stream")
def metrics_recompute_stream():
    """메트릭 재계산 진행 상황 SSE 스트림."""
    import json
    import time
    from flask import Response, stream_with_context

    def _generate():
        while True:
            with _recompute_lock:
                state = dict(_recompute_state)
            data = json.dumps(state)
            yield f"data: {data}\n\n"
            if state.get("status") in ("completed", "error", "idle"):
                break
            time.sleep(0.8)

    return Response(
        stream_with_context(_generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@settings_bp.get("/metrics/recompute-status")
def metrics_recompute_status():
    """재계산 현재 상태 JSON (폴링 fallback용)."""
    from flask import jsonify
    with _recompute_lock:
        return jsonify(dict(_recompute_state))


# ── 사용자 프로필 저장 ────────────────────────────────────────────────
@settings_bp.post("/settings/profile")
def settings_profile_post():
    """사용자 프로필 설정(max_hr, threshold_pace, weekly_km) 저장."""
    try:
        max_hr = int(request.form.get("max_hr", 190))
        weekly_km = float(request.form.get("weekly_km", 40.0))
        thr_min = int(request.form.get("threshold_pace_min", 5))
        thr_sec = int(request.form.get("threshold_pace_sec", 0))
        threshold_pace = thr_min * 60 + thr_sec
    except (ValueError, TypeError):
        return redirect("/settings?msg=입력값이 올바르지 않습니다")

    config = load_config()
    config.setdefault("user", {})
    config["user"]["max_hr"] = max_hr
    config["user"]["weekly_distance_target"] = weekly_km
    config["user"]["threshold_pace"] = threshold_pace
    save_config(config)
    return redirect("/settings?msg=프로필이 저장되었습니다")


# ── AI 설정 저장 ─────────────────────────────────────────────────────
@settings_bp.post("/settings/ai")
def settings_ai_post():
    """AI 코치 설정 저장."""
    config = load_config()
    config.setdefault("ai", {})
    provider = (request.form.get("ai_provider") or "rule").strip()
    config["ai"]["provider"] = provider
    claude_key = (request.form.get("claude_api_key") or "").strip()
    if claude_key:
        config["ai"]["claude_api_key"] = claude_key
    openai_key = (request.form.get("openai_api_key") or "").strip()
    if openai_key:
        config["ai"]["openai_api_key"] = openai_key
    save_config(config)
    msg = f"AI 설정 저장됨 (제공자: {provider})"
    return redirect(f"/settings?msg={msg}")


# ── Mapbox 토큰 저장 ─────────────────────────────────────────────────
@settings_bp.post("/settings/mapbox")
def settings_mapbox_post():
    """Mapbox access token 저장."""
    token = (request.form.get("mapbox_token") or "").strip()
    config = load_config()
    config.setdefault("mapbox", {})
    config["mapbox"]["token"] = token
    save_config(config)
    msg = "Mapbox 토큰이 저장되었습니다" if token else "Mapbox 토큰이 제거되었습니다"
    return redirect(f"/settings?msg={msg}")

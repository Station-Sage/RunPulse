"""서비스 연동 설정 뷰 — 메인 허브 + 설정 저장 라우트.

분리된 하위 모듈:
  views_settings_render.py       — 서비스 카드/프로필/Mapbox/CalDAV 렌더러
  views_settings_render_prefs.py — 훈련환경설정/AI/프롬프트 렌더러
  views_settings_garmin.py       — Garmin 연동 라우트 (settings_garmin_bp)
  views_settings_integrations.py — Strava/Intervals/Runalyze 라우트 (settings_integrations_bp)
  views_settings_metrics.py      — 메트릭 재계산 라우트 (settings_metrics_bp)
"""
from __future__ import annotations

import html as _html
import sqlite3

from flask import Blueprint, redirect, render_template, request

from src.sync.garmin import check_garmin_connection, _tokenstore_path
from src.sync.strava import check_strava_connection
from src.sync.intervals import check_intervals_connection
from src.sync.runalyze import check_runalyze_connection
from src.utils.config import load_config, save_config, update_service_config
from src.web.helpers import db_path, last_sync_info
from src.web.views_settings_hub import render_sync_overview, render_system_info
from src.web.views_settings_render import (
    _service_card, _render_user_profile_section,
    _render_mapbox_section, _render_caldav_section,
)
from src.web.views_settings_render_prefs import (
    _render_ai_section, _render_prompt_management,
)

settings_bp = Blueprint("settings", __name__)


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
<div class='card' style='display:flex;justify-content:space-between;align-items:center;'>
  <div>
    <h2 style='margin:0;font-size:1rem;'>동기화 · 서비스 연결</h2>
    <p class='muted' style='margin:0.3rem 0 0;font-size:0.82rem;'>데이터 동기화, 서비스 연동, 임포트는 동기화 탭에서 관리합니다.</p>
  </div>
  <a href='/sync' style='background:var(--cyan);color:#000;padding:0.4rem 1.2rem;
     border-radius:8px;font-weight:600;font-size:0.85rem;text-decoration:none;'>🔄 동기화 탭</a>
</div>
{_render_user_profile_section(config)}
<div class='card' style='border-left:4px solid var(--cyan);'>
  <h2 style='margin:0 0 0.5rem;font-size:0.95rem;'>훈련 환경 설정</h2>
  <p class='muted' style='font-size:0.85rem;margin:0 0 0.8rem;'>
    휴식 요일, 롱런 요일, 인터벌 거리 등 훈련 설정은 훈련 탭으로 이동했습니다.
  </p>
  <a href='/training#training-prefs-details'
    style='background:var(--cyan);color:#000;padding:0.4rem 1.2rem;
           border-radius:8px;font-weight:600;font-size:0.85rem;text-decoration:none;
           display:inline-block;'>
    ⚙️ 훈련 환경 설정 바로가기
  </a>
</div>
{_render_mapbox_section(config)}
{_render_ai_section(config)}
{_render_prompt_management(config)}
{_render_caldav_section(config)}
<div class='card' id='metrics-section'>
  <h2>메트릭 재계산</h2>
  <p>기존 DB 데이터를 기반으로 2차 메트릭(UTRS, CIRS, FEARP, RTTI, WLEI, TPDI 등)을 재계산합니다.<br>
  <small class='muted'>동기화 후 자동으로 실행되지만, 수동으로 강제 재계산할 때 사용합니다.</small></p>
  <form id='recompute-form' style='display:flex; align-items:center; gap:1rem; flex-wrap:wrap;'>
    <label>최근 <input type='number' id='recompute-days' value='90' min='1'
           style='width:60px; text-align:center;'> 일간 재계산</label>
    <button type='button' id='recompute-btn' onclick='startRecompute()'
      style='padding:0.4rem 1.2rem; background:#00d4ff; color:#000; border:none; border-radius:4px; cursor:pointer; font-weight:bold;'>
      재계산 시작
    </button>
    <button type='button' onclick='document.getElementById("recompute-days").value=0; startRecompute()'
      style='padding:0.4rem 1.2rem; background:rgba(255,255,255,0.1); color:var(--muted); border:1px solid var(--card-border); border-radius:4px; cursor:pointer;'>
      전체 기간
    </button>
  </form>
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
  var fd = new FormData(); fd.append('days', days);
  fetch('/metrics/recompute', {method:'POST', body:fd}).then(function() {
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
      } else if (d.status === 'idle') { es.close(); }
    };
    es.onerror = function() { es.close(); pollRecomputeStatus(btn); };
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
""" + f"""
{system_info}
<p class='muted' style='font-size:0.85rem;'>
  연동 정보는 <code>config.json</code>에 저장됩니다. Garmin 토큰은 로컬 tokenstore에 별도 저장됩니다.
</p>"""
    return render_template("generic_page.html", title="서비스 연동 설정", body=body, active_tab="settings")


# ── 설정 저장 라우트 ────────────────────────────────────────────────────

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


@settings_bp.post("/settings/training-prefs")
def settings_training_prefs_post():
    """훈련 환경 설정 — 훈련 탭으로 이전됨. 하위 호환 리디렉션."""
    return redirect("/training?msg=훈련 환경 설정은 훈련 탭 하단에서 변경하세요")


@settings_bp.post("/settings/ai")
def settings_ai_post():
    """AI 코치 설정 저장."""
    config = load_config()
    config.setdefault("ai", {})
    provider = (request.form.get("ai_provider") or "rule").strip()
    config["ai"]["provider"] = provider
    for key_name in ("gemini_api_key", "groq_api_key", "claude_api_key", "openai_api_key"):
        val = (request.form.get(key_name) or "").strip()
        if val:
            config["ai"][key_name] = val
    save_config(config)
    return redirect(f"/settings?msg=AI 설정 저장됨 (제공자: {provider})")


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


@settings_bp.post("/settings/prompts")
def settings_prompts_post():
    """사용자 커스텀 프롬프트 저장."""
    from src.ai.prompt_config import DEFAULT_PROMPTS
    config = load_config()
    config.setdefault("ai", {})
    custom = {}
    for key in DEFAULT_PROMPTS:
        val = request.form.get(f"prompt_{key}", "").strip()
        if val and val != DEFAULT_PROMPTS[key]["template"]:
            custom[key] = {"template": val}
    config["ai"]["custom_prompts"] = custom
    save_config(config)
    return redirect("/settings?msg=프롬프트가 저장되었습니다")


@settings_bp.get("/settings/prompts-reset")
def settings_prompts_reset():
    """프롬프트 기본값 복원."""
    config = load_config()
    config.get("ai", {}).pop("custom_prompts", None)
    save_config(config)
    return redirect("/settings?msg=프롬프트가 기본값으로 복원되었습니다")


@settings_bp.post("/settings/caldav")
def settings_caldav_post():
    """CalDAV 설정 저장."""
    config = load_config()
    config.setdefault("caldav", {})
    config["caldav"]["url"] = (request.form.get("caldav_url") or "").strip()
    config["caldav"]["username"] = (request.form.get("caldav_username") or "").strip()
    pw = (request.form.get("caldav_password") or "").strip()
    if pw:
        config["caldav"]["password"] = pw
    save_config(config)
    return redirect("/settings?msg=CalDAV 설정이 저장되었습니다")


@settings_bp.get("/settings/caldav-test")
def settings_caldav_test():
    """CalDAV 연결 테스트."""
    from src.training.caldav_push import test_connection
    config = load_config()
    ok, msg = test_connection(config)
    return msg

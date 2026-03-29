"""설정 페이지 렌더 헬퍼 — 서비스 카드 + 프로필 + Mapbox + CalDAV.

views_settings.py에서 분리 (2026-03-29).
"""
from __future__ import annotations

import html as _html


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
    from src.web.helpers import db_path
    est: dict = {}
    try:
        dbp = db_path()
        if not dbp or not dbp.exists():
            return est
        with sqlite3.connect(str(dbp)) as conn:
            from src.metrics.store import estimate_max_hr
            max_hr_est = estimate_max_hr(conn)
            if max_hr_est != 190.0:
                est["max_hr"] = int(max_hr_est)
            row = conn.execute(
                "SELECT metric_value FROM computed_metrics WHERE metric_name='eFTP' "
                "AND activity_id IS NULL AND metric_value IS NOT NULL ORDER BY date DESC LIMIT 1"
            ).fetchone()
            if row and row[0]:
                est["eftp"] = int(row[0])
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
    thr_mm = int(thr_pace) // 60
    thr_ss = int(thr_pace) % 60

    est = _estimate_profile()
    est_parts = []
    if est.get("max_hr"):
        est_parts.append(f"최대HR <strong>{est['max_hr']}</strong>bpm")
    if est.get("eftp"):
        m, s = divmod(est["eftp"], 60)
        est_parts.append(f"역치 <strong>{m}:{s:02d}</strong>/km")
    if est.get("weekly_km"):
        est_parts.append(f"주간 <strong>{est['weekly_km']:.1f}</strong>km")
    est_note = ""
    if est_parts:
        est_note = (
            "<div style='display:flex;align-items:center;gap:0.6rem;margin:0 0 0.6rem;flex-wrap:wrap;'>"
            f"<span style='font-size:0.8rem;color:var(--cyan);'>📊 RunPulse 추정: {' · '.join(est_parts)}</span>"
            f"<button type='button' onclick=\"applyEstimate({est.get('max_hr', 190)},{est.get('eftp', 300)},{est.get('weekly_km', 40)})\" "
            "style='background:rgba(0,212,255,0.15);color:var(--cyan);border:1px solid rgba(0,212,255,0.3);"
            "border-radius:12px;padding:2px 10px;font-size:0.75rem;cursor:pointer;'>적용</button></div>"
            "<script>function applyEstimate(hr,eftp,wk){"
            f"document.querySelector('[name=max_hr]').value=hr;"
            f"document.querySelector('[name=threshold_pace_min]').value=Math.floor(eftp/60);"
            f"document.querySelector('[name=threshold_pace_sec]').value=eftp%60;"
            f"document.querySelector('[name=weekly_km]').value=wk;"
            "}</script>"
        )

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


def _render_caldav_section(config: dict) -> str:
    """CalDAV 캘린더 설정 섹션."""
    c = config.get("caldav", {})
    url = c.get("url", "")
    username = c.get("username", "")
    has_pw = bool(c.get("password", ""))
    status = "<span style='color:var(--green);'>설정됨</span>" if url and username else "<span style='color:var(--muted);'>미설정</span>"
    return f"""
<div class='card'>
  <h2 style='margin-bottom:0.5rem;'>캘린더 연동 (CalDAV)</h2>
  <p class='muted' style='font-size:0.82rem;margin-bottom:0.6rem;'>
    훈련 계획을 Google/네이버/Apple 캘린더에 자동 등록합니다.
  </p>
  <p style='font-size:0.82rem;margin-bottom:0.6rem;'>상태: {status}</p>
  <form method='post' action='/settings/caldav' style='display:flex;flex-direction:column;gap:0.5rem;'>
    <label style='font-size:0.88rem;'>
      CalDAV URL
      <input type='text' name='caldav_url' value='{url}' placeholder='https://caldav.googleapis.com/...'
        style='display:block;margin-top:0.2rem;padding:0.4rem;border-radius:4px;
        border:1px solid rgba(255,255,255,0.2);background:rgba(255,255,255,0.07);color:inherit;width:100%;'>
    </label>
    <label style='font-size:0.88rem;'>
      사용자명
      <input type='text' name='caldav_username' value='{username}' placeholder='user@gmail.com'
        style='display:block;margin-top:0.2rem;padding:0.4rem;border-radius:4px;
        border:1px solid rgba(255,255,255,0.2);background:rgba(255,255,255,0.07);color:inherit;width:100%;'>
    </label>
    <label style='font-size:0.88rem;'>
      비밀번호 (앱 비밀번호) <span class='muted' style='font-size:0.78rem;'>({'설정됨' if has_pw else '미설정'})</span>
      <input type='password' name='caldav_password' placeholder='앱 비밀번호 입력...'
        style='display:block;margin-top:0.2rem;padding:0.4rem;border-radius:4px;
        border:1px solid rgba(255,255,255,0.2);background:rgba(255,255,255,0.07);color:inherit;width:100%;'>
    </label>
    <div style='display:flex;gap:0.5rem;'>
      <button type='submit'
        style='padding:0.45rem 1.2rem;background:var(--cyan);color:#000;border:none;border-radius:4px;cursor:pointer;font-weight:bold;'>
        저장</button>
      <button type='button' onclick="fetch('/settings/caldav-test').then(r=>r.text()).then(t=>alert(t))"
        style='padding:0.45rem 1.2rem;background:rgba(255,255,255,0.1);color:var(--fg);border:1px solid rgba(255,255,255,0.2);border-radius:4px;cursor:pointer;'>
        연결 테스트</button>
    </div>
  </form>
  <p class='muted' style='font-size:0.75rem;margin-top:0.5rem;'>
    Google: <a href='https://myaccount.google.com/apppasswords' target='_blank' style='color:var(--cyan);'>앱 비밀번호 발급</a> ·
    네이버: <a href='https://nid.naver.com/user2/help/myInfoV2?m=viewSecurity' target='_blank' style='color:var(--cyan);'>앱 비밀번호</a>
  </p>
</div>"""

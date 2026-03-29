"""설정 — Strava / Intervals.icu / Runalyze 연동 라우트.

views_settings.py에서 분리 (2026-03-29).
"""
from __future__ import annotations

import html as _html
import urllib.parse

from flask import Blueprint, redirect, render_template, request

from src.sync.intervals import check_intervals_connection
from src.sync.runalyze import check_runalyze_connection
from src.utils.config import load_config, update_service_config
from src.utils.sync_state import clear_retry_after

settings_integrations_bp = Blueprint("settings_integrations", __name__)

_STRAVA_AUTH_URL = "https://www.strava.com/oauth/authorize"
_STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"
_STRAVA_SCOPE = "read,activity:read_all"
_STRAVA_REDIRECT_PATH = "/connect/strava/callback"


# ── Strava ─────────────────────────────────────────────────────────────

@settings_integrations_bp.get("/connect/strava")
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


@settings_integrations_bp.post("/connect/strava/save-app")
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


@settings_integrations_bp.get("/connect/strava/oauth-start")
def strava_oauth_start():
    """Strava OAuth2 인증 시작."""
    config = load_config()
    client_id = config.get("strava", {}).get("client_id", "")
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


@settings_integrations_bp.get("/connect/strava/callback")
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

    try:
        with httpx.Client(timeout=15) as client:
            resp = client.post(_STRAVA_TOKEN_URL, data={
                "client_id": client_id, "client_secret": client_secret,
                "code": code, "grant_type": "authorization_code",
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


@settings_integrations_bp.post("/connect/strava/disconnect")
def strava_disconnect():
    """Strava 연동 해제."""
    update_service_config("strava", {"access_token": "", "refresh_token": "", "expires_at": 0})
    return redirect("/settings")


# ── Intervals.icu ──────────────────────────────────────────────────────

@settings_integrations_bp.get("/connect/intervals")
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


@settings_integrations_bp.post("/connect/intervals")
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

    config = load_config()
    result = check_intervals_connection(config)
    if result["ok"]:
        return redirect("/connect/intervals?msg=" + urllib.parse.quote(f"연결 성공: {result['detail']}"))
    return redirect("/connect/intervals?error=" + urllib.parse.quote(f"연결 실패 [{result['status']}]: {result['detail']}"))


@settings_integrations_bp.post("/connect/intervals/disconnect")
def intervals_disconnect():
    """Intervals.icu 연동 해제."""
    update_service_config("intervals", {"athlete_id": "", "api_key": ""})
    return redirect("/settings")


# ── Runalyze ──────────────────────────────────────────────────────────

@settings_integrations_bp.get("/connect/runalyze")
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


@settings_integrations_bp.post("/connect/runalyze")
def runalyze_connect_post():
    """Runalyze 토큰 저장 + 연결 테스트."""
    token = request.form.get("token", "").strip()
    action = request.form.get("action", "save")

    if not token:
        return redirect("/connect/runalyze?error=" + urllib.parse.quote("토큰을 입력하세요."))

    update_service_config("runalyze", {"token": token})
    clear_retry_after("runalyze")

    if action == "save":
        return redirect("/connect/runalyze?msg=" + urllib.parse.quote("저장 완료."))

    config = load_config()
    result = check_runalyze_connection(config)
    if result["ok"]:
        return redirect("/connect/runalyze?msg=" + urllib.parse.quote(f"연결 성공: {result['detail']}"))
    return redirect("/connect/runalyze?error=" + urllib.parse.quote(f"연결 실패 [{result['status']}]: {result['detail']}"))


@settings_integrations_bp.post("/connect/runalyze/disconnect")
def runalyze_disconnect():
    """Runalyze 연동 해제."""
    update_service_config("runalyze", {"token": ""})
    return redirect("/settings")

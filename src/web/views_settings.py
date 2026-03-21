"""서비스 연동 설정 뷰 — Blueprint.

/settings       : 전체 연동 상태 개요
/connect/garmin : Garmin 연동 폼 (이메일/패스워드 → 토큰 저장)
/connect/strava : Strava OAuth2 시작 (→ strava.com 리다이렉트)
/connect/strava/callback : OAuth2 콜백 (code → token 교환 → 저장)
/connect/intervals : Intervals.icu API 키 폼 (저장 + 연결 테스트)
/connect/runalyze  : Runalyze 토큰 폼 (저장 + 연결 테스트)
/connect/{service}/disconnect : 서비스 연동 해제
"""
from __future__ import annotations

import html as _html
import time
import urllib.parse
from pathlib import Path

from flask import Blueprint, redirect, request, url_for

from src.sync.garmin import check_garmin_connection, _tokenstore_path
from src.sync.strava import check_strava_connection
from src.sync.intervals import check_intervals_connection
from src.sync.runalyze import check_runalyze_connection
from src.utils.config import load_config, update_service_config, save_config
from .helpers import db_path, html_page, metric_row, score_badge

settings_bp = Blueprint("settings", __name__)

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
) -> str:
    """서비스 연동 상태 카드 HTML."""
    badge = _status_badge(status["ok"], status["status"])
    detail = _html.escape(status.get("detail", ""))
    connect_label = "재연동" if status["ok"] else "연동하기"
    disconnect_btn = ""
    if disconnect_url:
        disconnect_btn = (
            f"<form method='post' action='{disconnect_url}' style='display:inline'>"
            f"<button type='submit' style='margin-left:0.5rem; background:#fdd; border:1px solid #c00; border-radius:4px; padding:0.2rem 0.6rem; cursor:pointer;'>연동 해제</button>"
            f"</form>"
        )
    return f"""
<div class='card'>
  <h2>{_html.escape(icon)} {_html.escape(name)}</h2>
  <p>{badge} <small class='muted'>{detail}</small></p>
  <a href='{connect_url}'>
    <button style='padding:0.4rem 1rem; cursor:pointer;'>{connect_label}</button>
  </a>
  {disconnect_btn}
  {extra_html}
</div>"""


# ── /settings — 전체 연동 상태 페이지 ──────────────────────────────
@settings_bp.get("/settings")
def settings_view() -> str:
    """4개 서비스 연동 상태 개요 페이지."""
    config = load_config()

    garmin_status = check_garmin_connection(config)
    strava_status = check_strava_connection(config)
    intervals_status = check_intervals_connection(config)
    runalyze_status = check_runalyze_connection(config)

    tokenstore = _tokenstore_path(config)

    garmin_extra = f"<p class='muted' style='font-size:0.85rem;'>토큰 저장소: <code>{_html.escape(str(tokenstore))}</code></p>"

    body = f"""
<p>각 서비스의 연동 상태를 확인하고 설정하세요.</p>
<div class='cards-row'>
  {_service_card("Garmin Connect", "⌚", garmin_status,
                 "/connect/garmin", "/connect/garmin/disconnect", garmin_extra)}
  {_service_card("Strava", "🏃", strava_status,
                 "/connect/strava", "/connect/strava/disconnect")}
</div>
<div class='cards-row'>
  {_service_card("Intervals.icu", "📊", intervals_status,
                 "/connect/intervals", "/connect/intervals/disconnect")}
  {_service_card("Runalyze", "📈", runalyze_status,
                 "/connect/runalyze", "/connect/runalyze/disconnect")}
</div>
<hr>
<p class='muted' style='font-size:0.85rem;'>
  연동 정보는 <code>config.json</code>에 저장됩니다. Garmin 토큰은 로컬 tokenstore에 별도 저장됩니다.
</p>"""
    return html_page("서비스 연동 설정", body)


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
  <p>{'<span class="score-badge grade-good">토큰 존재</span>' if Path(current_tokenstore).expanduser().exists() else '<span class="score-badge grade-poor">토큰 없음</span>'}</p>
  <p class='muted'>MFA가 요청될 경우: Garmin 앱 또는 이메일에서 인증 코드를 입력하세요. 현재 CLI 기반 MFA 입력은 지원하지 않습니다. 브라우저에서 직접 로그인 후 garth 토큰을 복사하는 방법을 권장합니다.</p>
</div>"""
    return html_page("Garmin 연동", body)


@settings_bp.post("/connect/garmin")
def garmin_connect_post():
    """Garmin 이메일/패스워드 저장 (+ 선택적으로 연결 테스트)."""
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "").strip()
    tokenstore_str = request.form.get("tokenstore", "~/.garth").strip()
    action = request.form.get("action", "save")

    # 이메일은 필수, 패스워드는 비어있으면 기존 값 유지
    if not email:
        return redirect("/connect/garmin?error=" + urllib.parse.quote("이메일을 입력하세요."))

    updates: dict = {"email": email, "tokenstore": tokenstore_str}
    if password:
        updates["password"] = password

    update_service_config("garmin", updates)

    if action == "save":
        return redirect("/connect/garmin?msg=" + urllib.parse.quote("저장 완료. 다음 sync 시 자동 로그인됩니다."))

    # save_and_test: 실제 로그인 시도
    try:
        from garminconnect import Garmin
        config = load_config()
        tokenstore = Path(tokenstore_str).expanduser()
        client = Garmin(email, password)
        client.login()
        tokenstore.mkdir(parents=True, exist_ok=True)
        client.garth.dump(str(tokenstore))
        return redirect("/connect/garmin?msg=" + urllib.parse.quote(f"연결 성공! 토큰이 {tokenstore_str}에 저장되었습니다."))
    except ImportError:
        return redirect("/connect/garmin?error=" + urllib.parse.quote("garminconnect 미설치. pip install garminconnect"))
    except Exception as e:
        err_msg = str(e)
        # MFA 감지
        if "mfa" in err_msg.lower() or "two-factor" in err_msg.lower() or "verification" in err_msg.lower():
            return redirect("/connect/garmin?error=" + urllib.parse.quote(
                "MFA(이중 인증) 요청됨. Garmin 앱 또는 이메일에서 인증을 완료한 후 다시 시도하세요."
            ))
        return redirect("/connect/garmin?error=" + urllib.parse.quote(f"로그인 실패: {err_msg[:200]}"))


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
    콜백 URL: <code>http://localhost:8080{_STRAVA_REDIRECT_PATH}</code><br>
    Strava API 앱 설정에서 위 URL을 Authorized Callback Domain에 추가해야 합니다.
  </p>
</div>"""
    return html_page("Strava 연동", body)


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
        "redirect_uri": f"http://localhost:8080{_STRAVA_REDIRECT_PATH}",
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
    <a href='https://intervals.icu/settings' target='_blank'>intervals.icu/settings</a> → API 탭 →
    API Key 복사 후 아래에 입력하세요.
  </p>
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
    return html_page("Intervals.icu 연동", body)


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
    <a href='https://runalyze.com/settings/personal-api' target='_blank'>runalyze.com/settings/personal-api</a>에서
    Personal API 토큰을 생성 또는 복사한 후 아래에 입력하세요.
  </p>
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
    return html_page("Runalyze 연동", body)


@settings_bp.post("/connect/runalyze")
def runalyze_connect_post():
    """Runalyze 토큰 저장 + 연결 테스트."""
    token = request.form.get("token", "").strip()
    action = request.form.get("action", "save")

    if not token:
        return redirect("/connect/runalyze?error=" + urllib.parse.quote("토큰을 입력하세요."))

    update_service_config("runalyze", {"token": token})

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

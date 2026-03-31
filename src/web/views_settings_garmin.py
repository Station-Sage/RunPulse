"""설정 — Garmin 연동 라우트 (connect/MFA/disconnect).

views_settings.py에서 분리 (2026-03-29).
"""
from __future__ import annotations

import html as _html
import urllib.parse
import uuid
from pathlib import Path

from flask import Blueprint, redirect, render_template, request

from src.sync.garmin import _tokenstore_path
from src.utils.config import _auto_user_id, load_config, update_service_config

settings_garmin_bp = Blueprint("settings_garmin", __name__)

# MFA 대기 세션 (key → {client_state, garth_client, tokenstore, email})
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


@settings_garmin_bp.get("/connect/garmin")
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


@settings_garmin_bp.post("/connect/garmin")
def garmin_connect_post():
    """Garmin 이메일/패스워드 저장 (+ 선택적으로 연결 테스트, MFA 2단계 지원)."""
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

    cf_uid = _auto_user_id(None) or "default"
    safe_uid = cf_uid.replace("/", "_").replace("\\", "_")
    updates: dict = {
        "email": email,
        "tokenstore": f"~/.garth/{safe_uid}",
    }
    if password:
        updates["password"] = password
    update_service_config("garmin", updates)

    if action == "save":
        return redirect("/connect/garmin?msg=" + urllib.parse.quote("저장 완료. 다음 sync 시 자동 로그인됩니다."))

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

        if isinstance(result, tuple) and result[0] == "needs_mfa":
            key = str(uuid.uuid4())
            _pending_mfa[key] = {
                "client_state": result[1],
                "garth_client": g,
                "tokenstore": str(tokenstore),
                "email": email,
            }
            mfa_url = "/connect/garmin/mfa?" + urllib.parse.urlencode({
                "key": key, "tokenstore": tokenstore_str,
            })
            return redirect(mfa_url)

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


@settings_garmin_bp.get("/connect/garmin/mfa")
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


@settings_garmin_bp.post("/connect/garmin/mfa")
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


@settings_garmin_bp.post("/connect/garmin/disconnect")
def garmin_disconnect():
    """Garmin 연동 해제."""
    update_service_config("garmin", {"email": "", "password": ""})
    return redirect("/settings?msg=Garmin+연동+해제+완료")

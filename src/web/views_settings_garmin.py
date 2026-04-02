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

  <div style='background:#1e293b; border-radius:8px; padding:20px; margin-bottom:20px;'>
    <h3 style='margin-top:0; color:#4CAF50;'>🌐 브라우저 로그인 (권장)</h3>
    <p style='color:#aab; font-size:14px; line-height:1.6;'>
      브라우저에서 가민에 직접 로그인하여 연결합니다.<br>
      패스워드는 가민 서버에만 전송되며 이 서버를 경유하지 않습니다.
    </p>
    <div style='background:#111827; border-radius:6px; padding:16px; margin:12px 0;'>
      <div style='display:flex; align-items:flex-start; gap:12px; margin-bottom:12px;'>
        <span style='background:#4CAF50; color:white; border-radius:50%%; width:24px; height:24px; display:flex; align-items:center; justify-content:center; flex-shrink:0; font-size:13px;'>1</span>
        <span style='color:#ccc; font-size:14px;'>
          <a href='/connect/garmin/browser-login' target='_blank' style='color:#4CAF50; font-weight:bold;'>가민 로그인 페이지 열기</a>
          → 로그인 + MFA 완료
        </span>
      </div>
      <div style='display:flex; align-items:flex-start; gap:12px; margin-bottom:12px;'>
        <span style='background:#4CAF50; color:white; border-radius:50%%; width:24px; height:24px; display:flex; align-items:center; justify-content:center; flex-shrink:0; font-size:13px;'>2</span>
        <span style='color:#ccc; font-size:14px;'>로그인 성공 후 주소창 URL 전체를 복사</span>
      </div>
      <div style='display:flex; align-items:flex-start; gap:12px;'>
        <span style='background:#4CAF50; color:white; border-radius:50%%; width:24px; height:24px; display:flex; align-items:center; justify-content:center; flex-shrink:0; font-size:13px;'>3</span>
        <span style='color:#ccc; font-size:14px;'>아래에 붙여넣고 연결하기</span>
      </div>
    </div>
    <form method='post' action='/connect/garmin/paste-token'>
      <textarea name='oauth2_json' rows='2' placeholder='로그인 완료 후 주소창 URL을 여기에 붙여넣으세요  (예: https://sso.garmin.com/sso/embed?ticket=ST-...)' style='width:100%%; font-size:13px; font-family:monospace; background:#0f172a; color:#e2e8f0; padding:10px; border:1px solid #334155; border-radius:6px; resize:vertical;'></textarea>
      <button type='submit' style='margin-top:10px; background:#4CAF50; color:white; padding:10px 24px; border:none; border-radius:6px; cursor:pointer; font-size:14px; font-weight:bold;'>연결하기</button>
    </form>
  </div>

  <details style='margin-bottom:20px;'>
    <summary style='cursor:pointer; color:#94a3b8; font-size:14px;'>🔧 서버 직접 로그인 (서버 IP 차단 시 동작 안 함)</summary>
    <div style='background:#1e293b; border-radius:8px; padding:16px; margin-top:8px;'>
      <form method='post' action='/connect/garmin'>
        <table style='width:auto; border:none;'>
          <tr>
            <td style='border:none; padding:6px 8px;'><label style='color:#94a3b8;'>이메일</label></td>
            <td style='border:none; padding:6px 8px;'>
              <input type='email' name='email' value='{current_email}' required style='width:260px;'>
            </td>
          </tr>
          <tr>
            <td style='border:none; padding:6px 8px;'><label style='color:#94a3b8;'>패스워드</label></td>
            <td style='border:none; padding:6px 8px;'>
              <input type='password' name='password' placeholder='저장 안 됨' style='width:260px;'>
            </td>
          </tr>
        </table>
        <div style='margin-top:10px;'>
          <button type='submit' name='action' value='save'>저장</button>
          &nbsp;
          <button type='submit' name='action' value='save_and_test' style='background:#d4edff;'>저장 + 연결 테스트</button>
        </div>
      </form>
    </div>
  </details>

  <details>
    <summary style='cursor:pointer; color:#94a3b8; font-size:14px;'>📁 토큰 파일 직접 업로드</summary>
    <div style='background:#1e293b; border-radius:8px; padding:16px; margin-top:8px;'>
      <p style='color:#94a3b8; font-size:13px;'>PC에서 <code>pip install garth</code> 후 토큰 발급하여 업로드</p>
      <form method='post' action='/connect/garmin/upload-token' enctype='multipart/form-data'>
        <div style='margin:8px 0;'>
          <label style='font-size:13px; color:#94a3b8;'>oauth1_token.json (선택):</label><br>
          <input type='file' name='oauth1' accept='.json' style='font-size:13px;'>
        </div>
        <div style='margin:8px 0;'>
          <label style='font-size:13px; color:#94a3b8;'>oauth2_token.json (필수):</label><br>
          <input type='file' name='oauth2' accept='.json' style='font-size:13px;'>
        </div>
        <button type='submit' style='margin-top:8px;'>토큰 업로드</button>
      </form>
    </div>
  </details>
</div>

<div class='card'>
  <h3>연결 상태</h3>
  <p style='color:#94a3b8;'>토큰 경로: <code>{current_tokenstore}</code></p>
  {_garmin_token_status_html(tokenstore)}
</div>"""
    return render_template("generic_page.html", title="Garmin 연동", body=body, active_tab="settings")


@settings_garmin_bp.post("/connect/garmin")
def garmin_connect_post():
    """Garmin 로그인 → 토큰 저장. 비밀번호는 config에 저장하지 않음."""
    try:
        import garth as _garth
        from garth import sso as _sso
    except ImportError:
        _garth = None
        _sso = None

    email = request.form.get("email", "").strip()
    password = request.form.get("password", "").strip()
    action = request.form.get("action", "save")

    if not email:
        return redirect("/connect/garmin?error=" + urllib.parse.quote("이메일을 입력하세요."))

    cf_uid = _auto_user_id(None) or "default"
    safe_uid = cf_uid.replace("/", "_").replace("\\", "_")

    # 비밀번호는 저장하지 않음 — 이메일과 토큰 경로만 저장
    updates: dict = {
        "email": email,
    }
    update_service_config("garmin", updates)

    if action == "save":
        return redirect("/connect/garmin?msg=" + urllib.parse.quote(
            "저장 완료. '저장 + 연결 테스트'로 로그인하세요."
        ))

    # 연결 테스트: 비밀번호 필수
    if _garth is None or _sso is None:
        return redirect("/connect/garmin?error=" + urllib.parse.quote(
            "garth 라이브러리가 설치되지 않았습니다. pip install garth"))

    if not password:
        return redirect("/connect/garmin?error=" + urllib.parse.quote(
            "로그인하려면 패스워드를 입력하세요. (패스워드는 서버에 저장되지 않습니다)"
        ))

    tokenstore = Path(f"~/.garth/{safe_uid}").expanduser()

    try:
        g = _garth.Client()
        result = _sso.login(email, password, client=g, return_on_mfa=True)

        if isinstance(result, tuple) and result[0] == "needs_mfa":
            key = str(uuid.uuid4())
            _pending_mfa[key] = {
                "client_state": result[1],
                "garth_client": g,
                "tokenstore": str(tokenstore),
                "email": email,
            }
            mfa_url = "/connect/garmin/mfa?" + urllib.parse.urlencode({
                "key": key, "tokenstore": str(tokenstore),
            })
            return redirect(mfa_url)

        oauth1, oauth2 = result
        g.oauth1_token = oauth1
        g.oauth2_token = oauth2
        tokenstore.mkdir(parents=True, exist_ok=True)
        g.dump(str(tokenstore))
        # tokenstore 경로를 config에 저장
        update_service_config("garmin", {"tokenstore": str(tokenstore)})
        return redirect("/connect/garmin?msg=" + urllib.parse.quote(
            "연결 성공! 토큰이 저장되었습니다. 패스워드는 서버에 보관되지 않습니다."
        ))

    except ImportError:
        return redirect("/connect/garmin?error=" + urllib.parse.quote("garth 미설치."))
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
        # tokenstore 경로를 config에 저장
        update_service_config("garmin", {"tokenstore": str(tokenstore)})
        return redirect("/connect/garmin?msg=" + urllib.parse.quote(
            f"MFA 인증 성공! 토큰이 {tokenstore_str}에 저장되었습니다."
        ))
    except Exception as e:
        return redirect("/connect/garmin?error=" + urllib.parse.quote(f"MFA 인증 실패: {str(e)[:200]}"))


@settings_garmin_bp.post("/connect/garmin/disconnect")
def garmin_disconnect():
    """Garmin 연동 해제 — 이메일 + 토큰 경로 제거."""
    update_service_config("garmin", {"email": "", "tokenstore": ""})
    return redirect("/settings?msg=Garmin+연동+해제+완료")

@settings_garmin_bp.get("/connect/garmin/browser-login")
def garmin_browser_login():
    """사용자 브라우저에서 가민 SSO 로그인 — 팝업으로 열림."""
    host = request.host_url.rstrip("/")
    callback_url = f"{host}/connect/garmin/callback"

    SSO_EMBED = "https://sso.garmin.com/sso/embed"

    params = urllib.parse.urlencode({
        "id": "gauth-widget",
        "embedWidget": "true",
        "gauthHost": SSO_EMBED,
        "service": SSO_EMBED,
        "source": SSO_EMBED,
        "redirectAfterAccountLoginUrl": SSO_EMBED,
        "redirectAfterAccountCreationUrl": SSO_EMBED,
    })

    return redirect(f"https://sso.garmin.com/sso/signin?{params}")


@settings_garmin_bp.post("/connect/garmin/upload-token")
def garmin_upload_token():
    """로컬에서 발급받은 garth 토큰 파일 업로드."""
    oauth1_file = request.files.get("oauth1")
    oauth2_file = request.files.get("oauth2")

    if not oauth2_file:
        return redirect("/connect/garmin?error=" + urllib.parse.quote(
            "oauth2_token.json 파일은 필수입니다."))

    cf_uid = _auto_user_id(None) or "default"
    safe_uid = cf_uid.replace("/", "_").replace("\\", "_")
    tokenstore = Path(f"~/.garth/{safe_uid}").expanduser()
    tokenstore.mkdir(parents=True, exist_ok=True)

    try:
        import json as _json
        # oauth2 저장
        oauth2_data = _json.loads(oauth2_file.read())
        with open(tokenstore / "oauth2_token.json", "w") as f:
            _json.dump(oauth2_data, f, indent=2)

        # oauth1 저장 (선택)
        if oauth1_file:
            oauth1_data = _json.loads(oauth1_file.read())
            with open(tokenstore / "oauth1_token.json", "w") as f:
                _json.dump(oauth1_data, f, indent=2)

        update_service_config("garmin", {"tokenstore": str(tokenstore)})

        return redirect("/connect/garmin?msg=" + urllib.parse.quote(
            "토큰 업로드 성공! 동기화를 시도해보세요."))

    except Exception as e:
        return redirect("/connect/garmin?error=" + urllib.parse.quote(
            f"토큰 저장 실패: {str(e)[:200]}"))

@settings_garmin_bp.post("/connect/garmin/paste-token")
def garmin_paste_token():
    """OAuth2 토큰 JSON 또는 ticket URL 붙여넣기."""
    raw = request.form.get("oauth2_json", "").strip()
    if not raw:
        return redirect("/connect/garmin?error=" + urllib.parse.quote(
            "토큰 JSON 또는 URL을 입력하세요."))

    import re
    import json as _json

    cf_uid = _auto_user_id(None) or "default"
    safe_uid = cf_uid.replace("/", "_").replace("\\", "_")
    tokenstore = Path(f"~/.garth/{safe_uid}").expanduser()
    tokenstore.mkdir(parents=True, exist_ok=True)

    # ticket URL인 경우
    ticket_match = re.search(r'ticket=([A-Za-z0-9\-]+)', raw)
    if ticket_match:
        try:
            import garth as _garth
            from garth.sso import get_oauth1_token, exchange

            g = _garth.Client()
            oauth1 = get_oauth1_token(ticket_match.group(1), g)
            oauth2 = exchange(oauth1, g)
            g.oauth1_token = oauth1
            g.oauth2_token = oauth2
            tokenstore.mkdir(parents=True, exist_ok=True)
            g.dump(str(tokenstore))
            update_service_config("garmin", {"tokenstore": str(tokenstore)})
            return redirect("/connect/garmin?msg=" + urllib.parse.quote(
                "연결 성공! 토큰이 저장되었습니다."))
        except Exception as e:
            return redirect("/connect/garmin?error=" + urllib.parse.quote(
                f"ticket 교환 실패: {str(e)[:200]}"))

    # JSON인 경우
    try:
        token_data = _json.loads(raw)
        with open(tokenstore / "oauth2_token.json", "w") as f:
            _json.dump(token_data, f, indent=2)
        update_service_config("garmin", {"tokenstore": str(tokenstore)})
        return redirect("/connect/garmin?msg=" + urllib.parse.quote(
            "토큰 저장 성공! 동기화를 시도해보세요."))
    except _json.JSONDecodeError:
        return redirect("/connect/garmin?error=" + urllib.parse.quote(
            "유효한 JSON 또는 ticket URL이 아닙니다."))
    except Exception as e:
        return redirect("/connect/garmin?error=" + urllib.parse.quote(
            f"토큰 저장 실패: {str(e)[:200]}"))

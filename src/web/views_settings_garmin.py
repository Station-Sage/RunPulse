"""설정 — Garmin 연동 라우트 (connect/MFA/disconnect).

views_settings.py에서 분리 (2026-03-29).
"""
from __future__ import annotations

import html as _html
import urllib.parse
import uuid
from pathlib import Path

from flask import Blueprint, redirect, render_template, request

from src.sync.garmin import _tokenstore_path, check_garmin_connection
from src.utils.config import _auto_user_id, load_config, update_service_config

settings_garmin_bp = Blueprint("settings_garmin", __name__)

# MFA 대기 세션 (key → {client_state, garth_client, tokenstore, email})
_pending_mfa: dict = {}


def _garmin_token_status_html(config: dict) -> str:
    """garmin_tokens.json 기반 연결 상태를 HTML 배지로 반환."""
    result = check_garmin_connection(config)
    if result["ok"]:
        return f"<span class='score-badge grade-good'>토큰 유효 ✓</span>"
    grade = "grade-moderate" if "마이그레이션" in result["status"] or "갱신" in result["status"] else "grade-poor"
    return f"<span class='score-badge {grade}'>{_html.escape(result['status'])}</span>"


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

  <details style='margin-bottom:20px;'>
    <summary style='cursor:pointer; color:#94a3b8; font-size:14px;'>📁 토큰 파일 직접 업로드 (권장)</summary>
    <div style='background:#1e293b; border-radius:8px; padding:16px; margin-top:8px;'>
      <p style='color:#94a3b8; font-size:13px;'>
        PC에서 아래 명령으로 <code>garmin_tokens.json</code>을 발급한 뒤 업로드하세요.<br>
        <code>pip install garminconnect curl_cffi ua-generator</code><br>
        <code>python -c "from garminconnect import Garmin; g=Garmin('email','pw'); g.login(); g.client.dump('.')"</code>
      </p>
      <form method='post' action='/connect/garmin/upload-token' enctype='multipart/form-data'>
        <div style='margin:8px 0;'>
          <label style='font-size:13px; color:#94a3b8;'>garmin_tokens.json (필수):</label><br>
          <input type='file' name='token' accept='.json' style='font-size:13px;'>
        </div>
        <button type='submit' style='margin-top:8px;'>토큰 업로드</button>
      </form>
    </div>
  </details>

  <details>
    <summary style='cursor:pointer; color:#94a3b8; font-size:14px;'>📋 토큰 JSON 직접 붙여넣기</summary>
    <div style='background:#1e293b; border-radius:8px; padding:16px; margin-top:8px;'>
      <p style='color:#94a3b8; font-size:13px;'><code>garmin_tokens.json</code> 파일 내용을 그대로 붙여넣으세요.</p>
      <form method='post' action='/connect/garmin/paste-token'>
        <textarea name='oauth2_json' rows='4' placeholder='{{"oauth1_token": ..., "oauth2_token": ...}}' style='width:100%%; font-size:13px; font-family:monospace; background:#0f172a; color:#e2e8f0; padding:10px; border:1px solid #334155; border-radius:6px; resize:vertical;'></textarea>
        <button type='submit' style='margin-top:10px; background:#4CAF50; color:white; padding:10px 24px; border:none; border-radius:6px; cursor:pointer; font-size:14px; font-weight:bold;'>저장하기</button>
      </form>
    </div>
  </details>
</div>

<div class='card'>
  <h3>연결 상태</h3>
  <p style='color:#94a3b8;'>토큰 경로: <code>{current_tokenstore}</code></p>
  {_garmin_token_status_html(config)}
</div>"""
    return render_template("generic_page.html", title="Garmin 연동", body=body, active_tab="settings")


@settings_garmin_bp.post("/connect/garmin")
def garmin_connect_post():
    """Garmin 로그인 → 토큰 저장. 비밀번호는 config에 저장하지 않음."""
    try:
        from garminconnect import Garmin as _Garmin
    except ImportError:
        return redirect("/connect/garmin?error=" + urllib.parse.quote(
            "garminconnect 라이브러리가 설치되지 않았습니다. "
            "pip install garminconnect curl_cffi ua-generator"
        ))

    email = request.form.get("email", "").strip()
    password = request.form.get("password", "").strip()
    action = request.form.get("action", "save")

    if not email:
        return redirect("/connect/garmin?error=" + urllib.parse.quote("이메일을 입력하세요."))

    cf_uid = _auto_user_id(None) or "default"
    safe_uid = cf_uid.replace("/", "").replace("@", "_at").replace("\\", "_")

    # 비밀번호는 저장하지 않음 — 이메일만 저장
    update_service_config("garmin", {"email": email})

    if action == "save":
        return redirect("/connect/garmin?msg=" + urllib.parse.quote(
            "저장 완료. '저장 + 연결 테스트'로 로그인하세요."
        ))

    # 연결 테스트: 비밀번호 필수
    if not password:
        return redirect("/connect/garmin?error=" + urllib.parse.quote(
            "로그인하려면 패스워드를 입력하세요. (패스워드는 서버에 저장되지 않습니다)"
        ))

    tokenstore = Path(f"~/.garminconnect/{safe_uid}").expanduser()

    try:
        garmin = _Garmin(email, password, return_on_mfa=True)
        mfa_status, client_state = garmin.login(tokenstore=str(tokenstore))

        if mfa_status == "needs_mfa":
            key = str(uuid.uuid4())
            _pending_mfa[key] = {
                "garmin_client": garmin,
                "client_state": client_state,
                "tokenstore": str(tokenstore),
                "email": email,
            }
            mfa_url = "/connect/garmin/mfa?" + urllib.parse.urlencode({
                "key": key, "tokenstore": str(tokenstore),
            })
            return redirect(mfa_url)

        # 로그인 성공 — 토큰 자동 저장
        tokenstore.mkdir(parents=True, exist_ok=True)
        garmin.client.dump(str(tokenstore))
        update_service_config("garmin", {"tokenstore": str(tokenstore)})
        return redirect("/connect/garmin?msg=" + urllib.parse.quote(
            "연결 성공! 토큰이 저장되었습니다. 패스워드는 서버에 보관되지 않습니다."
        ))

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
    key = request.form.get("key", "")
    mfa_code = request.form.get("mfa_code", "").strip()
    tokenstore_str = request.form.get("tokenstore", "~/.garminconnect")

    if not key or key not in _pending_mfa:
        return redirect("/connect/garmin?error=" + urllib.parse.quote("MFA 세션 만료. 다시 시도하세요."))
    if not mfa_code:
        mfa_url = "/connect/garmin/mfa?" + urllib.parse.urlencode({
            "key": key, "tokenstore": tokenstore_str, "error": "인증 코드를 입력하세요."
        })
        return redirect(mfa_url)

    pending = _pending_mfa.pop(key)
    try:
        garmin = pending["garmin_client"]
        garmin.resume_login(pending.get("client_state", {}), mfa_code)
        tokenstore = Path(pending["tokenstore"]).expanduser()
        tokenstore.mkdir(parents=True, exist_ok=True)
        garmin.client.dump(str(tokenstore))
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
    """브라우저 SSO 안내 — garminconnect 0.3.x 미지원으로 CLI 토큰 발급 안내."""
    body = """
<div class='card'>
  <h2>브라우저 로그인 미지원</h2>
  <p style='color:#94a3b8;'>
    garminconnect 0.3.x는 브라우저 기반 SSO를 지원하지 않습니다.<br>
    PC에서 CLI로 토큰을 발급한 뒤 업로드하거나 붙여넣기 방식을 이용하세요.
  </p>
  <div style='background:#1e293b; border-radius:8px; padding:16px; margin-top:12px;'>
    <p style='font-size:13px; color:#94a3b8; margin:0 0 8px;'>PC에서 실행:</p>
    <pre style='background:#0f172a; color:#e2e8f0; padding:12px; border-radius:6px; font-size:13px; overflow-x:auto;'>pip install garminconnect curl_cffi ua-generator
python -c "
from garminconnect import Garmin
import json, pathlib
g = Garmin('your@email.com', 'password')
g.login()
g.client.dump('.')
print(pathlib.Path('garmin_tokens.json').read_text())
"</pre>
  </div>
  <p style='margin-top:16px;'><a href='/connect/garmin'>← 연동 설정으로 돌아가기</a></p>
</div>"""
    return render_template("generic_page.html", title="브라우저 로그인 안내", body=body, active_tab="settings")


@settings_garmin_bp.post("/connect/garmin/upload-token")
def garmin_upload_token():
    """로컬에서 발급받은 garmin_tokens.json 업로드."""
    import json as _json

    token_file = request.files.get("token")
    if not token_file:
        return redirect("/connect/garmin?error=" + urllib.parse.quote(
            "garmin_tokens.json 파일은 필수입니다."))

    cf_uid = _auto_user_id(None) or "default"
    safe_uid = cf_uid.replace("/", "").replace("@", "_at").replace("\\", "_")
    tokenstore = Path(f"~/.garminconnect/{safe_uid}").expanduser()
    tokenstore.mkdir(parents=True, exist_ok=True)

    try:
        token_data = _json.loads(token_file.read())
        with open(tokenstore / "garmin_tokens.json", "w") as f:
            _json.dump(token_data, f, indent=2)

        update_service_config("garmin", {"tokenstore": str(tokenstore)})
        return redirect("/connect/garmin?msg=" + urllib.parse.quote(
            "토큰 업로드 성공! 동기화를 시도해보세요."))

    except Exception as e:
        return redirect("/connect/garmin?error=" + urllib.parse.quote(
            f"토큰 저장 실패: {str(e)[:200]}"))

@settings_garmin_bp.post("/connect/garmin/paste-token")
def garmin_paste_token():
    """garmin_tokens.json 내용 붙여넣기."""
    import json as _json

    raw = request.form.get("oauth2_json", "").strip()
    if not raw:
        return redirect("/connect/garmin?error=" + urllib.parse.quote(
            "토큰 JSON을 입력하세요."))

    cf_uid = _auto_user_id(None) or "default"
    safe_uid = cf_uid.replace("/", "").replace("@", "_at").replace("\\", "_")
    tokenstore = Path(f"~/.garminconnect/{safe_uid}").expanduser()
    tokenstore.mkdir(parents=True, exist_ok=True)

    try:
        token_data = _json.loads(raw)
        with open(tokenstore / "garmin_tokens.json", "w") as f:
            _json.dump(token_data, f, indent=2)
        update_service_config("garmin", {"tokenstore": str(tokenstore)})
        return redirect("/connect/garmin?msg=" + urllib.parse.quote(
            "토큰 저장 성공! 동기화를 시도해보세요."))
    except _json.JSONDecodeError:
        return redirect("/connect/garmin?error=" + urllib.parse.quote(
            "유효한 JSON이 아닙니다. garmin_tokens.json 파일 내용을 그대로 붙여넣으세요."))
    except Exception as e:
        return redirect("/connect/garmin?error=" + urllib.parse.quote(
            f"토큰 저장 실패: {str(e)[:200]}"))

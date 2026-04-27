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
        return "<span class='score-badge grade-good'>토큰 유효 ✓</span>"
    grade = "grade-moderate" if "마이그레이션" in result["status"] or "갱신" in result["status"] else "grade-poor"
    return f"<span class='score-badge {grade}'>{_html.escape(result['status'])}</span>"


def _sync_options_html(prefix: str) -> str:
    """동기화 트리거 옵션 HTML (upload/paste 폼 공용)."""
    return (
        f"<div style='margin:10px 0; padding:10px; background:#0f172a; border-radius:6px; border:1px solid #334155;'>"
        f"<label style='display:flex; align-items:center; gap:8px; cursor:pointer; font-size:13px; color:#94a3b8;'>"
        f"<input type='checkbox' name='trigger_sync' value='1' id='{prefix}_trigger_sync'"
        f" onchange='document.getElementById(\"{prefix}_days_row\").style.display=this.checked?\"flex\":\"none\";'>"
        f"토큰 저장 후 즉시 동기화 시작"
        f"</label>"
        f"<div id='{prefix}_days_row' style='display:none; align-items:center; gap:8px; margin-top:8px; padding-left:20px;'>"
        f"<label style='font-size:13px; color:#94a3b8;'>최근</label>"
        f"<input type='number' name='days' value='30' min='1' max='90' style='width:70px; font-size:13px;'>"
        f"<label style='font-size:13px; color:#94a3b8;'>일 동기화</label>"
        f"</div>"
        f"</div>"
    )


def _trigger_sync_and_redirect(user_id: str, days: int):
    """토큰 저장 후 bg_sync 트리거 → /connect/garmin 리다이렉트."""
    from datetime import date as _date
    from datetime import timedelta

    from src.web.bg_sync import start_job

    days = max(1, min(days, 90))
    config = load_config(user_id=user_id)
    to_date = _date.today().isoformat()
    from_date = (_date.today() - timedelta(days=days)).isoformat()
    try:
        job_id = start_job("garmin", from_date, to_date, config, user_id=user_id)
        msg = f"토큰 저장 + 동기화 시작 (job: {job_id}). 진행: /sync"
    except Exception as e:
        msg = f"토큰 저장 완료. 동기화 시작 실패: {str(e)[:100]}"
    return redirect("/connect/garmin?msg=" + urllib.parse.quote(msg))


@settings_garmin_bp.get("/connect/garmin")
def garmin_connect_view() -> str:
    """Garmin 연동 폼 (2탭: 로컬 동기화 권장 / 서버 직접)."""
    config = load_config()
    garmin_cfg = config.get("garmin", {})
    tokenstore = _tokenstore_path(config)
    current_email = _html.escape(garmin_cfg.get("email", ""))
    current_tokenstore = _html.escape(str(tokenstore))

    msg = _html.escape(request.args.get("msg", ""))
    msg_html = f"<div class='card' style='border-color:#f0c040;'><p>{msg}</p></div>" if msg else ""
    err = _html.escape(request.args.get("error", ""))
    err_html = f"<div class='card' style='border-color:#c0392b;'><p style='color:#c0392b;'>{err}</p></div>" if err else ""

    # CF Service Token은 시스템 레벨 설정 → 루트 config에서 읽음
    cf_cfg = load_config(user_id="default").get("cf", {})
    cf_id_saved = cf_cfg.get("service_client_id", "")
    cf_secret_saved = cf_cfg.get("service_client_secret", "")
    _placeholder_id = "xxxxxxxx.access"
    _placeholder_secret = "your_cf_service_token_secret_here"
    cf_configured = bool(
        cf_id_saved and cf_secret_saved
        and cf_id_saved != _placeholder_id
        and cf_secret_saved != _placeholder_secret
    )
    cf_badge = (
        "<span class='score-badge grade-good' style='font-size:11px;'>설정됨 ✓</span>"
        if cf_configured
        else "<span class='score-badge grade-poor' style='font-size:11px;'>미설정</span>"
    )

    # CF 설정 카드
    _cf_id_val = _html.escape(cf_id_saved if cf_configured else "")
    _cf_secret_input = (
        f"<input type='password' name='cf_client_secret' value='{_html.escape(cf_secret_saved)}'"
        " style='width:100%; font-size:13px; font-family:monospace;'>"
        if cf_configured
        else "<input type='password' name='cf_client_secret' placeholder='CF Service Token Secret'"
             " style='width:100%; font-size:13px; font-family:monospace;'>"
    )
    _env_btn = (
        " &nbsp;<a href='/connect/garmin/download-env'"
        " style='font-size:13px; padding:5px 12px; background:#0f172a; border:1px solid #334155;"
        " border-radius:4px; color:#94a3b8; text-decoration:none;'>📥 .env 다운로드</a>"
    )
    cf_card = (
        "<div style='background:#1e293b; border-radius:8px; padding:16px; margin-bottom:14px;'>"
        "<div style='display:flex; align-items:center; justify-content:space-between; margin-bottom:10px;'>"
        "<span style='font-size:14px; color:#e2e8f0; font-weight:600;'>CF Service Token</span>"
        + cf_badge +
        "</div>"
        "<p style='color:#64748b; font-size:12px; margin:0 0 10px;'>"
        "CF Zero Trust 대시보드 → Access → Service Auth에서 발급. "
        "스크립트가 VPS API를 호출할 때 인증에 사용됩니다."
        "</p>"
        "<form method='post' action='/connect/garmin/cf-settings'>"
        "<table style='width:100%; border:none; border-collapse:collapse;'>"
        "<tr>"
        "<td style='border:none; padding:3px 6px; font-size:13px; color:#94a3b8; white-space:nowrap; width:110px;'>Client ID</td>"
        f"<td style='border:none; padding:3px 6px;'><input type='text' name='cf_client_id' value='{_cf_id_val}'"
        f" placeholder='{_placeholder_id}' style='width:100%; font-size:13px; font-family:monospace;'></td>"
        "</tr>"
        "<tr>"
        "<td style='border:none; padding:3px 6px; font-size:13px; color:#94a3b8;'>Client Secret</td>"
        f"<td style='border:none; padding:3px 6px;'>{_cf_secret_input}</td>"
        "</tr>"
        "</table>"
        "<div style='margin-top:10px; display:flex; gap:8px; align-items:center; flex-wrap:wrap;'>"
        "<button type='submit' style='font-size:13px;'>저장</button>"
        + _env_btn +
        "</div>"
        "</form>"
        "</div>"
    )

    # 스크립트 다운로드 + 실행 안내
    script_card = (
        "<div style='background:#0f172a; border-radius:6px; padding:12px; margin-bottom:14px;'>"
        "<div style='display:flex; align-items:center; justify-content:space-between; margin-bottom:8px;'>"
        "<span style='font-size:13px; color:#94a3b8;'>스크립트</span>"
        "<a href='/connect/garmin/download-script'"
        " style='font-size:12px; padding:4px 10px; background:#1e293b; border:1px solid #334155;"
        " border-radius:4px; color:#94a3b8; text-decoration:none;'>📥 garmin_local_sync.py</a>"
        "</div>"
        "<p style='font-size:12px; color:#475569; margin:0 0 4px;'>Windows (Git Bash) — Python 3.12 필요:</p>"
        "<pre style='color:#e2e8f0; font-size:11px; margin:0 0 8px; overflow-x:auto; white-space:pre-wrap;'>"
        "py -3.12 -m venv .venv\n"
        "source .venv/Scripts/activate\n"
        "python garmin_local_sync.py</pre>"
        "<p style='font-size:12px; color:#475569; margin:0 0 4px;'>Mac / Linux — Python 3.12 필요:</p>"
        "<pre style='color:#e2e8f0; font-size:11px; margin:0 0 8px; overflow-x:auto; white-space:pre-wrap;'>"
        "python3.12 -m venv .venv\n"
        "source .venv/bin/activate\n"
        "python garmin_local_sync.py</pre>"
        "<p style='font-size:12px; color:#475569; margin:0 0 4px;'>Android (Termux):</p>"
        "<pre style='color:#e2e8f0; font-size:11px; margin:0 0 6px; overflow-x:auto; white-space:pre-wrap;'>"
        "pkg install python  # Python 없을 때만\n"
        "python garmin_local_sync.py</pre>"
        "<p style='font-size:11px; color:#f59e0b; margin:0 0 4px;'>"
        "⚠ Python 3.12 필요: curl_cffi(CF 인증 우회)가 3.13+ 미지원"
        "</p>"
        "<p style='font-size:11px; color:#475569; margin:0 0 0;'>"
        "필요한 패키지(garminconnect, curl_cffi 등)는 미설치 시 스크립트가 자동으로 설치합니다."
        "</p>"
        "<p style='font-size:11px; color:#334155; margin:0;'>"
        ".env 파일 지원: GARMIN_EMAIL, GARMIN_VPS_URL, CF_SERVICE_CLIENT_ID, CF_SERVICE_CLIENT_SECRET"
        "</p>"
        "</div>"
    )

    # Tab 1: 로컬 동기화 (권장)
    tab_local = (
        cf_card
        + script_card
        + "<details style='margin-bottom:12px;'>"
        "<summary style='cursor:pointer; color:#94a3b8; font-size:14px; padding:8px 0;'>📁 토큰 파일 직접 업로드</summary>"
        "<div style='background:#1e293b; border-radius:8px; padding:16px; margin-top:8px;'>"
        "<form method='post' action='/connect/garmin/upload-token' enctype='multipart/form-data'>"
        "<div style='margin:8px 0;'>"
        "<label style='font-size:13px; color:#94a3b8;'>garmin_tokens.json (필수):</label><br>"
        "<input type='file' name='token' accept='.json' style='font-size:13px; margin-top:4px;'>"
        "</div>"
        + _sync_options_html("upload") +
        "<button type='submit' style='margin-top:8px;'>토큰 업로드</button>"
        "</form>"
        "</div>"
        "</details>"
        "<details>"
        "<summary style='cursor:pointer; color:#94a3b8; font-size:14px; padding:8px 0;'>📋 토큰 JSON 직접 붙여넣기</summary>"
        "<div style='background:#1e293b; border-radius:8px; padding:16px; margin-top:8px;'>"
        "<p style='color:#94a3b8; font-size:13px;'><code>garmin_tokens.json</code> 파일 내용을 그대로 붙여넣으세요.</p>"
        "<form method='post' action='/connect/garmin/paste-token'>"
        "<textarea name='oauth2_json' rows='4' placeholder='{\"access_token\": ..., \"refresh_token\": ...}'"
        " style='width:100%; font-size:13px; font-family:monospace; background:#0f172a; color:#e2e8f0;"
        " padding:10px; border:1px solid #334155; border-radius:6px; resize:vertical;'></textarea>"
        + _sync_options_html("paste") +
        "<button type='submit' style='margin-top:10px; background:#4CAF50; color:white; padding:10px 24px;"
        " border:none; border-radius:6px; cursor:pointer; font-size:14px; font-weight:bold;'>저장하기</button>"
        "</form>"
        "</div>"
        "</details>"
    )

    # Tab 2: 서버 직접 로그인
    tab_server = (
        "<div style='background:#2d1515; border:1px solid #7f1d1d; border-radius:8px; padding:12px; margin-bottom:16px;'>"
        "<p style='color:#fca5a5; font-size:13px; margin:0;'>"
        "⚠️ <strong>주의</strong>: VPS IP가 Garmin 인증 서버(diauth.garmin.com)에 차단되면 로그인이 실패합니다. "
        "가능하면 <strong>로컬 동기화</strong> 탭을 사용하세요."
        "</p>"
        "</div>"
        "<div style='background:#1e293b; border-radius:8px; padding:16px;'>"
        "<form method='post' action='/connect/garmin'>"
        "<table style='width:auto; border:none;'>"
        "<tr>"
        "<td style='border:none; padding:6px 8px;'><label style='color:#94a3b8;'>이메일</label></td>"
        f"<td style='border:none; padding:6px 8px;'><input type='email' name='email' value='{current_email}' required style='width:260px;'></td>"
        "</tr>"
        "<tr>"
        "<td style='border:none; padding:6px 8px;'><label style='color:#94a3b8;'>패스워드</label></td>"
        "<td style='border:none; padding:6px 8px;'><input type='password' name='password' placeholder='저장 안 됨' style='width:260px;'></td>"
        "</tr>"
        "</table>"
        "<div style='margin-top:10px;'>"
        "<button type='submit' name='action' value='save'>저장</button>"
        "&nbsp;"
        "<button type='submit' name='action' value='save_and_test' style='background:#d4edff;'>저장 + 연결 테스트</button>"
        "</div>"
        "</form>"
        "</div>"
    )

    # Tab widget (프로젝트 공통 패턴)
    tabs = [("local", "로컬 동기화 (권장)", tab_local), ("server", "서버 직접 로그인", tab_server)]
    btns = []
    panels = []
    for i, (key, label, content) in enumerate(tabs):
        is_first = i == 0
        bg = "var(--cyan)" if is_first else "none"
        color = "#000" if is_first else "var(--muted)"
        border = "var(--cyan)" if is_first else "var(--card-border)"
        btns.append(
            f"<button id='gtab-btn-{key}' onclick='switchGarminTab(\"{key}\")'"
            f" style='padding:0.4rem 1rem;font-size:13px;border:1px solid {border};"
            f"background:{bg};color:{color};border-radius:4px;cursor:pointer;'>"
            f"{label}</button>"
        )
        display = "block" if is_first else "none"
        panels.append(f"<div id='gtab-panel-{key}' style='display:{display};margin-top:12px;'>{content}</div>")

    tab_keys_js = ",".join(f"'{k}'" for k, _, _ in tabs)
    tab_js = (
        "<script>"
        f"var _gTabKeys=[{tab_keys_js}];"
        "function switchGarminTab(t){"
        "_gTabKeys.forEach(function(k){"
        "var p=document.getElementById('gtab-panel-'+k);"
        "var b=document.getElementById('gtab-btn-'+k);"
        "if(!p||!b)return;"
        "if(k===t){p.style.display='block';b.style.background='var(--cyan)';b.style.color='#000';b.style.borderColor='var(--cyan)';}"
        "else{p.style.display='none';b.style.background='none';b.style.color='var(--muted)';b.style.borderColor='var(--card-border)';}"
        "})}"
        "</script>"
    )

    tab_html = (
        f"<div style='display:flex;gap:6px;flex-wrap:wrap;'>{''.join(btns)}</div>"
        + "".join(panels)
        + tab_js
    )

    body = f"""
{err_html}{msg_html}
<div class='card'>
  <h2>Garmin Connect 연동</h2>
  {tab_html}
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
    <pre style='background:#0f172a; color:#e2e8f0; padding:12px; border-radius:6px; font-size:13px; overflow-x:auto;'># Python 3.12 필요 (curl_cffi 지원)
# Windows: py -3.12 -m venv .venv && source .venv/Scripts/activate
# Mac/Linux: python3.12 -m venv .venv && source .venv/bin/activate
pip install garminconnect curl_cffi ua-generator
python garmin_local_sync.py  # .env 파일 포함 시 이메일/패스워드 자동 로드</pre>
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

        if request.form.get("trigger_sync") == "1":
            return _trigger_sync_and_redirect(cf_uid, int(request.form.get("days", 30) or 30))

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

        if request.form.get("trigger_sync") == "1":
            return _trigger_sync_and_redirect(cf_uid, int(request.form.get("days", 30) or 30))

        return redirect("/connect/garmin?msg=" + urllib.parse.quote(
            "토큰 저장 성공! 동기화를 시도해보세요."))
    except _json.JSONDecodeError:
        return redirect("/connect/garmin?error=" + urllib.parse.quote(
            "유효한 JSON이 아닙니다. garmin_tokens.json 파일 내용을 그대로 붙여넣으세요."))
    except Exception as e:
        return redirect("/connect/garmin?error=" + urllib.parse.quote(
            f"토큰 저장 실패: {str(e)[:200]}"))


def _strip_cf_header_prefix(value: str, header_name: str) -> str:
    """'CF-Access-Client-Id: xxx' 형식 붙여넣기 허용 — prefix 자동 제거."""
    lower = value.lower()
    prefix = header_name.lower() + ":"
    if lower.startswith(prefix):
        return value[len(prefix):].strip()
    return value


@settings_garmin_bp.post("/connect/garmin/cf-settings")
def garmin_cf_settings_post():
    """CF Service Token 저장."""
    cf_id = _strip_cf_header_prefix(
        request.form.get("cf_client_id", "").strip(), "CF-Access-Client-Id"
    )
    cf_secret = _strip_cf_header_prefix(
        request.form.get("cf_client_secret", "").strip(), "CF-Access-Client-Secret"
    )
    if not cf_id or not cf_secret:
        return redirect("/connect/garmin?error=" + urllib.parse.quote(
            "Client ID와 Secret을 모두 입력하세요."))
    update_service_config("cf", {"service_client_id": cf_id, "service_client_secret": cf_secret}, user_id="default")
    return redirect("/connect/garmin?msg=" + urllib.parse.quote(
        "CF Service Token 저장 완료. .env 다운로드 후 스크립트에서 바로 사용 가능합니다."))


@settings_garmin_bp.get("/connect/garmin/download-script")
def garmin_download_script():
    """garmin_local_sync.py 다운로드."""
    from flask import send_file
    script_path = Path(__file__).parents[2] / "scripts" / "garmin_local_sync.py"
    return send_file(script_path, as_attachment=True, download_name="garmin_local_sync.py",
                     mimetype="text/x-python")


@settings_garmin_bp.get("/connect/garmin/download-env")
def garmin_download_env():
    """CF 토큰 pre-fill된 .env 파일 생성 + 다운로드."""
    from flask import make_response, session
    config = load_config()
    garmin_cfg = config.get("garmin", {})
    cf_cfg = load_config(user_id="default").get("cf", {})
    runpulse_user_id = session.get("user_id", "")
    lines = [
        "# Garmin 로컬 동기화 설정 — garmin_local_sync.py",
        f"RUNPULSE_USER_ID={runpulse_user_id}",
        f"GARMIN_EMAIL={garmin_cfg.get('email', 'your@email.com')}",
        "# GARMIN_PASSWORD=  # 첫 실행 후 스크립트가 자동 저장 제안",
        "# GARMIN_TOKENSTORE=  # 기본값: 스크립트 위치/.garminconnect (첫 실행 시 자동 설정)",
        f"CF_SERVICE_CLIENT_ID={cf_cfg.get('service_client_id', '')}",
        f"CF_SERVICE_CLIENT_SECRET={cf_cfg.get('service_client_secret', '')}",
        "# GARMIN_VPS_URL=  # 기본값: https://runpulse.stationsage.dev",
    ]
    resp = make_response("\n".join(lines) + "\n")
    resp.headers["Content-Type"] = "text/plain; charset=utf-8"
    resp.headers["Content-Disposition"] = "attachment; filename=.env"
    return resp

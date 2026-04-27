"""Garmin 로컬 토큰 발급 + VPS 동기화 트리거 스크립트.

로컬 기기(주거용 IP)에서 Garmin 로그인 후 발급된 토큰을 VPS에 업로드하고
백그라운드 sync를 시작한다. AWS VPS IP가 diauth.garmin.com에 차단된 경우의
우회 방법 (ADR-010, A안).

사용법:
    python garmin_local_sync.py                          # 처음 실행 (이메일/패스워드 입력)
    python garmin_local_sync.py --days 7                 # 동기화 기간 변경
    python garmin_local_sync.py --vps https://other.dev  # VPS URL 오버라이드

환경변수 (.env 파일 지원):
    RUNPULSE_USER_ID          RunPulse 앱 user_id (GitHub 이메일, .env 다운로드 시 자동 설정)
    GARMIN_EMAIL              Garmin 계정 이메일
    GARMIN_PASSWORD           Garmin 패스워드 (로그인 성공 후 저장 가능)
    GARMIN_TOKENSTORE         토큰 저장 디렉터리 (기본값: 스크립트 위치/.garminconnect, 첫 실행 시 .env 자동 저장)
    CF_SERVICE_CLIENT_ID      CF Zero Trust 서비스 토큰 Client ID
    CF_SERVICE_CLIENT_SECRET  CF Zero Trust 서비스 토큰 Client Secret
    GARMIN_VPS_URL            VPS URL 오버라이드 (기본값: https://runpulse.stationsage.dev)
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
from pathlib import Path


_DEFAULT_VPS_URL = "https://runpulse.stationsage.dev"
_REQUIRED_PACKAGES = ["garminconnect>=0.3.1", "curl_cffi", "ua-generator"]
_TOKEN_FILES = ["oauth1_token.json", "oauth2_token.json"]


def _ensure_venv() -> None:
    """스크립트 폴더 .venv(Python 3.12)로 자동 재실행. 없으면 생성 후 재실행."""
    import subprocess

    script_dir = Path(__file__).parent
    venv_dir = script_dir / ".venv"
    is_win = sys.platform == "win32"
    venv_python = venv_dir / ("Scripts" if is_win else "bin") / ("python.exe" if is_win else "python")

    # 이미 이 venv Python으로 실행 중이면 skip
    try:
        if venv_python.exists() and venv_python.resolve().samefile(Path(sys.executable).resolve()):
            return
    except OSError:
        pass

    if not venv_python.exists():
        print(".venv 생성 중 (Python 3.12)...")
        py312_candidates = [["py", "-3.12"]] if is_win else [["python3.12"], ["python3"]]
        created = False
        for cmd in py312_candidates:
            try:
                subprocess.check_call(cmd + ["-m", "venv", str(venv_dir)])
                created = True
                break
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue
        if not created:
            print("경고: Python 3.12를 찾을 수 없어 venv 생성 실패. 현재 Python으로 계속합니다.")
            return

    print("가상환경으로 재실행 중...")
    sys.exit(subprocess.run([str(venv_python)] + sys.argv).returncode)


def _ensure_deps() -> None:
    """garminconnect 미설치 시 한 번만 설치."""
    try:
        import garminconnect  # noqa: F401
        return
    except ImportError:
        pass
    print(f"패키지 설치 중: {' '.join(_REQUIRED_PACKAGES)} ...")
    import subprocess
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "--quiet"] + _REQUIRED_PACKAGES,
    )
    print("설치 완료.")


def _load_dotenv() -> None:
    """스크립트 디렉터리 또는 현재 디렉터리의 .env 파일 로드 (python-dotenv 불필요)."""
    for base in (Path(__file__).parent, Path.cwd()):
        env_file = base / ".env"
        if env_file.exists():
            with open(env_file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, _, value = line.partition("=")
                        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
            break


def _dotenv_set(key: str, value: str) -> None:
    """스크립트 디렉터리 .env 파일에 key=value upsert."""
    env_file = Path(__file__).parent / ".env"
    lines: list[str] = []
    if env_file.exists():
        with open(env_file, encoding="utf-8") as f:
            lines = f.readlines()
    for i, line in enumerate(lines):
        if line.strip().startswith(f"{key}="):
            lines[i] = f"{key}={value}\n"
            break
    else:
        lines.append(f"{key}={value}\n")
    with open(env_file, "w", encoding="utf-8") as f:
        f.writelines(lines)


def _save_dotenv(email: str, password: str) -> None:
    """로그인 성공 후 .env에 이메일/패스워드 upsert."""
    _dotenv_set("GARMIN_EMAIL", email)
    _dotenv_set("GARMIN_PASSWORD", password)
    print(f"  저장 완료: {(Path(__file__).parent / '.env').resolve()}")


def _prompt(label: str, default: str = "", secret: bool = False) -> str:
    """기본값 있으면 그대로 반환, 없으면 인터랙티브 입력."""
    if default:
        return default
    if secret:
        return getpass.getpass(f"{label}: ")
    return input(f"{label}: ").strip()


def _garmin_login(email: str, password: str) -> dict:
    """Garmin 로그인 후 oauth2 토큰 dict 반환."""
    try:
        from garminconnect import Garmin, GarminConnectTooManyRequestsError
    except ImportError:
        print("오류: garminconnect 패키지가 설치되지 않았습니다.")
        print("  pip install 'garminconnect>=0.3.1'")
        sys.exit(1)

    tokenstore_str = os.environ.get("GARMIN_TOKENSTORE", "")
    if tokenstore_str:
        tokenstore = Path(tokenstore_str)
    else:
        tokenstore = Path(__file__).parent / ".garminconnect"
        try:
            _dotenv_set("GARMIN_TOKENSTORE", str(tokenstore))
        except OSError:
            pass
        os.environ["GARMIN_TOKENSTORE"] = str(tokenstore)

    tokenstore.mkdir(parents=True, exist_ok=True)

    # 기존 토큰 파일이 있으면 Garmin 서버로 유효성 검증 (DI 형식은 expires_at 없음)
    _token_file = tokenstore / "garmin_tokens.json"
    if _token_file.exists():
        print(f"[1/3] 기존 토큰 발견 — 유효성 확인 중...")
        try:
            _client = Garmin()
            _client.login(tokenstore=str(tokenstore))
            # 갱신된 토큰 저장
            try:
                _g = _client.garth
                if hasattr(_g, "dump"):
                    _g.dump(str(tokenstore))
            except Exception:
                pass
            with open(_token_file, encoding="utf-8") as f:
                _tok = json.load(f)
            _keys = list(_tok.keys()) if isinstance(_tok, dict) else type(_tok).__name__
            print(f"[2/3] 토큰 유효 — 재인증 불필요. (키: {_keys})")
            return _tok
        except Exception as e:
            print(f"  토큰 만료 또는 갱신 실패 ({e}). 재로그인합니다.")

    # 유효한 토큰 없음 — stale 캐시 삭제 후 재로그인
    # (garth가 stale OAuth1 캐시를 로드하면 SSO를 스킵해 MFA 프롬프트가 뜨지 않음)
    for _f in list(tokenstore.iterdir()):
        if _f.is_file():
            _f.unlink()

    print(f"[1/3] Garmin 로그인 중... ({email})")

    def _prompt_mfa() -> str:
        return input("MFA 코드 입력: ").strip()

    client = Garmin(email, password, prompt_mfa=_prompt_mfa)

    try:
        client.login(tokenstore=str(tokenstore))
    except GarminConnectTooManyRequestsError:
        print("오류: Garmin 요청 한도 초과 (429). 잠시 후 다시 시도하세요.")
        sys.exit(1)
    except Exception as e:
        print(f"오류: 로그인 실패 — {e}")
        sys.exit(1)

    # garth가 auto-dump하지 않은 경우 강제 저장
    try:
        _g = client.garth
        if hasattr(_g, "dump"):
            _g.dump(str(tokenstore))
        elif hasattr(_g, "save"):
            _g.save(str(tokenstore))
    except Exception:
        pass

    _token_file_after = tokenstore / "garmin_tokens.json"
    if _token_file_after.exists():
        with open(_token_file_after, encoding="utf-8") as f:
            _tok = json.load(f)
        _keys = list(_tok.keys()) if isinstance(_tok, dict) else type(_tok).__name__
        print(f"[2/3] 토큰 발급 완료. (키: {_keys})")
        return _tok

    _ts_files = [f.name for f in tokenstore.iterdir()] if tokenstore.exists() else []
    print(f"오류: 토큰 파일이 생성되지 않았습니다. (tokenstore 파일: {_ts_files or '없음'})")
    sys.exit(1)


def _upload_token(vps_url: str, token: dict, days: int, cf_id: str, cf_secret: str, user_id: str) -> None:
    """토큰을 VPS에 POST하고 sync를 트리거한다."""
    url = vps_url.rstrip("/") + "/api/garmin/local-sync"
    # sync_key: CF가 엣지에서 서비스 토큰 헤더를 제거하므로 body에 포함해 Flask가 2차 검증
    payload = {"token": token, "days": days, "user_id": user_id, "sync_key": cf_secret}
    cf_headers = {
        "CF-Access-Client-Id": cf_id,
        "CF-Access-Client-Secret": cf_secret,
    }

    print(f"[3/3] VPS에 토큰 업로드 중... ({url})")
    code: int = 0
    body_text: str = ""
    body: dict = {}

    try:
        # curl_cffi: browser TLS fingerprint으로 CF Bot Fight Mode 우회
        from curl_cffi import requests as _creq
        resp = _creq.post(url, json=payload, headers=cf_headers, timeout=30, impersonate="chrome")
        code = resp.status_code
        body_text = resp.text
        if code < 400:
            body = json.loads(body_text) if body_text else {}
    except ImportError:
        # urllib fallback (curl_cffi 미설치 환경)
        import urllib.request as _req
        import urllib.error as _uerr
        data = json.dumps(payload).encode("utf-8")
        headers = {**cf_headers, "Content-Type": "application/json"}
        try:
            req = _req.Request(url, data=data, headers=headers, method="POST")
            with _req.urlopen(req, timeout=30) as r:
                body_text = r.read().decode()
                code = r.status
                body = json.loads(body_text) if body_text else {}
        except _uerr.HTTPError as e:
            code = e.code
            try:
                body_text = e.read().decode()
            except Exception:
                pass
        except Exception as e:
            body_text = str(e)

    if code in (200, 202):
        print(f"성공: {body.get('message', 'sync 시작됨')}")
        job_id = body.get("job_id", "")
        if job_id:
            print(f"  job_id: {job_id}")
        print(f"  sync 진행 상황: {vps_url.rstrip('/')}/sync")
        return

    if code == 401:
        print("오류: CF 서비스 토큰 인증 실패 (401). CF_SERVICE_CLIENT_ID/SECRET을 확인하세요.")
    elif code == 400:
        print(f"오류: 잘못된 요청 (400). {body_text}")
    else:
        print(f"오류: 업로드 실패 — HTTP {code}. {body_text}")
    sys.exit(1)


def main() -> None:
    _ensure_venv()
    _ensure_deps()
    _load_dotenv()

    parser = argparse.ArgumentParser(
        description="Garmin 로컬 토큰 발급 + VPS 동기화 트리거",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--user-id", default=os.environ.get("RUNPULSE_USER_ID", ""),
                        help="RunPulse 앱 user_id (GitHub 이메일). .env에 자동 설정됨.")
    parser.add_argument("--email", default=os.environ.get("GARMIN_EMAIL", ""))
    parser.add_argument("--password", default=os.environ.get("GARMIN_PASSWORD", ""))
    parser.add_argument("--vps", default=os.environ.get("GARMIN_VPS_URL", _DEFAULT_VPS_URL))
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument(
        "--token-only",
        action="store_true",
        help="토큰 발급만 수행하고 garmin_tokens.json으로 저장 (업로드 없이 종료)",
    )
    args = parser.parse_args()

    # 자격증명이 이미 env에 있는지 기록 (로그인 성공 후 저장 여부 결정에 사용)
    creds_from_env = bool(args.email and args.password)

    email = _prompt("Garmin 이메일", args.email)
    password = _prompt("Garmin 패스워드", args.password, secret=True)

    # 로그인 성공 시에만 이후 코드 진행 (실패 시 _garmin_login이 sys.exit)
    token = _garmin_login(email, password)

    if not creds_from_env:
        try:
            answer = input("이메일/패스워드를 .env에 저장할까요? 다음부터 자동 로그인됩니다. [y/N]: ").strip().lower()
        except EOFError:
            answer = "n"
        if answer == "y":
            _save_dotenv(email, password)

    if args.token_only:
        out = Path("garmin_tokens.json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump(token, f, indent=2)
        print(f"토큰 저장 완료: {out.resolve()}")
        return

    user_id = args.user_id
    if not user_id:
        print("오류: RUNPULSE_USER_ID 환경변수가 필요합니다.")
        print("  웹 UI(/connect/garmin)에서 .env 다운로드하면 자동 설정됩니다.")
        sys.exit(1)

    cf_id = os.environ.get("CF_SERVICE_CLIENT_ID", "")
    cf_secret = os.environ.get("CF_SERVICE_CLIENT_SECRET", "")

    if not cf_id or not cf_secret:
        print("오류: CF_SERVICE_CLIENT_ID, CF_SERVICE_CLIENT_SECRET 환경변수가 필요합니다.")
        print("  웹 UI(/connect/garmin)에서 CF Service Token 설정 후 .env 다운로드하세요.")
        sys.exit(1)

    _upload_token(args.vps, token, args.days, cf_id, cf_secret, user_id)


if __name__ == "__main__":
    main()

"""무인 실행 알림 — Telegram Bot API로 완료/차단/오류를 통지한다.

세션 내 Telegram MCP 플러그인(reply 도구)은 살아있는 대화 세션에서만 동작하므로
백그라운드 러너는 Bot API를 직접 호출한다. 토큰/허용 chat_id는
~/.claude/channels/telegram/(.env, access.json)에서 읽는다 — 이 파일들은
텔레그램 플러그인 설정이며 autopilot이 값을 바꾸지 않는다(읽기 전용).
네트워크 실패는 러너를 막지 않는다 — best-effort, 예외를 삼킨다.
"""
from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

_CHANNEL_DIR = Path.home() / ".claude" / "channels" / "telegram"
_ENV_PATH = _CHANNEL_DIR / ".env"
_ACCESS_PATH = _CHANNEL_DIR / "access.json"
_API_BASE = "https://api.telegram.org/bot{token}/sendMessage"


def _read_token() -> str | None:
    if not _ENV_PATH.exists():
        return None
    m = re.search(r"^TELEGRAM_BOT_TOKEN=(.+)$", _ENV_PATH.read_text(encoding="utf-8"), re.M)
    token = m.group(1).strip() if m else ""
    return token or None


def _read_chat_ids() -> list[str]:
    if not _ACCESS_PATH.exists():
        return []
    try:
        data = json.loads(_ACCESS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return [str(c) for c in (data.get("allowFrom") or [])]


def send(text: str) -> bool:
    """페어링된 모든 chat_id에 전송 시도. 하나라도 성공하면 True."""
    token = _read_token()
    chat_ids = _read_chat_ids()
    if not token or not chat_ids:
        return False
    ok = False
    url = _API_BASE.format(token=token)
    for chat_id in chat_ids:
        body = json.dumps({"chat_id": chat_id, "text": text}).encode("utf-8")
        req = urllib.request.Request(
            url, data=body, headers={"Content-Type": "application/json"}, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                ok = ok or resp.status == 200
        except Exception:
            continue  # best-effort — 러너를 막지 않는다
    return ok

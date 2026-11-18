"""Today 내러티브의 claude_queue 경로 — 워밍 스레드 전용(요청 스레드에서는 큐를 기다리지 않는다).

큐가 불가·실패·검증 불통과면 None 을 돌려 호출자가 기존 provider 체인 → 규칙 문장으로 내려가게 한다.
"""
from __future__ import annotations

import re
import sqlite3

MAX_LEN = 400
_NUM = re.compile(r"\d+(?:\.\d+)?")


def queue_ready(conn: sqlite3.Connection, config: dict | None) -> bool:
    from src.ai import provider_claude_queue as pcq
    return pcq.available(conn, config)


def validate_narrative(prompt: str, out: str | None) -> str | None:
    """프롬프트 근거에 없는 숫자·과도한 길이·마크다운 제목이 있으면 None."""
    if not out:
        return None
    t = out.strip()
    if not t or len(t) > MAX_LEN or t.startswith("#"):
        return None
    known = set(_NUM.findall(prompt))
    if any(n not in known for n in _NUM.findall(t)):
        return None
    return t


def narrative_via_queue(conn: sqlite3.Connection, config: dict | None, prompt: str) -> str | None:
    from src.ai import provider_claude_queue as pcq
    return validate_narrative(prompt, pcq.try_complete(conn, config, kind="narrative", prompt=prompt))

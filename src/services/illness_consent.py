"""질병 정보 AI 코치 전송 동의 (NEW-12·14~17) — illness_consent_events 추가 전용 기록, 현재 상태 = 최신 행.

동의 여부와 무관하게 에피소드 저장·로컬 조정은 동작한다. 미동의·철회면 AI 에는 '컨디션 신호'로 일반화해 보낸다.
부상(injury) 신호는 동의 대상이 아니라 항상 같은 '컨디션 신호'로 일반화한다(ADR-058 — 정도·부위·단계 미전송).
"""
from __future__ import annotations

import sqlite3

GENERIC_LABEL = "컨디션 신호"
_ACTIONS = ("grant", "decline", "revoke")
_VIA = ("first_input", "settings")


def record(conn: sqlite3.Connection, action: str, via: str) -> int:
    """동의 이벤트 1건 추가(commit 은 호출자)."""
    if action not in _ACTIONS or via not in _VIA:
        raise ValueError("invalid consent event")
    return conn.execute("INSERT INTO illness_consent_events(action, via) VALUES (?,?)", (action, via)).lastrowid


def current_action(conn: sqlite3.Connection) -> str | None:
    row = conn.execute("SELECT action FROM illness_consent_events ORDER BY id DESC LIMIT 1").fetchone()
    return row[0] if row else None


def has_consent(conn: sqlite3.Connection) -> bool:
    return current_action(conn) == "grant"


def needs_first_prompt(conn: sqlite3.Connection) -> bool:
    """첫 질병 입력에만 1회 묻는다 — 이벤트가 0건일 때만 True(거절 후 재질문 없음, NEW-17)."""
    return conn.execute("SELECT 1 FROM illness_consent_events LIMIT 1").fetchone() is None


def redact_health_for_ai(conn: sqlite3.Connection, signals: list[dict]) -> list[dict]:
    """injury 는 항상, illness 는 미동의면 '컨디션 신호' 로 일반화(value·detail 제거). 호출마다 동의 상태를 새로 조회한다."""
    hide = {"injury"} if has_consent(conn) else {"illness", "injury"}
    out = []
    for s in signals:
        if s.get("signal") in hide:
            s = {**s, "signal": "condition", "value": GENERIC_LABEL, "detail": None, "provider": "context"}
        out.append(s)
    return out


redact_illness_for_ai = redact_health_for_ai   # 이전 이름(호환)

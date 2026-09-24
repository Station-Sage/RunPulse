"""AI 채팅 컨텍스트 — 러너 자기 보고(QuickInput 체크인)."""
from __future__ import annotations
import sqlite3

_PAIN_LABELS = {"none": "없음", "mild": "경미", "moderate": "중간", "severe": "심함"}
_NOTE_MAX = 200


def build_checkin_context(conn: sqlite3.Connection, today: str) -> dict | None:
    """today 기준 최근 체크인(user_inputs) — 없거나 값이 전부 비었으면 None.

    과거(UTC 기준 저장) 체크인 행은 KST 새벽엔 서버 로컬 날짜와 하루 어긋날 수 있다 — 그래서 today가 아니라 [today-1일, today+1일] 범위에서
    가장 최근 1건을 쓴다.
    """
    row = conn.execute(
        "SELECT input_date, fatigue, pain, note FROM user_inputs"
        " WHERE input_type = 'checkin'"
        "   AND input_date BETWEEN date(?, '-1 day') AND date(?, '+1 day')"
        " ORDER BY input_date DESC LIMIT 1",
        (today, today),
    ).fetchone()
    if row is None:
        return None
    date_, fatigue, pain, note = row[0], row[1], row[2], row[3]
    if fatigue is None and not pain and not (note or "").strip():
        return None
    return {"date": date_, "fatigue": fatigue, "pain": pain, "note": note}


def format_checkin_line(checkin: dict | None) -> str | None:
    """프롬프트용 한 줄 — 예: '러너 자기 보고(2026-09-24): 피로도 6/10 | 통증 경미 | 메모 "무릎 뻐근"'."""
    if not checkin:
        return None
    parts: list[str] = []
    if checkin.get("fatigue") is not None:
        parts.append(f"피로도 {checkin['fatigue']}/10")
    pain = checkin.get("pain")
    if pain:
        parts.append(f"통증 {_PAIN_LABELS.get(pain, pain)}")
    note = (checkin.get("note") or "").strip()
    if note:
        parts.append(f'메모 "{note[:_NOTE_MAX]}"')
    if not parts:
        return None
    return f"러너 자기 보고({checkin['date']}): " + " | ".join(parts)

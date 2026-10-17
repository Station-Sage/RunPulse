"""오늘 화면용 컨텍스트 요약 (NEW-19·22) — 읽기 전용. 진행 중 에피소드·질병 재확인 배너·건강 질문 플래그."""
from __future__ import annotations

import sqlite3

from src.services import context_autodetect, context_episodes
from src.utils.reference_day import reference_today


def build(conn: sqlite3.Connection) -> dict:
    try:
        active = [e for e in context_episodes.list_all(conn) if e["end_date"] is None]
        return {"active": active, "illness_reconfirm": context_episodes.illness_reconfirm(conn),
                "health_question": context_autodetect.rhr_hrv_question(conn, reference_today(conn)[0])}
    except sqlite3.Error:
        return {"active": [], "illness_reconfirm": None, "health_question": False}

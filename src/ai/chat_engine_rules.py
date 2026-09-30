"""AI 채팅 — 규칙 기반 답변 디스패처 (30-coach-chat design §7.3).

AI가 없을 때 chip_id 핸들러(coach_rule_handlers)로 답한다. 자유 입력이나 알 수 없는 칩은
키워드로 추측하지 않고 "AI 없이는 답할 수 없다"고 정직하게 안내한다.
"""
from __future__ import annotations

import sqlite3

from .coach_rule_handlers import answer_chip, free_text_answer
from .coach_rule_types import RuleAnswer


def rule_based_response(
    conn: sqlite3.Connection,
    user_message: str = "",
    chip_id: str | None = None,
) -> RuleAnswer:
    """chip_id 핸들러 답변, 없으면 자유 입력 안내 답변."""
    if chip_id:
        answer = answer_chip(conn, chip_id)
        if answer is not None:
            return answer
    return free_text_answer(conn)

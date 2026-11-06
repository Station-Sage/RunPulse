"""GET /api/v1/library/metrics/training-balance — Training Balance Radar 6축 (07 §7d, balance-radar 설계 §6)."""
from __future__ import annotations

import sqlite3
from datetime import date

from flask import request

from src.services import training_balance_service
from src.utils.reference_day import reference_today
from src.utils.user_context import db_path

from . import api_bp, api_error, api_ok


def _parse_date(raw: str | None) -> str | None:
    """YYYY-MM-DD 만 허용. 형식 오류는 ValueError."""
    if raw is None or raw == "":
        return None
    if len(raw) != 10:
        raise ValueError(raw)
    return date.fromisoformat(raw).isoformat()


@api_bp.get("/library/metrics/training-balance")
def get_library_training_balance():
    try:
        as_of = _parse_date(request.args.get("date"))
    except ValueError:
        return api_error("INVALID_PARAM", "date는 YYYY-MM-DD 형식이어야 합니다.", 400)
    try:
        compare_days = int(request.args.get("compare_days", 28))
    except ValueError:
        return api_error("INVALID_PARAM", "compare_days는 정수여야 합니다.", 400)
    if not 0 <= compare_days <= training_balance_service.MAX_COMPARE_DAYS:
        return api_error("INVALID_PARAM", "compare_days는 0~84 범위여야 합니다.", 400)

    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)
    conn = sqlite3.connect(str(dpath))
    try:
        day = as_of or reference_today(conn)[0]
        return api_ok(training_balance_service.get_training_balance(conn, day, compare_days))
    finally:
        conn.close()

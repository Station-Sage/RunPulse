"""지표 해금 진행도 — 핵심 게이지(CTL·TSB·CIRS·UTRS)가 열리기까지 모은 일수 (REVIEW03 §2.5, D-L7).

load_span: 첫 러닝 활동부터 오늘까지의 일수(PMC·ACWR는 누적 부하 기간이 필요),
wellness_days: 웰니스 기록이 있는 날 수(UTRS는 회복 입력 기준). 임계값은 각 지표 계산식의 창 길이.
"""
from __future__ import annotations

import sqlite3
from datetime import date as _date

REQUIRED = {
    "ctl": (42, "load_span"),
    "tsb": (42, "load_span"),
    "cirs": (28, "load_span"),
    "utrs": (7, "wellness_days"),
}


def get_unlock_progress(conn: sqlite3.Connection, today: str | None = None) -> dict:
    """{ctl|tsb|cirs|utrs: {required_days, have_days, unlocked, basis}} — 데이터 없으면 have_days=0."""
    end = _date.fromisoformat(today) if today else _date.today()
    first = conn.execute(
        "SELECT MIN(substr(start_time, 1, 10)) FROM v_canonical_activities"
        " WHERE activity_type LIKE '%running%'").fetchone()[0]
    span = max(0, (end - _date.fromisoformat(first)).days + 1) if first else 0
    wellness = int(conn.execute(
        "SELECT COUNT(DISTINCT date) FROM daily_wellness WHERE date <= ?", (end.isoformat(),)).fetchone()[0] or 0)
    have = {"load_span": span, "wellness_days": wellness}
    return {
        k: {"required_days": req, "have_days": have[basis], "unlocked": have[basis] >= req, "basis": basis}
        for k, (req, basis) in REQUIRED.items()
    }

"""분해 v2 활동 scope(`@a{id}`, DESIGN-PENDING-12 §3) — 활동 단위 지표 explainer.

현재 TRIMP 1종. 값 = 시간(분) × 심박예비율 × k × e^(b·심박예비율)(Banister) —
TRIMPCalculator와 같은 입력(평균 심박·최대/안정시 심박)을 다시 읽어 항으로 펼친다.
최대심박은 측정값(athlete) → 최근 180일 활동 최대 → 190 순서(stream_utils.athlete_max_hr 규칙).
"""
from __future__ import annotations

import math
import sqlite3

from src.metrics.trimp import TRIMPCalculator
from src.utils.db_helpers import get_primary_metric


def _max_hr(conn: sqlite3.Connection, start: str) -> int:
    row = get_primary_metric(conn, "athlete", "me", "max_hr_measured")
    if row and row.get("numeric_value"):
        return int(row["numeric_value"])
    r = conn.execute(
        "SELECT MAX(max_hr) FROM activity_summaries WHERE max_hr IS NOT NULL "
        "AND substr(start_time,1,10) <= ? AND substr(start_time,1,10) > date(?, '-180 days')",
        (start[:10], start[:10]),
    ).fetchone()
    return int(r[0]) if r and r[0] else 190


def _rest_hr(conn: sqlite3.Connection, day: str) -> int:
    r = conn.execute("SELECT resting_hr FROM daily_wellness WHERE date=?", (day,)).fetchone()
    if r and r[0]:
        return int(r[0])
    r = conn.execute(
        "SELECT AVG(resting_hr) FROM daily_wellness WHERE resting_hr IS NOT NULL "
        "AND date <= ? AND date > date(?, '-7 days')",
        (day, day),
    ).fetchone()
    return int(r[0]) if r and r[0] else 60


def explain_trimp_activity(conn: sqlite3.Connection, scope_type: str, scope_id: str) -> tuple[list[dict], list[dict], str]:
    """(terms, sources, formula_text). 입력이 모자라면 terms=[] — 호출부가 v1로 폴백한다."""
    row = conn.execute(
        "SELECT name, start_time, avg_hr, COALESCE(duration_sec, moving_time_sec) AS dur "
        "FROM v_canonical_activities WHERE id=?",
        (int(scope_id),),
    ).fetchone()
    if not row or not row[2] or not row[3]:
        return [], [], ""
    name, start, avg_hr, dur = row[0], row[1], row[2], row[3]
    max_hr, rest_hr = _max_hr(conn, start), _rest_hr(conn, start[:10])
    if max_hr <= rest_hr:
        return [], [], ""
    frac = max(0.0, min(1.0, (avg_hr - rest_hr) / (max_hr - rest_hr)))
    k, b = TRIMPCalculator.COEFFS["male"]
    minutes = dur / 60.0
    terms = [
        {"slug": "duration_min", "label": "운동 시간", "raw": round(minutes, 1), "unit": "분", "role": "factor"},
        {"slug": "avg_hr", "label": "평균 심박", "raw": round(avg_hr), "unit": "bpm"},
        {"slug": "rest_hr", "label": "안정시 심박", "raw": rest_hr, "unit": "bpm"},
        {"slug": "max_hr", "label": "최대 심박", "raw": max_hr, "unit": "bpm"},
        {
            "slug": "hr_reserve", "label": "심박예비율", "raw": round(frac, 3), "unit": "ratio", "role": "factor",
            "weight": round(frac * k * math.exp(b * frac), 3),
        },
    ]
    sources = [{"type": "activity", "id": int(scope_id), "label": name or "활동", "value": round(minutes, 1), "unit": "분", "effect": ""}]
    text = "TRIMP = 시간(분) × 심박예비율 × k × e^(b × 심박예비율), 심박예비율 = (평균 − 안정시) ÷ (최대 − 안정시)"
    return terms, sources, text

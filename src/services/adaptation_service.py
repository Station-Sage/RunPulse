"""플랜 적응 상태 서비스 — 03e-coach.md 5-F "적응 상태"(ACWR·HRV·주간 피로도). 읽기 전용."""
from __future__ import annotations

import sqlite3
from datetime import date as _date

from src.metrics.acwr import ACWRCalculator

# P-10: 구간 경계는 메트릭 정의(ACWRCalculator.ranges)에서 받는다 — 화면 문구와 판정이 같은 값을 쓴다.
_RANGES = ACWRCalculator.ranges
ACWR_OPTIMAL = tuple(_RANGES["optimal"])


def _acwr_zone(v: float) -> str:
    """Gabbett 구간 — 경계 포함 규칙: low 미만 저부하, optimal 상한까지 적정, caution 상한까지 주의."""
    if v < _RANGES["optimal"][0]:
        return "저부하"
    if v <= _RANGES["optimal"][1]:
        return "적정"
    if v <= _RANGES["caution"][1]:
        return "주의"
    return "위험"


def _hrv_zone(delta_pct: float) -> str:
    """기준(주간 평균) 대비 변화율 — 5-F 목업의 'HRV 58ms ●기준 −7% (경계)'."""
    if delta_pct >= -5:
        return "정상"
    if delta_pct >= -10:
        return "경계"
    return "저하"


def get_adaptation_status(conn: sqlite3.Connection, date: str | None = None) -> dict:
    """date 기준 적응 상태. 없는 항목은 None(에러 아님).
    반환: {"date", "acwr": {"value","zone","date","optimal_range"}|None,
           "hrv": {"value","baseline","delta_pct","zone"}|None,
           "fatigue_avg": {"value","n"}|None}
    """
    if date is None:
        date = _date.today().isoformat()
    acwr = None
    row = conn.execute(
        "SELECT scope_id, numeric_value FROM metric_store"
        " WHERE scope_type = 'daily' AND metric_name = 'acwr' AND is_primary = 1"
        "   AND scope_id <= ? AND numeric_value IS NOT NULL"
        " ORDER BY scope_id DESC LIMIT 1",
        (date,),
    ).fetchone()
    if row:
        acwr = {"value": round(float(row[1]), 2), "zone": _acwr_zone(float(row[1])), "date": row[0],
                "optimal_range": list(ACWR_OPTIMAL)}
    hrv = None
    row = conn.execute(
        "SELECT hrv_last_night, hrv_weekly_avg FROM daily_wellness"
        " WHERE date <= ? AND hrv_last_night IS NOT NULL ORDER BY date DESC LIMIT 1",
        (date,),
    ).fetchone()
    if row:
        value, baseline = float(row[0]), row[1]
        delta = round((value - baseline) / baseline * 100) if baseline else None
        hrv = {
            "value": value,
            "baseline": baseline,
            "delta_pct": delta,
            "zone": _hrv_zone(delta) if delta is not None else None,
        }
    fatigue_avg = None
    row = conn.execute(
        "SELECT AVG(fatigue), COUNT(fatigue) FROM user_inputs"
        " WHERE input_type = 'checkin' AND fatigue IS NOT NULL"
        "   AND input_date BETWEEN date(?, '-6 day') AND ?",
        (date, date),
    ).fetchone()
    if row and row[1]:
        fatigue_avg = {"value": round(float(row[0]), 1), "n": int(row[1])}
    return {"date": date, "acwr": acwr, "hrv": hrv, "fatigue_avg": fatigue_avg}

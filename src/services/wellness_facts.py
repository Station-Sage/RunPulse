"""AI 다듬기 근거용 웰니스 원값 — 그날 값과 본인 7·90일 평균(당일 제외) (ADR-059 D18, 사용자 결정 2026-11-20).

수면 시간·점수, 스트레스, 안정시 심박, HRV, Body Battery 최고치만 숫자로 준다. 체크인·메모·통증·질병 기록은
넣지 않는다(건강 일반화 원칙 유지 — 이 값들은 측정 수치일 뿐 질병·부상 단어가 아니다). 표본이 적은 평균은 생략한다.
수치는 해시 안정성을 위해 화면 정밀도로 반올림한다(수면 0.1시간, 나머지 정수).
"""
from __future__ import annotations

import sqlite3
from datetime import date as _date, timedelta

# (facts 키, daily_wellness 컬럼, 변환)
FIELDS = (
    ("sleep_hours", "sleep_duration_sec", lambda v: round(v / 3600, 1)),
    ("sleep_score", "sleep_score", lambda v: int(round(v))),
    ("stress", "avg_stress", lambda v: int(round(v))),
    ("resting_hr", "resting_hr", lambda v: int(round(v))),
    ("hrv", "hrv_last_night", lambda v: int(round(v))),
    ("body_battery_max", "body_battery_high", lambda v: int(round(v))),
)
WINDOWS = ((7, 3), (90, 14))   # (일수, 최소 표본)


def _avg(conn: sqlite3.Connection, col: str, day: str, back: int, min_n: int) -> float | None:
    lo = (_date.fromisoformat(day) - timedelta(days=back)).isoformat()
    r = conn.execute(f"SELECT AVG({col}), COUNT({col}) FROM daily_wellness WHERE date >= ? AND date < ?"
                     f" AND {col} IS NOT NULL", (lo, day)).fetchone()
    return float(r[0]) if r and r[1] >= min_n and r[0] is not None else None


def wellness_facts(conn: sqlite3.Connection, day: str) -> dict:
    """day 의 웰니스 원값 + 본인 7·90일 평균. 그날 값이 없는 항목은 평균도 생략(비교 대상이 없으므로)."""
    cols = ", ".join(c for _, c, _ in FIELDS)
    try:
        row = conn.execute(f"SELECT {cols} FROM daily_wellness WHERE date=?", (day,)).fetchone()
    except sqlite3.Error:
        return {}
    if not row:
        return {}
    out: dict = {}
    for (key, col, conv), v in zip(FIELDS, row):
        if v is None:
            continue
        out[key] = conv(float(v))
        for back, min_n in WINDOWS:
            a = _avg(conn, col, day, back, min_n)
            if a is not None:
                out[f"{key}_avg_{back}d"] = conv(a)
    return out

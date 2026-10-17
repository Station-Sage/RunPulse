"""여행·고지대 자동 감지 (NEW-2·8) — 최근 활동에서 후보(origin='auto', status='candidate')만 만든다.

travel: activity 범위 metric_store.timezone_offset 숫자값(시간)을 28일 최빈값(홈)과 비교, 차이 ≥ TRAVEL_TZ_DELTA_H.
altitude: activity_streams.altitude_m 활동별 중앙값 ≥ ALTITUDE_THRESHOLD_M 이고 홈 중앙값보다 ALTITUDE_DELTA_M 이상 높음.
임계값은 제안값(구현 시 값 확인 필요). 후보는 사용자가 확정하기 전까지 신호에 쓰이지 않는다.
"""
from __future__ import annotations

import sqlite3
import statistics
from collections import Counter
from datetime import date, timedelta

from src.services import context_episodes
from src.utils.reference_day import reference_today

TRAVEL_TZ_DELTA_H = 3.5
ALTITUDE_THRESHOLD_M = 1750.0
ALTITUDE_DELTA_M = 500.0
HOME_WINDOW_DAYS = 28
RECENT_DAYS = 2
RHR_UP_BPM = 5.0
HRV_DOWN_PCT = 10.0


def _hours(v: float) -> float:
    return v / 3_600_000 if abs(v) > 24 else v


def _tz_rows(conn, start: str, end: str) -> list[tuple[str, float]]:
    rows = conn.execute(
        "SELECT substr(a.start_time,1,10), m.numeric_value FROM activity_summaries a JOIN metric_store m"
        " ON m.scope_type='activity' AND m.scope_id=CAST(a.id AS TEXT) AND m.metric_name='timezone_offset'"
        " WHERE m.numeric_value IS NOT NULL AND substr(a.start_time,1,10) BETWEEN ? AND ?", (start, end)).fetchall()
    return [(d, _hours(v)) for d, v in rows]


def detect_travel(conn: sqlite3.Connection, today: str) -> dict | None:
    t = date.fromisoformat(today)
    recent_from = (t - timedelta(days=RECENT_DAYS)).isoformat()
    base = _tz_rows(conn, (t - timedelta(days=HOME_WINDOW_DAYS)).isoformat(), (t - timedelta(days=RECENT_DAYS + 1)).isoformat())
    recent = _tz_rows(conn, recent_from, today)
    if not base or not recent:
        return None
    home = Counter(round(v * 2) / 2 for _, v in base).most_common(1)[0][0]
    cur = max(recent, key=lambda r: r[0])
    delta = cur[1] - home
    if abs(delta) < TRAVEL_TZ_DELTA_H:
        return None
    return {"from_offset": home, "to_offset": cur[1], "delta_h": round(abs(delta), 1),
            "direction": "east" if delta > 0 else "west", "start_date": cur[0]}


def _median_alt(conn, start: str, end: str) -> list[tuple[str, float]]:
    out = []
    for aid, day in conn.execute(
            "SELECT id, substr(start_time,1,10) FROM activity_summaries WHERE substr(start_time,1,10) BETWEEN ? AND ?",
            (start, end)).fetchall():
        vals = [r[0] for r in conn.execute(
            "SELECT altitude_m FROM activity_streams WHERE activity_id=? AND altitude_m IS NOT NULL", (aid,))]
        if len(vals) >= 30:
            out.append((day, statistics.median(vals)))
    return out


def detect_altitude(conn: sqlite3.Connection, today: str) -> dict | None:
    t = date.fromisoformat(today)
    base = _median_alt(conn, (t - timedelta(days=HOME_WINDOW_DAYS)).isoformat(), (t - timedelta(days=RECENT_DAYS + 1)).isoformat())
    recent = _median_alt(conn, (t - timedelta(days=RECENT_DAYS)).isoformat(), today)
    if not recent:
        return None
    home = statistics.median(v for _, v in base) if base else 0.0
    day, alt = max(recent, key=lambda r: r[1])
    if alt < ALTITUDE_THRESHOLD_M or alt - home < ALTITUDE_DELTA_M:
        return None
    return {"altitude_m": int(alt), "home_m": int(home), "start_date": day}


def rhr_hrv_question(conn: sqlite3.Connection, today: str) -> bool:
    """NEW-8: 안정시 심박↑ + HRV↓ 이면 '몸 상태 어때요?' 질문만 띄운다(질병 후보를 만들지 않음)."""
    t = date.fromisoformat(today)

    def avg(metric: str, a: int, b: int):
        r = conn.execute(
            "SELECT AVG(numeric_value) FROM metric_store WHERE scope_type='daily' AND metric_name=?"
            " AND numeric_value IS NOT NULL AND scope_id BETWEEN ? AND ?",
            (metric, (t - timedelta(days=a)).isoformat(), (t - timedelta(days=b)).isoformat())).fetchone()
        return r[0]

    out = []
    for m in ("resting_hr", "hrv_last_night"):
        recent, base = avg(m, 2, 0), avg(m, 30, 3)
        if recent is None or base is None:
            return False
        out.append((recent, base))
    (rhr, rhr_b), (hrv, hrv_b) = out
    return rhr - rhr_b >= RHR_UP_BPM and hrv_b > 0 and (hrv_b - hrv) / hrv_b * 100 >= HRV_DOWN_PCT


def run(conn: sqlite3.Connection) -> dict:
    """후보 생성(이미 진행 중인 같은 kind 가 있으면 건너뜀). commit 은 호출자."""
    today = reference_today(conn)[0]
    made = {}
    for kind, found in (("travel", detect_travel(conn, today)), ("altitude", detect_altitude(conn, today))):
        if not found:
            continue
        open_ = conn.execute("SELECT 1 FROM context_episodes WHERE kind=? AND end_date IS NULL"
                             " AND status IN ('candidate','confirmed')", (kind,)).fetchone()
        if open_:
            continue
        start = found.pop("start_date")
        made[kind] = context_episodes.open_episode(conn, kind, start_date=start, detail=found,
                                                   origin="auto", status="candidate")
    return {"created": made, "health_question": rhr_hrv_question(conn, today)}

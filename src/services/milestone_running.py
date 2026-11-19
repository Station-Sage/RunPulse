"""러닝 기록 마일스톤 탐지 — 최장거리(longest_run)·연속 훈련 주(streak_weeks) (ADR-057).

전 기간을 매번 다시 훑고 INSERT OR IGNORE 한다(멱등) — 동기화와 백필이 같은 함수를 쓴다.
날짜는 탐지한 날이 아니라 사건이 일어난 날(그 러닝의 날짜 / 그 주의 마지막 날). 러닝 군(family 'running')만.
주는 일요일 시작(Story·MCP 주별 집계와 같은 규칙).
"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from src.utils.activity_types import family_clause

LONGEST_MIN_KM = 15.0        # 이보다 짧은 '최장'은 기록하지 않는다
LONGEST_MIN_PRIOR_RUNS = 10  # 초기 이력(처음 몇 번의 러닝)마다 '최장'이 쏟아지지 않게
LONGEST_MARGIN_KM = 0.5      # GPS 오차 수준 갱신은 무시
MIN_PACE_SEC_KM = 150        # 2:30/km 보다 빠르면 차량 이동 등 오기록으로 보고 제외
STREAK_MIN_RUNS = 2          # 주 2회 이상 러닝이면 '훈련한 주'
STREAK_TIERS = (4, 8, 12, 26, 52)


def _insert(conn: sqlite3.Connection, row: dict) -> dict | None:
    cur = conn.execute("INSERT OR IGNORE INTO milestones (type, date, title, detail, activity_id)"
                       " VALUES (:type, :date, :title, :detail, :activity_id)",
                       {"detail": None, "activity_id": None, **row})
    return {**row, "id": cur.lastrowid} if cur.rowcount else None


def _runs(conn: sqlite3.Connection) -> list[tuple]:
    clause, params = family_clause("running")
    return conn.execute(
        "SELECT id, DATE(start_time), distance_m,"
        " COALESCE(avg_pace_sec_km, moving_time_sec * 1000.0 / distance_m) FROM v_canonical_activities"
        f" WHERE {clause} AND distance_m > 0 ORDER BY start_time ASC, id ASC", params).fetchall()


def detect_longest_runs(conn: sqlite3.Connection) -> list[dict]:
    """이전 모든 러닝의 최장을 LONGEST_MARGIN_KM 이상 넘고 LONGEST_MIN_KM 이상인 러닝 → longest_run."""
    out: list[dict] = []
    prior_max, prior_n = 0.0, 0
    for aid, day, dist_m, pace in _runs(conn):
        if pace is not None and 0 < pace < MIN_PACE_SEC_KM:
            continue
        km = float(dist_m) / 1000.0
        if (prior_n >= LONGEST_MIN_PRIOR_RUNS and km >= LONGEST_MIN_KM
                and km >= prior_max + LONGEST_MARGIN_KM):
            m = _insert(conn, {"type": "longest_run", "date": day, "title": f"최장거리 {km:.1f}km",
                               "detail": f"이전 최장 {prior_max:.1f}km", "activity_id": aid})
            if m:
                out.append(m)
        prior_max = max(prior_max, km)
        prior_n += 1
    return out


def week_start(d: date) -> date:
    """일요일 시작 주의 첫날."""
    return d - timedelta(days=(d.weekday() + 1) % 7)


def streak_tiers(n: int) -> bool:
    """n 주 연속이 기록할 단계인가 — 4·8·12·26·52, 이후 52주마다."""
    return n in STREAK_TIERS or (n > 52 and n % 52 == 0)


def detect_streaks(conn: sqlite3.Connection, today: str) -> list[dict]:
    """주 STREAK_MIN_RUNS 회 이상 러닝한 주가 이어진 단계 도달 → streak_weeks(날짜 = 그 주 토요일, today 이후면 보류)."""
    counts: dict[date, int] = {}
    for _, day, _, _ in _runs(conn):
        if day:
            ws = week_start(date.fromisoformat(day))
            counts[ws] = counts.get(ws, 0) + 1
    if not counts:
        return []
    out: list[dict] = []
    end_limit = date.fromisoformat(today)
    ws, last = min(counts), max(counts)
    streak, first = 0, None
    while ws <= last:
        if counts.get(ws, 0) >= STREAK_MIN_RUNS:
            streak += 1
            first = first or ws
            sat = ws + timedelta(days=6)
            if streak_tiers(streak) and sat <= end_limit:
                m = _insert(conn, {"type": "streak_weeks", "date": sat.isoformat(), "title": f"{streak}주 연속 훈련",
                                   "detail": f"{first.isoformat()} 주부터 · 주 {STREAK_MIN_RUNS}회 이상 러닝"})
                if m:
                    out.append(m)
        else:
            streak, first = 0, None
        ws += timedelta(days=7)
    return out

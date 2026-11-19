"""AI 다듬기 교차 의존 서명 — 활동 자신의 데이터를 반올림해 해시 근거로 쓴다 (ADR-059 D16).

활동 서명 = 거리(0.1km)·평균 페이스(5초)·평균 심박·랩(거리·페이스)·플랜 매칭(rematch)·피드백(RPE·메모·편집 시각,
메모는 해시만)·그 활동의 마일스톤. 이 서명이 바뀌면 그 활동의 '이 러닝의 의미'와, 서명을 의존으로 선언한
기간 이야기·그날 지표 해석이 다시 만들어진다. 서명은 해시 전용이며 AI 로 보내지 않는다.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3

from src.services.ai_wording_basis import STEP_PACE_SEC, _bucket

MAX_LAPS = 60


def _h(obj) -> str:
    return hashlib.sha1(json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()[:12]


def _pace(v) -> float | None:
    return _bucket(float(v), STEP_PACE_SEC) if v else None


def _rows(conn: sqlite3.Connection, sql: str, args: tuple) -> list[tuple]:
    try:
        return [tuple(r) for r in conn.execute(sql, args).fetchall()]
    except sqlite3.Error:
        return []


def activity_signature(conn: sqlite3.Connection, activity_id: int | None) -> str | None:
    """활동 자신의 데이터 서명(짧은 해시). 활동이 없으면 None."""
    if activity_id is None:
        return None
    a = _rows(conn, "SELECT activity_type, substr(start_time,1,10), distance_m, avg_pace_sec_km, avg_hr"
                    " FROM activity_summaries WHERE id=?", (activity_id,))
    if not a:
        return None
    typ, day, dist, pace, hr = a[0]
    laps = _rows(conn, "SELECT distance_m, avg_pace_sec_km FROM activity_laps WHERE activity_id=?"
                       " ORDER BY source, lap_index LIMIT ?", (activity_id, MAX_LAPS))
    plan = _rows(conn, "SELECT id, workout_type, distance_km FROM planned_workouts WHERE matched_activity_id=?"
                       " ORDER BY id", (activity_id,))
    fb = _rows(conn, "SELECT rpe, note, pain, pain_sites, updated_at FROM activity_feedback WHERE activity_id=?",
               (activity_id,))
    ms = _rows(conn, "SELECT type, title FROM milestones WHERE activity_id=? ORDER BY type, title", (activity_id,))
    return _h({
        "t": typ, "d": day, "km": round(dist / 1000, 1) if dist else None, "pace": _pace(pace),
        "hr": int(round(hr)) if hr else None,
        "laps": [(round(d / 1000, 1) if d else None, _pace(p)) for d, p in laps],
        "plan": plan, "fb": _h(fb) if fb else None, "ms": ms,
    })


def period_signature(conn: sqlite3.Connection, start: str, end: str) -> str:
    """[start, end] 날짜(포함) 활동들의 서명 묶음 — 기간 이야기·그날 지표 해석의 의존."""
    ids = _rows(conn, "SELECT id FROM v_canonical_activities WHERE substr(start_time,1,10) BETWEEN ? AND ?"
                      " ORDER BY start_time, id", (start, end))
    return _h([(i, activity_signature(conn, i)) for (i,) in ids])

"""Phase 7b 마일스톤 탐지 + 저장 서비스 (03a-today.md 1-D).

detect_and_store_milestones(): sync 파이프라인에서 호출, INSERT OR IGNORE로 중복 방지.
get_recent_milestones(): 읽기 전용, today_service / routes_today 에서 호출.

설계 문서: v0.3/data/phase-7-ui-renewal/DECISIONS.md [P7-DESIGN-7B-API] 항목.
"""
from __future__ import annotations

import sqlite3
from datetime import date as _date


# ── 레이스 거리 버킷 ──────────────────────────────────────────────
_RACE_BUCKETS: list[tuple[float, float, str]] = [
    (4500, 5500, "5K"),
    (9000, 11000, "10K"),
    (20000, 22500, "하프마라톤"),
    (40000, 43000, "풀마라톤"),
]

# ── 100km 단위 ─────────────────────────────────────────────────────
_DISTANCE_STEP_M = 100_000


def _is_race(name: str | None, metric_type: str | None) -> bool:
    """활동이 레이스인지 판정 — tool_exec_context._exec_get_race_history와 동일 기준."""
    if metric_type == "race":
        return True
    if name and any(kw in name for kw in ("레이스", "대회", "Race")):
        return True
    return False


def detect_and_store_milestones(
    conn: sqlite3.Connection,
    start_date: str,
    end_date: str,
) -> list[dict]:
    """start_date~end_date 범위 활동을 기준으로 마일스톤을 탐지해 INSERT OR IGNORE로 저장.

    Returns: 새로 삽입된 마일스톤 dict 목록.
    """
    inserted: list[dict] = []
    inserted += _detect_distance_thresholds(conn, start_date, end_date)
    inserted += _detect_pb(conn, start_date, end_date)
    return inserted


def get_recent_milestones(
    conn: sqlite3.Connection,
    limit: int = 10,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[dict]:
    """최근 마일스톤 목록 — ORDER BY date DESC, id DESC.

    date_from/date_to를 주면 그 범위로 제한(과거 달 조회 시 오늘 기준 "최근"이
    아니라 그 달 기준으로 스코프하기 위함 — 둘 다 없으면 기존과 동일하게 전체
    기간에서 최신순).
    """
    conn.row_factory = sqlite3.Row
    clauses = []
    params: list = []
    if date_from:
        clauses.append("date >= ?")
        params.append(date_from)
    if date_to:
        clauses.append("date <= ?")
        params.append(date_to)
    where = f"WHERE {' AND '.join(clauses)} " if clauses else ""
    rows = conn.execute(
        f"SELECT * FROM milestones {where}ORDER BY date DESC, id DESC LIMIT ?",
        (*params, limit * 5),          # 같은 날 예측 재계산이 한 줄로 합쳐지므로 넉넉히 읽고 자른다
    ).fetchall()
    from src.services.milestone_present import present_milestones
    return present_milestones([dict(r) for r in rows])[:limit]


# ── 내부 헬퍼 ─────────────────────────────────────────────────────

def _detect_distance_thresholds(
    conn: sqlite3.Connection,
    start_date: str,
    end_date: str,
) -> list[dict]:
    """100km 배수 돌파 마일스톤 탐지."""
    # start_date 이전 누적 거리
    row = conn.execute(
        "SELECT COALESCE(SUM(distance_m), 0) FROM v_canonical_activities "
        "WHERE DATE(start_time) < ?",
        (start_date,),
    ).fetchone()
    pre_total = float(row[0]) if row else 0.0

    # 범위 내 활동 순서대로 조회
    activities = conn.execute(
        "SELECT id, DATE(start_time) AS act_date, distance_m "
        "FROM v_canonical_activities "
        "WHERE DATE(start_time) >= ? AND DATE(start_time) <= ? "
        "  AND distance_m IS NOT NULL AND distance_m > 0 "
        "ORDER BY start_time ASC",
        (start_date, end_date),
    ).fetchall()

    inserted: list[dict] = []
    running_total = pre_total
    next_threshold = (_floor_div(pre_total, _DISTANCE_STEP_M) + 1) * _DISTANCE_STEP_M

    for act in activities:
        act_date = act[1] if isinstance(act, (list, tuple)) else act["act_date"]
        dist = float(act[2] if isinstance(act, (list, tuple)) else act["distance_m"])
        running_total += dist

        while running_total >= next_threshold:
            n = int(next_threshold // _DISTANCE_STEP_M)
            title = f"누적 {n * 100}km 돌파"
            m = _insert_or_ignore(conn, {
                "type": "distance_threshold",
                "date": act_date,
                "title": title,
            })
            if m:
                inserted.append(m)
            next_threshold += _DISTANCE_STEP_M

    return inserted


def _detect_pb(
    conn: sqlite3.Connection,
    start_date: str,
    end_date: str,
) -> list[dict]:
    """레이스 PB 탐지."""
    # 범위 내 활동 + workout_type_classified 조회
    activities = conn.execute(
        """
        SELECT
            a.id,
            DATE(a.start_time) AS act_date,
            a.name,
            a.distance_m,
            a.avg_pace_sec_km,
            a.elapsed_time_sec,
            (SELECT ms.text_value FROM metric_store ms
             WHERE ms.scope_type='activity' AND ms.scope_id=CAST(a.id AS TEXT)
               AND ms.metric_name='workout_type_classified' AND ms.is_primary=1
             LIMIT 1) AS workout_type
        FROM v_canonical_activities a
        WHERE DATE(a.start_time) >= ? AND DATE(a.start_time) <= ?
          AND a.distance_m IS NOT NULL
          AND a.avg_pace_sec_km IS NOT NULL
          AND a.avg_pace_sec_km > 0
        ORDER BY a.start_time ASC
        """,
        (start_date, end_date),
    ).fetchall()

    inserted: list[dict] = []
    for act in activities:
        act_id = act[0]
        act_date = act[1]
        act_name = act[2]
        dist = float(act[3])
        pace = float(act[4])
        elapsed = act[5]
        wtype = act[6]

        if not _is_race(act_name, wtype):
            continue

        bucket = _get_bucket(dist)
        if bucket is None:
            continue
        lo, hi, label = bucket

        # 같은 버킷의 이전 전체 기록 중 최고(빠른) 페이스
        best_row = conn.execute(
            """
            SELECT MIN(a2.avg_pace_sec_km)
            FROM v_canonical_activities a2
            LEFT JOIN metric_store ms
              ON ms.scope_type='activity' AND ms.scope_id=CAST(a2.id AS TEXT)
                 AND ms.metric_name='workout_type_classified' AND ms.is_primary=1
            WHERE a2.start_time < (
                  SELECT start_time FROM activity_summaries WHERE id=?
              )
              AND a2.distance_m BETWEEN ? AND ?
              AND a2.avg_pace_sec_km > 0
              AND (ms.text_value='race'
                   OR a2.name LIKE '%레이스%'
                   OR a2.name LIKE '%대회%'
                   OR a2.name LIKE '%Race%')
            """,
            (act_id, lo, hi),
        ).fetchone()

        prev_best = best_row[0] if best_row and best_row[0] is not None else None

        if prev_best is None:
            # 이전 기록 없음 → PB로 치지 않음
            continue

        if pace < prev_best:
            detail = _format_elapsed(elapsed) if elapsed else None
            m = _insert_or_ignore(conn, {
                "type": "pb",
                "date": act_date,
                "title": f"{label} PB",
                "detail": detail,
                "activity_id": act_id,
            })
            if m:
                inserted.append(m)

    return inserted


def _insert_or_ignore(conn: sqlite3.Connection, data: dict) -> dict | None:
    """milestones에 INSERT OR IGNORE. 새 행이 삽입됐으면 dict 반환, 이미 존재하면 None."""
    cur = conn.execute(
        """
        INSERT OR IGNORE INTO milestones
            (type, date, title, detail, activity_id, metric_name, old_value, new_value)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data.get("type"),
            data.get("date"),
            data.get("title"),
            data.get("detail"),
            data.get("activity_id"),
            data.get("metric_name"),
            data.get("old_value"),
            data.get("new_value"),
        ),
    )
    if cur.rowcount == 0:
        return None  # 이미 존재했음 (IGNORE)
    row_id = cur.lastrowid
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM milestones WHERE id=?", (row_id,)).fetchone()
    return dict(row) if row else None


def _floor_div(value: float, step: float) -> int:
    return int(value // step)


def _get_bucket(dist_m: float) -> tuple[float, float, str] | None:
    for lo, hi, label in _RACE_BUCKETS:
        if lo <= dist_m <= hi:
            return lo, hi, label
    return None


def _format_elapsed(elapsed_sec: int | float) -> str:
    s = int(elapsed_sec)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{sec:02d}"
    return f"{m}:{sec:02d}"

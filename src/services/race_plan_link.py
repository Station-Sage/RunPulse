"""대회 ↔ 플랜 연결 (RC-b, §2.6·§2.12) — B/C 대회 영향을 plan_adjustments 배치(source='race')로 적용·되돌린다.

배치 식별자는 signals_json[0] 에 {signal:'race_plan', race_id, batch_id} 로 둔다(컬럼 없음, S4-27).
commit 은 호출자(savepoint 안에서도 쓰이므로 내부에서 commit 하지 않는다). 확인 필요(done·대회일≥오늘) 대회는 다루지 않는다.
같은 (행, 날짜)에 다른 자동 조정이 있으면 제안 상태는 되돌리고(대회가 우선), 이미 수락된 것은 건너뛴다.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import date, timedelta

from src.services import race_calendar_query as q
from src.services.adjustment_signals_race import windows_for
from src.services.plan_adj_flag import sync_adj_flag
from src.services.plan_adjustment_rows import AUTO_SQL
from src.training.constraints import race_impact

RULE = "race_v1"
_COLS = ("id", "date", "workout_type", "distance_km", "target_pace_min", "target_pace_max", "completed",
         "matched_activity_id", "interval_prescription")


def _race(conn, race_id: int, today: str) -> dict:
    r = q.require(conn, race_id)
    if r["status"] != "planned" or q.is_needs_review(r, today):
        raise q.RaceError("NOT_APPLICABLE", "예정 상태의 대회만 플랜에 반영할 수 있습니다")
    return r


def _windows(r: dict) -> tuple[int, int]:
    return windows_for(r["priority"], r["distance_km"], r.get("taper_days"), r.get("recovery_days"))


def _label(conn, race_id) -> str:
    row = conn.execute("SELECT name, race_date FROM race_calendar WHERE id=?", (race_id,)).fetchone()
    return (row[0] or row[1]) if row else "대회"


def preview(conn: sqlite3.Connection, race_id: int, today: str) -> list[dict]:
    """적용 시 바뀔 행(오늘 이후, planner 행만) [{before, after}]. 플랜이 없거나 창에 행이 없으면 빈 리스트."""
    r = _race(conn, race_id, today)
    taper, rec = _windows(r)
    rd = date.fromisoformat(r["race_date"])
    lo = max(today, (rd - timedelta(days=taper)).isoformat())
    hi = (rd + timedelta(days=rec)).isoformat()
    rows = [dict(zip(_COLS, x)) for x in conn.execute(
        f"SELECT {', '.join(_COLS)} FROM planned_workouts WHERE source='planner' AND date BETWEEN ? AND ? ORDER BY date",
        (lo, hi))]
    return race_impact(rows, r, (taper, rec))


def apply(conn: sqlite3.Connection, race_id: int, today: str) -> dict:
    """미리보기 결과를 새 batch_id 로 한꺼번에 기록한다. 바뀐 행이 없으면 n=0 (호출자가 판단)."""
    changes = preview(conn, race_id, today)
    batch = f"race-{race_id}-{uuid.uuid4().hex[:8]}"
    goal = conn.execute("SELECT id FROM goals WHERE status='active' LIMIT 1").fetchone()
    sig = json.dumps([{"signal": "race_plan", "race_id": race_id, "batch_id": batch}])
    done, touched = 0, []
    for c in changes:
        b, a = c["before"], c["after"]
        conn.execute(
            f"UPDATE plan_adjustments SET decision='reverted', decided_at=datetime('now') WHERE workout_id=? AND date=?"
            f" AND source IN ({AUTO_SQL}) AND decision='proposed'", (b["id"], b["date"]))
        if conn.execute(f"SELECT 1 FROM plan_adjustments WHERE workout_id=? AND date=? AND source IN ({AUTO_SQL})"
                        " AND decision='accepted'", (b["id"], b["date"])).fetchone():
            continue
        fp = lambda x: {"workout_type": x["workout_type"], "distance_km": x.get("distance_km")}  # noqa: E731
        conn.execute(
            "INSERT INTO plan_adjustments(goal_id, workout_id, date, source, op, before_json, after_json, reasons_json,"
            " signals_json, rule_version, decision, decided_via, accepted_at, decided_at)"
            " VALUES (?,?,?,'race',?,?,?,?,?,?,'accepted','plan',datetime('now'),datetime('now'))",
            (goal[0] if goal else None, b["id"], b["date"], "rest" if a["workout_type"] == "rest" else "replace",
             json.dumps(fp(b)), json.dumps(fp(a)),
             json.dumps([{"key": "race", "label": f"{_label(conn, race_id)} 대회 영향"}], ensure_ascii=False), sig, RULE))
        touched.append(b["id"])
        done += 1
    sync_adj_flag(conn, touched)
    return {"batch_id": batch, "n": done}


def undo(conn: sqlite3.Connection, race_id: int) -> int:
    """이 대회의 살아 있는 race 배치를 모두 되돌린다. 되돌린 행 수."""
    ids = [(i, w) for i, w in conn.execute(
        "SELECT id, workout_id FROM plan_adjustments WHERE source='race' AND decision='accepted'"
        " AND json_extract(signals_json,'$[0].race_id') = ?", (race_id,))]
    if not ids:
        return 0
    conn.executemany("UPDATE plan_adjustments SET decision='reverted', decided_at=datetime('now'), updated_at=datetime('now')"
                     " WHERE id=?", [(i,) for i, _ in ids])
    sync_adj_flag(conn, [w for _, w in ids])
    return len(ids)


def reapply(conn: sqlite3.Connection, race_id: int, today: str) -> tuple[bool, str | None]:
    """복원 재적용(§2.12): 먼저 남은 배치를 정리하고 새 배치로 적용. 0행이면 실패(호출자 savepoint 가 롤백)."""
    undo(conn, race_id)
    res = apply(conn, race_id, today)
    return (True, None) if res["n"] else (False, "NO_ROWS")

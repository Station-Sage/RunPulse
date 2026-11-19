"""사용자 사건 마일스톤 기록·삭제 원시 함수 (ADR-057) — 호출자 트랜잭션 안에서 실행, commit 하지 않는다.

record_event/remove_event 는 예외를 삼키고(log) 실패를 False/0 으로 돌려준다 — 마일스톤 기록 실패가
대회 확인·목표 설정 같은 본 API 를 실패시키지 않게 한다. 출처 연결은 milestones.source_ref('<출처>:<id>').
"""
from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timedelta

log = logging.getLogger(__name__)

# 사용자 사건 종류(동기화 탐지 distance_threshold·pb·longest_run·streak_weeks 는 milestone_running/service)
EVENT_TYPES = ("race_finish", "goal_set", "goal_changed", "plan_replan", "race_registered",
               "illness_start", "injury_start", "recovery")


def ref(kind: str, source_id: int | str) -> str:
    """source_ref 문자열 — kind ∈ race_result·goal·race·episode·replan."""
    return f"{kind}:{source_id}"


def today_local(conn: sqlite3.Connection) -> str:
    """사용자 현지 '오늘'(reference_today). 실패하면 서버 로컬 날짜."""
    try:
        from src.utils.reference_day import reference_today
        return reference_today(conn)[0]
    except Exception:  # noqa: BLE001 — 날짜 추정 실패가 기록을 막지 않는다
        return datetime.now().strftime("%Y-%m-%d")


def local_date_of(conn: sqlite3.Connection, utc_naive: str | None, offset_sec: int | None = None) -> str | None:
    """UTC naive 'YYYY-MM-DD HH:MM:SS'(datetime('now')) → 사용자 현지 날짜. offset 없으면 서버 localtime."""
    if not utc_naive:
        return None
    if offset_sec is None:
        row = conn.execute("SELECT date(?, 'localtime')", (utc_naive,)).fetchone()
        return row[0] if row and row[0] else utc_naive[:10]
    try:
        dt = datetime.strptime(utc_naive[:19].replace("T", " "), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return utc_naive[:10]
    return (dt + timedelta(seconds=offset_sec)).strftime("%Y-%m-%d")


def user_offset(conn: sqlite3.Connection) -> int | None:
    """현지 UTC 오프셋(초) — 백필에서 created_at 을 현지 날짜로 바꿀 때 한 번만 구한다."""
    try:
        from src.utils.reference_day import reference_offset
        return reference_offset(conn)
    except Exception:  # noqa: BLE001
        return None


def _has_table(conn: sqlite3.Connection) -> bool:
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='milestones'").fetchone() is not None


def record_event(conn: sqlite3.Connection, type: str, date: str, title: str, *, detail: str | None = None,
                 activity_id: int | None = None, source_ref: str | None = None, per_day: bool = False) -> bool:
    """마일스톤 1건 기록. source_ref 가 같은 (type, source_ref) 행이 있으면 그 행을 갱신(출처 수정 반영).

    per_day=True 면 같은 날짜의 행만 갱신 대상(goal_changed — 하루 1건으로 합치고 다른 날 이력은 보존).
    UNIQUE(type, date, title) 충돌은 무시(INSERT OR IGNORE). 성공(삽입·갱신)이면 True.
    """
    try:
        if source_ref:
            sql = "SELECT id FROM milestones WHERE type=? AND source_ref=?"
            args: tuple = (type, source_ref)
            if per_day:
                sql, args = sql + " AND date=?", (*args, date)
            row = conn.execute(sql + " ORDER BY id LIMIT 1", args).fetchone()
            if row:
                try:
                    conn.execute("UPDATE milestones SET date=?, title=?, detail=?, activity_id=? WHERE id=?",
                                 (date, title, detail, activity_id, row[0]))
                except sqlite3.IntegrityError:  # 같은 (type,date,title) 행이 이미 있음 — 그 행이 대표
                    conn.execute("DELETE FROM milestones WHERE id=?", (row[0],))
                return True
        cur = conn.execute(
            "INSERT OR IGNORE INTO milestones (type, date, title, detail, activity_id, source_ref)"
            " VALUES (?,?,?,?,?,?)", (type, date, title, detail, activity_id, source_ref))
        return cur.rowcount > 0
    except Exception as exc:  # noqa: BLE001 — 본 API 를 실패시키지 않는다
        log.warning("마일스톤 기록 실패(%s %s): %s", type, source_ref, exc)
        return False


def find_event(conn: sqlite3.Connection, type: str, source_ref: str) -> dict | None:
    """(type, source_ref) 행 하나(없거나 오류면 None)."""
    try:
        r = conn.execute("SELECT id, date, title, detail FROM milestones WHERE type=? AND source_ref=?"
                         " ORDER BY id DESC LIMIT 1", (type, source_ref)).fetchone()
    except Exception:  # noqa: BLE001
        return None
    return {"id": r[0], "date": r[1], "title": r[2], "detail": r[3]} if r else None


def remove_event(conn: sqlite3.Connection, source_ref: str, types: tuple[str, ...] | None = None) -> int:
    """source_ref 가 같은 마일스톤 삭제(types 지정 시 그 종류만). 삭제 행 수, 오류면 0."""
    try:
        if types:
            ph = ",".join("?" * len(types))
            return conn.execute(f"DELETE FROM milestones WHERE source_ref=? AND type IN ({ph})",
                                (source_ref, *types)).rowcount
        return conn.execute("DELETE FROM milestones WHERE source_ref=?", (source_ref,)).rowcount
    except Exception as exc:  # noqa: BLE001
        log.warning("마일스톤 삭제 실패(%s): %s", source_ref, exc)
        return 0


# 출처 상태 → 마일스톤이 남아도 되는지. 각 SQL 은 살아 있는 출처 id 를 돌려준다.
_ALIVE = {
    "race_result": "SELECT CAST(activity_id AS TEXT) FROM race_results",
    "goal": "SELECT CAST(id AS TEXT) FROM goals WHERE status != 'cancelled'",
    "race": "SELECT CAST(id AS TEXT) FROM race_calendar WHERE status != 'cancelled'",
    "episode": "SELECT CAST(id AS TEXT) FROM context_episodes WHERE status = 'confirmed'",
    "replan": "SELECT CAST(id AS TEXT) FROM plan_replans WHERE status = 'applied'",
}


def prune_orphans(conn: sqlite3.Connection) -> int:
    """출처가 사라졌거나 취소·기각·되돌림 된 source_ref 마일스톤 삭제(동기화·백필 안전망). 삭제 행 수."""
    if not _has_table(conn):
        return 0
    n = 0
    for kind, alive_sql in _ALIVE.items():
        try:
            n += conn.execute(
                "DELETE FROM milestones WHERE source_ref LIKE ? AND substr(source_ref, ?) NOT IN (" + alive_sql + ")",
                (f"{kind}:%", len(kind) + 2)).rowcount
        except sqlite3.OperationalError:  # 출처 테이블 없음(구 스키마) — 건너뜀
            continue
    try:  # 회복 마일스톤은 에피소드가 끝나 있어야 한다
        n += conn.execute("DELETE FROM milestones WHERE type='recovery' AND source_ref LIKE 'episode:%'"
                          " AND substr(source_ref, 9) IN (SELECT CAST(id AS TEXT) FROM context_episodes"
                          " WHERE end_date IS NULL)").rowcount
    except sqlite3.OperationalError:
        pass
    return n

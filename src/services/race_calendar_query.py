"""race_calendar 조회·공통 규칙 — 행 변환, 확인 필요 판정, A 충돌·중복 검사, 구역 목록 (RC §2.2·2.4·2.8)."""
from __future__ import annotations

import sqlite3

COLS = ("id", "created_at", "updated_at", "name", "race_date", "distance_km", "priority", "goal_type", "goal_value",
        "adapt_choice", "plan_state", "cancel_prev_adapt_choice", "cancel_prev_plan_state", "taper_days",
        "recovery_days", "status", "origin", "planned_workout_id", "race_result_id", "note")
_SEL = ", ".join(COLS)


class RaceError(Exception):
    """서비스 오류. http 는 API 계층이 그대로 쓰는 상태 코드, code 는 클라이언트 분기용."""

    def __init__(self, code: str, message: str = "", http: int = 409, **extra):
        super().__init__(message or code)
        self.code, self.http, self.extra = code, http, extra


def row_dict(row) -> dict:
    return dict(zip(COLS, row))


def get(conn: sqlite3.Connection, race_id: int) -> dict | None:
    r = conn.execute(f"SELECT {_SEL} FROM race_calendar WHERE id=?", (race_id,)).fetchone()
    return row_dict(r) if r else None


def require(conn: sqlite3.Connection, race_id: int) -> dict:
    race = get(conn, race_id)
    if race is None:
        raise RaceError("NOT_FOUND", "대회를 찾을 수 없습니다", http=404)
    return race


def is_needs_review(row: dict, today: str) -> bool:
    """done 인데 대회일이 오늘 이후 — 결과 연결·신호·D-day 대상에서 제외하고 배지로 보인다(RC-33)."""
    return row["status"] == "done" and row["race_date"] >= today


def lazy_done(conn: sqlite3.Connection, today: str) -> int:
    """대회일이 지난 planned 행을 done 으로(RC-8). commit 은 호출자."""
    return conn.execute("UPDATE race_calendar SET status='done', updated_at=datetime('now')"
                        " WHERE status='planned' AND race_date < ?", (today,)).rowcount


def active_goal_race_id(conn: sqlite3.Connection) -> int | None:
    r = conn.execute("SELECT race_id FROM goals WHERE status='active' AND race_id IS NOT NULL LIMIT 1").fetchone()
    return r[0] if r else None


def is_goal_race(conn: sqlite3.Connection, race_id: int) -> bool:
    return active_goal_race_id(conn) == race_id


def find_other_a(conn: sqlite3.Connection, exclude_id: int | None = None) -> dict | None:
    """planned 또는 done 인 다른 A. 응답용 요약에 활성 목표 연결 여부를 싣는다."""
    r = conn.execute(f"SELECT {_SEL} FROM race_calendar WHERE priority='A' AND status IN ('planned','done')"
                     " AND id != ? ORDER BY status='planned' DESC, race_date DESC LIMIT 1", (exclude_id or 0,)).fetchone()
    if not r:
        return None
    a = row_dict(r)
    g = conn.execute("SELECT id FROM goals WHERE status='active' AND race_id=?", (a["id"],)).fetchone()
    a["active_goal_id"] = g[0] if g else None
    return a


def a_conflict(existing: dict) -> RaceError:
    keep = {k: existing[k] for k in ("id", "name", "race_date", "distance_km", "status", "active_goal_id")}
    return RaceError("A_CONFLICT", "이미 A 대회가 있습니다", existing_a=keep)


def check_duplicate(conn: sqlite3.Connection, race_date: str, distance_km: float, exclude_id: int | None = None) -> None:
    """같은 날짜·거리 planned 행 금지(ux_race_planned_same)."""
    r = conn.execute("SELECT id FROM race_calendar WHERE status='planned' AND race_date=? AND distance_km=?"
                     " AND id != ?", (race_date, distance_km, exclude_id or 0)).fetchone()
    if r:
        raise RaceError("DUPLICATE", "같은 날짜·거리의 예정 대회가 있습니다", duplicate_id=r[0])


def list_zones(conn: sqlite3.Connection, today: str) -> dict:
    """확인 필요 / 다가오는 / 지난 / 취소 네 구역(RC-33). 다가오는 = planned 오름차순, 지난 = done 내림차순."""
    rows = [row_dict(r) for r in conn.execute(f"SELECT {_SEL} FROM race_calendar ORDER BY race_date, id")]
    out = {"needs_review": [], "upcoming": [], "past": [], "cancelled": [], "today": today}
    for r in rows:
        if r["status"] == "cancelled":
            out["cancelled"].append(r)
        elif is_needs_review(r, today):
            out["needs_review"].append(r)
        elif r["status"] == "planned" and r["race_date"] >= today:
            out["upcoming"].append(r)
        else:
            out["past"].append(r)
    out["past"].reverse()
    out["cancelled"].reverse()
    return out

"""재계획으로 지워진 RunPulse 세션의 Garmin 캘린더 일정을 사용자 확인 후 삭제한다 (DESIGN-PLAN-A6-REPLAN-UI §13.1 D).

대상은 plan_replans.replaced_json.deleted 중 garmin_workout_id 가 있는 행(replace_range 는 source='planner' 만 지운다).
성공한 행은 JSON 의 garmin_workout_id 를 null 로 바꿔 재시도가 실패분만 다루게 한다.
"""
from __future__ import annotations

import json
import logging
import sqlite3

log = logging.getLogger(__name__)


class CleanupError(Exception):
    """code: NO_REPLAN(404) / NOT_APPLIED(409)."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _load(conn: sqlite3.Connection, replan_id: int) -> tuple[str, dict]:
    row = conn.execute("SELECT status, replaced_json FROM plan_replans WHERE id=?", (replan_id,)).fetchone()
    if row is None:
        raise CleanupError("NO_REPLAN", "재계획 기록이 없습니다")
    if row[0] != "applied":
        raise CleanupError("NOT_APPLIED", "되돌린 재계획은 Garmin 일정을 정리할 수 없습니다")
    return row[0], json.loads(row[1] or "{}")


def targets(conn: sqlite3.Connection, replan_id: int) -> list[dict]:
    """아직 지우지 않은 Garmin 일정 [{date, garmin_workout_id}] (날짜순)."""
    _, saved = _load(conn, replan_id)
    rows = [{"date": d["date"], "garmin_workout_id": str(d["garmin_workout_id"])}
            for d in saved.get("deleted", []) if d.get("garmin_workout_id")]
    return sorted(rows, key=lambda r: r["date"])


def _delete_one(client, wid: str) -> str:
    """'deleted' | 'missing'. 실패는 예외. 존재 확인 후 삭제하고, 한 번 재시도한다."""
    last: Exception | None = None
    for _ in range(2):
        try:
            try:
                client.get_workout_by_id(wid)
            except Exception as e:
                if "404" in str(e) or "not found" in str(e).lower():
                    return "missing"
                raise
            client.delete_workout(wid)
            return "deleted"
        except Exception as e:
            last = e
    raise last  # type: ignore[misc]


def cleanup(conn: sqlite3.Connection, replan_id: int, client) -> dict:
    """{deleted, missing, failed:[{date, error}]}. 행 단위 실패는 기록하고 계속 진행한다."""
    _, saved = _load(conn, replan_id)
    out = {"deleted": 0, "missing": 0, "failed": []}
    for d in saved.get("deleted", []):
        wid = d.get("garmin_workout_id")
        if not wid:
            continue
        try:
            kind = _delete_one(client, str(wid))
        except Exception as e:
            log.warning("[garmin_cleanup] %s 삭제 실패: %s", d.get("date"), e)
            out["failed"].append({"date": d.get("date"), "error": str(e)[:120]})
            continue
        out[kind] += 1
        d["garmin_workout_id"] = None
    conn.execute("UPDATE plan_replans SET replaced_json=? WHERE id=?",
                 (json.dumps(saved, ensure_ascii=False), replan_id))
    conn.commit()
    return out

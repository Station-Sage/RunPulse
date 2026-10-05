"""활동별 주관 입력(RPE·통증·메모) 저장 서비스 — activity_feedback(ADR-022).

쓰기는 캐노니컬 id 로 정규화하고 그룹당 1행을 유지한다. 읽기는 그룹 구성원 중 최신 행을 쓴다(재매칭 후에도 유지).
"""
from __future__ import annotations

import json
import sqlite3

from src.utils.canonical import canonical_activity_id, group_activity_ids

PAIN_LEVELS = ("none", "mild", "moderate", "severe")
PAIN_SITES = ("foot", "ankle", "achilles", "calf", "shin", "knee", "it_band",
              "hamstring", "quad", "hip", "lower_back", "other")
NOTE_MAX = 500
MAX_SITES = 3


class FeedbackError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def validate(payload: dict) -> dict:
    """입력 정규화: 빈 문자열→None, 부위 중복 제거·정렬. 잘못된 값은 FeedbackError."""
    rpe = payload.get("rpe")
    if rpe in ("", None):
        rpe = None
    elif isinstance(rpe, bool) or not isinstance(rpe, int) or not 1 <= rpe <= 10:
        raise FeedbackError("INVALID_RPE", "RPE 는 1~10 정수")
    pain = payload.get("pain") or None
    if pain is not None and pain not in PAIN_LEVELS:
        raise FeedbackError("INVALID_PAIN", "통증 단계가 올바르지 않음")
    sites_in = payload.get("pain_sites") or []
    if not isinstance(sites_in, list) or any(s not in PAIN_SITES for s in sites_in):
        raise FeedbackError("INVALID_SITE", "통증 부위가 올바르지 않음")
    sites = sorted(set(sites_in))
    if len(sites) > MAX_SITES:
        raise FeedbackError("INVALID_SITE", f"통증 부위는 최대 {MAX_SITES}개")
    if pain in (None, "none"):
        sites = []
    note = payload.get("note")
    note = note.strip() if isinstance(note, str) else None
    if note and len(note) > NOTE_MAX:
        raise FeedbackError("NOTE_TOO_LONG", f"메모는 {NOTE_MAX}자 이내")
    return {"rpe": rpe, "pain": pain, "pain_sites": sites, "note": note or None}


def _row_to_dict(r) -> dict:
    return {"activity_id": r[0], "rpe": r[1], "pain": r[2],
            "pain_sites": json.loads(r[3]) if r[3] else [], "note": r[4], "updated_at": r[5]}


_COLS = "activity_id, rpe, pain, pain_sites, note, updated_at"


def get_feedback(conn: sqlite3.Connection, activity_id: int) -> dict | None:
    ids = group_activity_ids(conn, activity_id)
    q = ",".join("?" * len(ids))
    row = conn.execute(f"SELECT {_COLS} FROM activity_feedback WHERE activity_id IN ({q}) "
                       "ORDER BY updated_at DESC, activity_id LIMIT 1", ids).fetchone()
    return _row_to_dict(row) if row else None


def put_feedback(conn: sqlite3.Connection, activity_id: int, payload: dict) -> dict | None:
    """저장. 활동이 없으면 LookupError. 모든 필드가 비면 삭제하고 None."""
    if not conn.execute("SELECT 1 FROM activity_summaries WHERE id=?", (activity_id,)).fetchone():
        raise LookupError(activity_id)
    data = validate(payload)
    if all(not data[k] for k in ("rpe", "pain", "pain_sites", "note")):
        delete_feedback(conn, activity_id)
        return None
    canon = canonical_activity_id(conn, activity_id)
    others = [i for i in group_activity_ids(conn, activity_id) if i != canon]
    if others:
        conn.execute(f"DELETE FROM activity_feedback WHERE activity_id IN ({','.join('?' * len(others))})", others)
    conn.execute(
        "INSERT INTO activity_feedback(activity_id, rpe, pain, pain_sites, note) VALUES (?,?,?,?,?) "
        "ON CONFLICT(activity_id) DO UPDATE SET rpe=excluded.rpe, pain=excluded.pain, "
        "pain_sites=excluded.pain_sites, note=excluded.note, updated_at=datetime('now')",
        (canon, data["rpe"], data["pain"], json.dumps(data["pain_sites"]) if data["pain_sites"] else None,
         data["note"]))
    conn.commit()
    return get_feedback(conn, canon)


def delete_feedback(conn: sqlite3.Connection, activity_id: int) -> bool:
    ids = group_activity_ids(conn, activity_id)
    cur = conn.execute(f"DELETE FROM activity_feedback WHERE activity_id IN ({','.join('?' * len(ids))})", ids)
    conn.commit()
    return cur.rowcount > 0


def feedback_for_activities(conn: sqlite3.Connection, ids: list[int]) -> dict[int, dict]:
    """목록용 일괄 조회 — 입력 id 중 피드백이 있는 것만 {id: feedback}. 그룹 구성원 행도 해당 id 로 매핑."""
    if not ids:
        return {}
    q = ",".join("?" * len(ids))
    rows = conn.execute(
        f"SELECT a.id, f.activity_id, f.rpe, f.pain, f.pain_sites, f.note, f.updated_at "
        f"FROM activity_summaries a JOIN activity_summaries m ON "
        f"COALESCE(m.matched_group_id,'solo_'||m.id) = COALESCE(a.matched_group_id,'solo_'||a.id) "
        f"JOIN activity_feedback f ON f.activity_id = m.id WHERE a.id IN ({q}) "
        "ORDER BY f.updated_at", ids).fetchall()
    return {r[0]: _row_to_dict(r[1:]) for r in rows}

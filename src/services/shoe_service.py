"""신발 쓰기 — CRUD·기본 신발 교체·merge·gear 연결·가져오기·활동 배정. 설계 shoes.md §6.

commit 은 라우트 계층이 한다(서비스는 commit 하지 않음). 규칙 위반은 ShoeError(code, message, http).
FK CASCADE 는 연결의 `PRAGMA foreign_keys` 에 의존하지 않도록 명시적으로 지운다.
기본 신발 해제(교체·은퇴) 전에는 그 신발의 기본 규칙 배정을 activity_shoe(origin='rule')로 고정해
과거 활동 마일리지가 사라지지 않게 한다(§4 `default_since` 원칙의 이력 보존).
"""
from __future__ import annotations

import sqlite3

from src.services import shoe_assignment as sa
from src.services import shoe_query as q
from src.utils.activity_types import sport_family

_EDITABLE = ("name", "brand", "model", "category", "start_date", "retire_km", "notes")


class ShoeError(Exception):
    def __init__(self, code: str, message: str, http: int = 400):
        super().__init__(message)
        self.code, self.http = code, http


def _require(conn, shoe_id: int) -> dict:
    shoe = q.require(conn, shoe_id)
    if shoe is None:
        raise ShoeError("NOT_FOUND", "신발을 찾을 수 없어요", 404)
    return shoe


def freeze_rule_history(conn: sqlite3.Connection, shoe_id: int) -> int:
    """현재 기본 규칙으로 이 신발에 배정된 활동을 rule 이력으로 고정한다."""
    rows = [(a.activity_id, shoe_id) for a in sa.resolve(conn).values()
            if a.shoe_id == shoe_id and a.method == "rule"]
    conn.executemany("INSERT OR IGNORE INTO activity_shoe (activity_id, shoe_id, origin) VALUES (?, ?, 'rule')", rows)
    return len(rows)


def _release_default(conn, kind: str, keep_id: int | None = None) -> None:
    for (sid,) in conn.execute("SELECT id FROM user_shoes WHERE default_for=? AND retired_at IS NULL AND id IS NOT ?",
                               (kind, keep_id)).fetchall():
        freeze_rule_history(conn, sid)
        conn.execute("UPDATE user_shoes SET default_for=NULL, default_since=NULL, updated_at=datetime('now')"
                     " WHERE id=?", (sid,))


def _check_dates(start: str | None, retired: str | None) -> None:
    if start and retired and retired < start:
        raise ShoeError("INVALID_PARAM", "은퇴일은 개시일 이후여야 해요")


def create(conn: sqlite3.Connection, data: dict, today: str) -> int:
    _check_dates(data.get("start_date"), None)
    kind = data.get("default_for")
    if kind:
        _release_default(conn, kind)
    cur = conn.execute(
        "INSERT INTO user_shoes (name, brand, model, category, start_date, initial_distance_m, retire_km,"
        " default_for, default_since, notes, origin) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (data["name"], data.get("brand"), data.get("model"), data.get("category") or "daily",
         data.get("start_date"), (data.get("initial_distance_km") or 0) * 1000, data.get("retire_km"),
         kind, today if kind else None, data.get("notes"), data.get("origin") or "manual"))
    return cur.lastrowid


def update(conn: sqlite3.Connection, shoe_id: int, changes: dict, today: str) -> None:
    """부분 수정. changes 의 키만 바꾼다(None = 비우기). default_for·retired_at 은 이력 고정 후 변경."""
    shoe = _require(conn, shoe_id)
    if "name" in changes and not changes["name"]:
        raise ShoeError("INVALID_PARAM", "이름은 비울 수 없어요")
    retired = changes.get("retired_at", shoe["retired_at"])
    _check_dates(changes.get("start_date", shoe["start_date"]), retired)
    sets = {k: changes[k] for k in _EDITABLE if k in changes}
    if "category" in sets and not sets["category"]:
        sets["category"] = "daily"
    if "initial_distance_km" in changes:
        sets["initial_distance_m"] = (changes["initial_distance_km"] or 0) * 1000
    kind = changes["default_for"] if "default_for" in changes else shoe["default_for"]
    if retired and kind:
        if changes.get("default_for"):  # 은퇴 상태로 기본 신발 지정 요청
            raise ShoeError("RETIRED_DEFAULT", "은퇴한 신발은 기본 신발로 지정할 수 없어요")
        kind = None  # 은퇴 → 기본 신발 해제(이력 고정)
    if kind != shoe["default_for"]:
        if shoe["default_for"]:
            freeze_rule_history(conn, shoe_id)
        if kind:
            _release_default(conn, kind, keep_id=shoe_id)
        sets.update(default_for=kind, default_since=today if kind else None)
    if "retired_at" in changes:
        sets["retired_at"] = changes["retired_at"]
    if not sets:
        return
    cols = ", ".join(f"{k}=?" for k in sets)
    conn.execute(f"UPDATE user_shoes SET {cols}, updated_at=datetime('now') WHERE id=?", [*sets.values(), shoe_id])


def delete(conn: sqlite3.Connection, shoe_id: int) -> None:
    _require(conn, shoe_id)
    conn.execute("DELETE FROM activity_shoe WHERE shoe_id=?", (shoe_id,))
    conn.execute("UPDATE gear SET shoe_id=NULL WHERE shoe_id=?", (shoe_id,))
    conn.execute("DELETE FROM user_shoes WHERE id=?", (shoe_id,))


def merge(conn: sqlite3.Connection, target_id: int, source_id: int) -> None:
    """source 신발을 target 으로 흡수 — gear 링크·배정 이관, 시작 거리는 큰 값, 기본 신발은 비어 있으면 승계."""
    if target_id == source_id:
        raise ShoeError("INVALID_PARAM", "같은 신발끼리는 합칠 수 없어요")
    target, source = _require(conn, target_id), _require(conn, source_id)
    conn.execute("UPDATE gear SET shoe_id=? WHERE shoe_id=?", (target_id, source_id))
    conn.execute("UPDATE activity_shoe SET shoe_id=? WHERE shoe_id=?", (target_id, source_id))
    conn.execute("DELETE FROM user_shoes WHERE id=?", (source_id,))
    sets = {"initial_distance_m": max(target["initial_distance_m"] or 0, source["initial_distance_m"] or 0)}
    if source["default_for"] and not target["default_for"] and not target["retired_at"] \
            and not conn.execute("SELECT 1 FROM user_shoes WHERE default_for=? AND retired_at IS NULL",
                                 (source["default_for"],)).fetchone():
        sets.update(default_for=source["default_for"], default_since=source["default_since"])
    cols = ", ".join(f"{k}=?" for k in sets)
    conn.execute(f"UPDATE user_shoes SET {cols}, updated_at=datetime('now') WHERE id=?", [*sets.values(), target_id])


def link_gear(conn: sqlite3.Connection, shoe_id: int, gear_id: int) -> None:
    _require(conn, shoe_id)
    row = conn.execute("SELECT shoe_id FROM gear WHERE id=?", (gear_id,)).fetchone()
    if row is None:
        raise ShoeError("NOT_FOUND", "장비를 찾을 수 없어요", 404)
    if row[0] is not None and row[0] != shoe_id:
        raise ShoeError("GEAR_LINKED", "이 장비는 이미 다른 신발에 연결돼 있어요", 409)
    conn.execute("UPDATE gear SET shoe_id=? WHERE id=?", (shoe_id, gear_id))


def unlink_gear(conn: sqlite3.Connection, shoe_id: int, gear_id: int) -> None:
    cur = conn.execute("UPDATE gear SET shoe_id=NULL WHERE id=? AND shoe_id=?", (gear_id, shoe_id))
    if cur.rowcount == 0:
        raise ShoeError("NOT_FOUND", "이 신발에 연결된 장비가 아니에요", 404)


def import_gear(conn: sqlite3.Connection, today: str) -> dict:
    """미연결 신발 gear → 신발 생성(정규화 이름이 같으면 한 켤레, 기존 신발과 같으면 연결만). 멱등."""
    existing = {q.normalize_name(n): sid for sid, n in conn.execute("SELECT id, name FROM user_shoes")}
    created = linked = 0
    for sug in q.suggestions(conn):
        ph = ",".join("?" * len(sug["gear_ids"]))
        gears = conn.execute(f"SELECT brand, model, status FROM gear WHERE id IN ({ph})", sug["gear_ids"]).fetchall()
        key = q.normalize_name(sug["name"])
        sid = existing.get(key)
        if sid is None:
            brand = next((g[0] for g in gears if g[0]), None)
            model = next((g[1] for g in gears if g[1]), None)
            sid = create(conn, {"name": sug["name"][:60], "brand": brand, "model": model, "origin": "gear"}, today)
            if all((g[2] or "active") != "active" for g in gears):
                conn.execute("UPDATE user_shoes SET retired_at=? WHERE id=?", (today, sid))
            existing[key] = sid
            created += 1
        conn.execute(f"UPDATE gear SET shoe_id=? WHERE id IN ({ph})", [sid, *sug["gear_ids"]])
        linked += len(sug["gear_ids"])
    return {"created": created, "linked": linked}


def _activity(conn, activity_id: int):
    return conn.execute("SELECT activity_type, source FROM activity_summaries WHERE id=?", (activity_id,)).fetchone()


def _group_ids(conn, activity_id: int) -> list[int]:
    from src.utils.canonical import group_activity_ids
    return group_activity_ids(conn, activity_id)


def set_activity_shoe(conn: sqlite3.Connection, activity_id: int, shoe_id: int | None) -> None:
    """수동 배정(shoe_id None = '신발 없음' 명시). 그룹 내 기존 배정 행은 지우고 canonical id 에 1행."""
    row = _activity(conn, activity_id)
    if row is None:
        raise ShoeError("NOT_FOUND", "활동을 찾을 수 없어요", 404)
    if sport_family(row[0], row[1]) != "running":
        raise ShoeError("NOT_RUNNING", "러닝 활동에만 신발을 지정할 수 있어요")
    if shoe_id is not None:
        _require(conn, shoe_id)
    from src.utils.canonical import canonical_activity_id
    ids = _group_ids(conn, activity_id)
    conn.execute(f"DELETE FROM activity_shoe WHERE activity_id IN ({','.join('?' * len(ids))})", ids)
    conn.execute("INSERT INTO activity_shoe (activity_id, shoe_id, origin) VALUES (?, ?, 'manual')",
                 (canonical_activity_id(conn, activity_id), shoe_id))


def clear_activity_shoe(conn: sqlite3.Connection, activity_id: int) -> None:
    """수동 배정 해제 → 자동 규칙으로 복귀(rule 이력은 유지)."""
    if _activity(conn, activity_id) is None:
        raise ShoeError("NOT_FOUND", "활동을 찾을 수 없어요", 404)
    ids = _group_ids(conn, activity_id)
    conn.execute(f"DELETE FROM activity_shoe WHERE origin='manual' AND activity_id IN ({','.join('?' * len(ids))})",
                 ids)


def assign_bulk(conn: sqlite3.Connection, shoe_id: int, activity_ids: list[int]) -> dict:
    _require(conn, shoe_id)
    assigned = skipped_non_running = missing = 0
    for aid in activity_ids:
        try:
            set_activity_shoe(conn, aid, shoe_id)
            assigned += 1
        except ShoeError as exc:
            if exc.code == "NOT_RUNNING":
                skipped_non_running += 1
            else:
                missing += 1
    return {"assigned": assigned, "skipped_non_running": skipped_non_running, "skipped_missing": missing}

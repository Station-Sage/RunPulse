"""원본 payload 조회 도구 실행기 — source_payloads 목록·본문(경로 선택·길이 제한). 로컬 전용."""
from __future__ import annotations

import json
import sqlite3

MAX_CHARS = 6000
_MAX_LIST = 50


def _exec_list_raw_payloads(conn: sqlite3.Connection, args: dict) -> dict:
    where, params = [], []
    for col in ("source", "entity_type", "entity_id", "activity_id"):
        if args.get(col) not in (None, ""):
            where.append(f"{col}=?")
            params.append(args[col])
    if args.get("date_from"):
        where.append("entity_date>=?")
        params.append(args["date_from"])
    if args.get("date_to"):
        where.append("entity_date<=?")
        params.append(args["date_to"])
    limit = min(int(args.get("limit", 20)), _MAX_LIST)
    sql = ("SELECT id, source, entity_type, entity_id, entity_date, activity_id, length(payload), fetched_at"
           " FROM source_payloads" + (" WHERE " + " AND ".join(where) if where else "")
           + " ORDER BY COALESCE(entity_date,'') DESC, id DESC LIMIT ?")
    rows = conn.execute(sql, params + [limit]).fetchall()
    return {"fields": ["id", "source", "entity_type", "entity_id", "entity_date", "activity_id", "bytes", "fetched_at"],
            "rows": [list(r) for r in rows]}


def _walk(obj, path: str):
    for part in [p for p in path.split(".") if p]:
        if isinstance(obj, list) and part.isdigit():
            obj = obj[int(part)]
        elif isinstance(obj, dict) and part in obj:
            obj = obj[part]
        else:
            raise KeyError(f"경로 없음: {path} ('{part}')")
    return obj


def _shape(obj, depth: int = 2):
    if isinstance(obj, dict):
        return {k: (_shape(v, depth - 1) if depth > 0 else type(v).__name__) for k, v in obj.items()}
    if isinstance(obj, list):
        return [f"list[{len(obj)}]", _shape(obj[0], depth - 1)] if obj and depth > 0 else f"list[{len(obj)}]"
    return type(obj).__name__


def _exec_get_raw_payload(conn: sqlite3.Connection, args: dict) -> dict:
    pid = args.get("id")
    if pid is None:
        return {"error": "id 필요 (list_raw_payloads 로 먼저 조회)"}
    row = conn.execute("SELECT source, entity_type, entity_id, entity_date, payload FROM source_payloads WHERE id=?",
                       (int(pid),)).fetchone()
    if not row:
        return {"error": f"payload {pid} 없음"}
    meta = {"id": int(pid), "source": row[0], "entity_type": row[1], "entity_id": row[2], "entity_date": row[3]}
    try:
        data = json.loads(row[4])
    except ValueError:
        return {**meta, "raw": row[4][:MAX_CHARS], "truncated": len(row[4]) > MAX_CHARS}
    path = args.get("path") or ""
    try:
        sub = _walk(data, path)
    except (KeyError, IndexError) as exc:
        return {**meta, "error": str(exc), "shape": _shape(data)}
    text = json.dumps(sub, ensure_ascii=False, default=str, separators=(",", ":"))
    limit = min(int(args.get("max_chars", MAX_CHARS)), 20000)
    if len(text) <= limit:
        return {**meta, "path": path, "data": sub}
    return {**meta, "path": path, "truncated": True, "total_chars": len(text), "shape": _shape(sub),
            "head": text[:limit], "hint": "path 로 하위 키를 좁혀 다시 조회"}

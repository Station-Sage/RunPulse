"""마일스톤 조회 — 표시 필터(블랙리스트)·전체 이력 페이지네이션·종류별 상한 (ADR-057).

표시 필터는 내부 사건만 뺀다(algo_recompute·metric_recompute, 검토 중 provider) — 새 종류는 따로 등록하지 않아도 보인다.
"""
from __future__ import annotations

import re
import sqlite3

HIDDEN_TYPES = ("algo_recompute", "metric_recompute")
_CURSOR = re.compile(r"^(\d{4}-\d{2}-\d{2}):(\d+)$")
_TYPE = re.compile(r"^[a-z_]{1,32}$")
_FIELDS = "id, type, date, title, detail, activity_id"


def visible_clauses() -> list[str]:
    """사용자에게 보이는 마일스톤 WHERE 조건(AND 로 묶음)."""
    hidden = ",".join(f"'{t}'" for t in HIDDEN_TYPES)
    return [f"type NOT IN ({hidden})",
            "(provider IS NULL OR (provider NOT LIKE '%:shadow%' AND provider NOT LIKE '%:ref\\_%' ESCAPE '\\'))"]


def parse_types(raw: str | None) -> list[str] | None:
    """'a,b' → ['a','b'] (빈 값은 None). 형식이 틀린 항목이 있으면 ValueError."""
    if not raw:
        return None
    out = [t.strip() for t in raw.split(",") if t.strip()]
    if not out or any(not _TYPE.fullmatch(t) for t in out):
        raise ValueError(raw)
    return out


def parse_cursor(raw: str | None) -> tuple[str, int] | None:
    """'YYYY-MM-DD:id' → (date, id). 형식 오류는 ValueError."""
    if not raw:
        return None
    m = _CURSOR.fullmatch(raw)
    if not m:
        raise ValueError(raw)
    return m.group(1), int(m.group(2))


def list_milestones(conn: sqlite3.Connection, *, types: list[str] | None = None,
                    before: tuple[str, int] | None = None, limit: int = 50) -> dict:
    """전체 이력(최신순). 반환 {items, next_before, type_counts}. next_before 는 다음 페이지 커서(없으면 None)."""
    where = visible_clauses()
    params: list = []
    if types:
        where.append(f"type IN ({','.join('?' * len(types))})")
        params += types
    page_where = list(where)
    page_params = list(params)
    if before:
        page_where.append("(date < ? OR (date = ? AND id < ?))")
        page_params += [before[0], before[0], before[1]]
    rows = conn.execute(
        f"SELECT {_FIELDS} FROM milestones WHERE {' AND '.join(page_where)} ORDER BY date DESC, id DESC LIMIT ?",
        (*page_params, limit + 1)).fetchall()
    keys = [k.strip() for k in _FIELDS.split(",")]
    items = [dict(zip(keys, r)) for r in rows[:limit]]
    nxt = f"{items[-1]['date']}:{items[-1]['id']}" if len(rows) > limit and items else None
    counts = conn.execute(
        f"SELECT type, COUNT(*) FROM milestones WHERE {' AND '.join(visible_clauses())}"
        " GROUP BY type ORDER BY COUNT(*) DESC, type").fetchall()
    return {"items": items, "next_before": nxt, "type_counts": [{"type": t, "count": n} for t, n in counts]}


def diversify(items: list[dict], *, per_type: int = 2, total: int = 8) -> list[dict]:
    """최신순 목록에서 종류별 per_type 건까지만 남기고 total 로 자른다(순서 유지).

    한 달에 목표 수정·대회 등록이 몰려도 누적 거리·PB 같은 기록이 밀려나지 않게 한다.
    """
    seen: dict[str, int] = {}
    out: list[dict] = []
    for m in items:
        t = m.get("type") or ""
        if seen.get(t, 0) >= per_type:
            continue
        seen[t] = seen.get(t, 0) + 1
        out.append(m)
        if len(out) >= total:
            break
    return out

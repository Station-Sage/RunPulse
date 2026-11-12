"""신발 조회 — 목록·상세·배정 활동·미배정·Today 알림·활동 칩(읽기 전용). 설계 shoes.md §5·§6.

마일리지 = 시작 거리 + 배정된 canonical 러닝 거리 합(소스 누적값은 비교로만 노출, Q4).
"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from src.services import shoe_assignment as sa
from src.services import shoe_status as st

_COLS = ("id, name, brand, model, category, start_date, initial_distance_m, retire_km, default_for,"
         " default_since, retired_at, origin, notes, created_at")


def days_to_race(conn: sqlite3.Connection, today: str) -> int | None:
    row = conn.execute("SELECT MIN(race_date) FROM goals WHERE status='active' AND race_date >= ?",
                       (today,)).fetchone()
    if not row or not row[0]:
        return None
    return (date.fromisoformat(row[0][:10]) - date.fromisoformat(today)).days


def _rows(conn, where: str = "", params=()) -> list[dict]:
    cur = conn.execute(f"SELECT {_COLS} FROM user_shoes {where}", params)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def shoe_view(shoe: dict, stat: dict | None, race_days: int | None) -> dict:
    stat = stat or {"count": 0, "assigned_m": 0.0, "last_used": None, "by_method": {}}
    mileage = round((shoe["initial_distance_m"] or 0) / 1000 + stat["assigned_m"] / 1000, 1)
    state = st.shoe_state(shoe["category"], shoe["retire_km"], shoe["retired_at"], mileage, race_days)
    return {
        "id": shoe["id"], "name": shoe["name"], "brand": shoe["brand"], "model": shoe["model"],
        "category": shoe["category"], "category_label": st.CATEGORY_LABELS.get(shoe["category"], "기타"),
        "start_date": shoe["start_date"], "initial_km": round((shoe["initial_distance_m"] or 0) / 1000, 1),
        "retire_km_custom": shoe["retire_km"], "default_for": shoe["default_for"],
        "default_since": shoe["default_since"], "retired_at": shoe["retired_at"], "origin": shoe["origin"],
        "notes": shoe["notes"], "mileage_km": mileage, "activity_count": stat["count"],
        "last_used": stat["last_used"], **state,
    }


_SOURCE_LABEL = {"strava": "Strava", "strava_export": "Strava", "garmin": "Garmin",
                 "intervals": "Intervals", "runalyze": "Runalyze"}


def gear_label(source: str | None, source_gear_id: str | None, name: str | None) -> str:
    """gear 표시 이름. 이름이 없으면(Intervals 숫자 id 등 — 소스가 이름을 안 줌) `<소스> 신발 #<소스 id>`.

    이름 없는 gear 가 모두 '이름 없는 신발' 로 보이고, 가져오기 때 같은 이름의 신발로 여러 켤레 생기던 문제를 막는다.
    """
    if name and name.strip():
        return name
    label = _SOURCE_LABEL.get(source or "", source or "소스")
    return f"{label} 신발 #{source_gear_id}" if source_gear_id else "이름 없는 신발"


def suggestions(conn: sqlite3.Connection) -> list[dict]:
    """미연결 신발 gear 를 정규화 이름으로 묶은 가져오기 제안."""
    groups: dict[str, dict] = {}
    for gid, src, sgid, name, dist in conn.execute(
            "SELECT id, source, source_gear_id, name, total_distance_m FROM gear WHERE shoe_id IS NULL"
            " AND COALESCE(gear_type,'shoes')='shoes' ORDER BY id"):
        key = normalize_name(name) or f"#{gid}"
        g = groups.setdefault(key, {"name": gear_label(src, sgid, name), "sources": [], "gear_ids": [], "total_km": 0.0})
        g["gear_ids"].append(gid)
        if src not in g["sources"]:
            g["sources"].append(src)
        g["total_km"] = round(max(g["total_km"], (dist or 0) / 1000), 1)
    return list(groups.values())


def normalize_name(name: str | None) -> str:
    return "".join((name or "").lower().split())


def list_shoes(conn: sqlite3.Connection, today: str, include_retired: bool = True) -> dict:
    shoes = _rows(conn)
    stats, unassigned = sa.aggregate(sa.resolve(conn))
    race_days = days_to_race(conn, today)
    views = sorted((shoe_view(s, stats.get(s["id"]), race_days) for s in shoes), key=st.sort_key)
    active = [v for v in views if v["status"] != "retired"]
    return {
        "shoes": views if include_retired else active,
        "retired_count": len(views) - len(active),
        "unassigned_count": unassigned,
        "headline": st.headline(active) if active else None,
        "suggestions": suggestions(conn),
    }


def require(conn: sqlite3.Connection, shoe_id: int) -> dict | None:
    rows = _rows(conn, "WHERE id=?", (shoe_id,))
    return rows[0] if rows else None


def get_shoe(conn: sqlite3.Connection, shoe_id: int, today: str) -> dict | None:
    shoe = require(conn, shoe_id)
    if shoe is None:
        return None
    assigns = [a for a in sa.resolve(conn).values() if a.shoe_id == shoe_id]
    stat = sa.aggregate({a.activity_id: a for a in assigns})[0].get(shoe_id)
    view = shoe_view(shoe, stat, days_to_race(conn, today))
    by = (stat or {}).get("by_method", {})
    monthly: dict[str, float] = {}
    for a in assigns:
        monthly[a.date[:7]] = monthly.get(a.date[:7], 0.0) + a.distance_m / 1000
    sources = [{"gear_id": gid, "source": src, "name": gear_label(src, sgid, name),
                "total_km": round((dist or 0) / 1000, 1)}
               for gid, src, sgid, name, dist in conn.execute(
                   "SELECT id, source, source_gear_id, name, total_distance_m FROM gear WHERE shoe_id=? ORDER BY source",
                   (shoe_id,))]
    view.update({
        "breakdown": {"initial_km": view["initial_km"],
                      "assigned_km": round(((stat or {}).get("assigned_m") or 0) / 1000, 1),
                      "by_method": {k: round(by.get(k, 0.0) / 1000, 1) for k in ("manual", "source", "rule")}},
        "sources": sources,
        "monthly_km": [{"month": m, "km": round(v, 1)} for m, v in sorted(monthly.items())],
        "conflict_count": sum(1 for a in assigns if a.conflict),
    })
    return view


def _activity_rows(conn, assigns: list[sa.Assignment], shoes: dict[int, dict]) -> list[dict]:
    from src.services.activity_list_rows import enrich_rows
    if not assigns:
        return []
    ids = [a.activity_id for a in assigns]
    prev, conn.row_factory = conn.row_factory, sqlite3.Row
    try:
        rows = {r["id"]: dict(r) for r in conn.execute(
            f"SELECT * FROM v_canonical_activities WHERE id IN ({','.join('?' * len(ids))})", ids)}
    finally:
        conn.row_factory = prev
    out = []
    for a in assigns:
        row = rows.get(a.activity_id)
        if row is None:
            continue
        row.update({"method": a.method, "method_source": method_source(a), "conflict": a.conflict,
                    "conflict_sources": conflict_sources(a, shoes) if a.conflict else []})
        out.append(row)
    enrich_rows(conn, out)
    return out


def method_source(a: sa.Assignment) -> str | None:
    """method='source' 일 때 채택된 소스(우선순위 1위) 이름 — 태그 "Garmin" 등."""
    return next(iter(a.by_source), None) if a.method == "source" else None


def conflict_sources(a: sa.Assignment, shoes: dict[int, dict]) -> list[dict]:
    return [{"source": src, "shoe_id": sid, "name": (shoes.get(sid) or {}).get("name")}
            for src, sid in a.by_source.items()]


def _page(assigns: list[sa.Assignment], cursor: int, limit: int):
    assigns.sort(key=lambda a: (a.date, a.activity_id), reverse=True)
    chunk = assigns[cursor:cursor + limit]
    nxt = cursor + limit if cursor + limit < len(assigns) else None
    return chunk, nxt, len(assigns)


def shoe_activities(conn: sqlite3.Connection, shoe_id: int, cursor: int = 0, limit: int = 30) -> dict:
    shoes = sa.load_shoes(conn)
    assigns = [a for a in sa.resolve(conn, shoes=shoes).values() if a.shoe_id == shoe_id]
    chunk, nxt, total = _page(assigns, cursor, limit)
    return {"activities": _activity_rows(conn, chunk, shoes), "next_cursor": nxt, "total": total}


def unassigned_activities(conn: sqlite3.Connection, cursor: int = 0, limit: int = 50) -> dict:
    shoes = sa.load_shoes(conn)
    assigns = [a for a in sa.resolve(conn, shoes=shoes).values() if a.method == "none"]
    chunk, nxt, total = _page(assigns, cursor, limit)
    return {"activities": _activity_rows(conn, chunk, shoes), "next_cursor": nxt, "total": total}


def activity_shoe_view(conn: sqlite3.Connection, activity_id: int) -> dict | None:
    """활동 상세 칩용. 비러닝은 None, 러닝 미배정은 id=None."""
    a = sa.resolve_one(conn, activity_id)
    if a is None:
        return None
    shoes = sa.load_shoes(conn)
    shoe = shoes.get(a.shoe_id) if a.shoe_id is not None else None
    status = None
    if shoe:
        assigned = sum(v.distance_m for v in sa.resolve(conn, shoes=shoes).values() if v.shoe_id == shoe["id"])
        mileage = (shoe["initial_distance_m"] or 0) / 1000 + assigned / 1000
        status = st.shoe_state(shoe["category"], shoe["retire_km"], shoe["retired_at"], mileage)["status"]
    return {"id": a.shoe_id, "name": shoe["name"] if shoe else None, "status": status, "method": a.method,
            "source": method_source(a), "conflict": a.conflict, "conflict_sources": conflict_sources(a, shoes) if a.conflict else []}


def today_alert(conn: sqlite3.Connection, today: str) -> dict | None:
    """Q3 — replace(≥100%) 이면서 최근 7일 안에 신은 활성 신발 1개(가장 많이 넘긴 것)."""
    since = (date.fromisoformat(today) - timedelta(days=7)).isoformat()
    data = list_shoes(conn, today, include_retired=False)
    hits = [s for s in data["shoes"] if s["status"] == "replace" and (s["last_used"] or "") >= since]
    if not hits:
        return None
    top = min(hits, key=lambda s: s["remaining_km"])
    return {"id": top["id"], "name": top["name"], "message": top["message"]}

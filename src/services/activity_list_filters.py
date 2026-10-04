"""활동 목록 필터·정렬 SQL 조립 (UX 리뷰 20 §7-2 ④, B-3 공용).

목록·facets·summary가 같은 필터 규칙을 쓰도록 한 곳에서 WHERE를 만든다. 읽기 전용.
type 키(API)와 저장된 workout_type_classified 값의 대응은 TYPE_CLASSES가 유일한 출처다.
"""
from __future__ import annotations

import re
import sqlite3
from typing import Any

from src.utils.activity_types import normalize_activity_type

TYPE_CLASSES: dict[str, tuple[str, ...]] = {
    "race": ("race",),
    "interval": ("interval", "sprint", "repetition"),
    "tempo": ("tempo", "threshold"),
    "long": ("long_run", "long"),
    "easy": ("easy", "steady"),
    "recovery": ("recovery",),
}
SPORT_LABELS = {"running": "러닝", "cycling": "사이클", "swimming": "수영", "walking": "걷기/하이킹",
                "strength": "근력"}
LOAD_METRIC = ("hrss", "runpulse:formula_v1")
_MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
SORT_COLUMNS = {"date": "start_time", "distance": "distance_m", "pace": "avg_pace_sec_km", "load": "load"}
_LOAD_SQL = ("(SELECT numeric_value FROM metric_store WHERE scope_type='activity' AND scope_id=CAST(v_canonical_activities.id AS TEXT)"
             " AND metric_name='hrss' AND provider LIKE 'runpulse%' LIMIT 1)")


def parse_args(args: Any) -> dict:
    """request.args 유사 매핑 → 필터 dict. 잘못된 값은 ValueError."""
    f: dict = {}
    for src, dst in (("sport", "activity_type"), ("from", "date_from"), ("to", "date_to"),
                     ("search", "search"), ("q", "q"), ("sport_group", "sport_group"), ("type", "type"),
                     ("month", "month")):
        if args.get(src):
            f[dst] = args[src]
    if f.get("type") and f["type"] not in TYPE_CLASSES:
        raise ValueError("type")
    if f.get("month") and not _MONTH_RE.match(f["month"]):
        raise ValueError("month")
    if args.get("dist_min"):
        f["min_distance_m"] = float(args["dist_min"]) * 1000
    return f


def sport_types(conn: sqlite3.Connection, group: str) -> list[str]:
    """정규화 그룹(running 등)에 속하는 raw activity_type 목록."""
    rows = conn.execute("SELECT DISTINCT activity_type, source FROM v_canonical_activities").fetchall()
    return sorted({r[0] for r in rows if normalize_activity_type(r[0], r[1]) == group})


def build_where(conn: sqlite3.Connection, filters: dict, skip: tuple[str, ...] = ()) -> tuple[str, list]:
    """(WHERE 절 문자열, 파라미터). skip은 facet 계산 시 제외할 필터 키."""
    cl: list[str] = []
    p: list[Any] = []
    f = {k: v for k, v in filters.items() if k not in skip}
    if f.get("activity_type"):
        cl.append("activity_type = ?"); p.append(f["activity_type"])
    if f.get("sport_group"):
        raws = sport_types(conn, f["sport_group"]) or ["__none__"]
        cl.append(f"activity_type IN ({','.join('?' * len(raws))})"); p.extend(raws)
    if f.get("date_from"):
        cl.append("start_time >= ?"); p.append(f["date_from"])
    if f.get("date_to"):
        cl.append("start_time <= ?"); p.append(f["date_to"])
    if f.get("month"):
        cl.append("substr(start_time,1,7) = ?"); p.append(f["month"])
    if f.get("min_distance_m") is not None:
        cl.append("distance_m >= ?"); p.append(f["min_distance_m"])
    if f.get("search"):
        cl.append("name LIKE ?"); p.append(f"%{f['search']}%")
    if f.get("q"):
        cl.append("(name LIKE ? OR start_time LIKE ? OR description LIKE ?)")
        p.extend([f"%{f['q']}%"] * 3)
    if f.get("type"):
        vals = TYPE_CLASSES[f["type"]]
        cl.append("CAST(id AS TEXT) IN (SELECT scope_id FROM metric_store WHERE scope_type='activity'"
                  f" AND metric_name='workout_type_classified' AND text_value IN ({','.join('?' * len(vals))}))")
        p.extend(vals)
    return ((" WHERE " + " AND ".join(cl)) if cl else ""), p


def order_clause(sort: str | None, sort_by: str, sort_dir: str) -> str:
    """sort(date|distance|pace|load)가 있으면 우선. pace는 빠른 순(ASC), 나머지는 DESC. 값 없는 행은 뒤로."""
    if sort not in SORT_COLUMNS:
        return f" ORDER BY {sort_by} {sort_dir}"
    expr = _LOAD_SQL if sort == "load" else SORT_COLUMNS[sort]
    direction = "ASC" if sort == "pace" else "DESC"
    return f" ORDER BY ({expr}) IS NULL, {expr} {direction}, start_time DESC"

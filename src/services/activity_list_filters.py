"""활동 목록 필터·정렬 SQL 조립 (UX 리뷰 20 §7-2 ④, B-3 공용).

목록·facets·summary가 같은 필터 규칙을 쓰도록 한 곳에서 WHERE를 만든다. 읽기 전용.
type 키(API)와 저장된 workout_type_classified 값의 대응은 TYPE_CLASSES가 유일한 출처다.
"""
from __future__ import annotations

import math
import re
import sqlite3
from datetime import date
from typing import Any

from src.utils.activity_types import FAMILIES, SPORT_LABELS, normalize_activity_type, sport_family  # noqa: F401 (re-export)

TYPE_CLASSES: dict[str, tuple[str, ...]] = {
    "race": ("race",),
    "interval": ("interval", "sprint", "repetition"),
    "tempo": ("tempo", "threshold"),
    "long": ("long_run", "long"),
    "easy": ("easy", "steady"),
    "recovery": ("recovery",),
}
LOAD_METRIC = ("hrss", "runpulse:formula_v1")
_MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
# from/to: 날짜, 또는 날짜 + 시각(프론트가 to 에 ' 23:59:59' 를 붙인다)
_DATE_TIME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})([ T]\d{2}:\d{2}(:\d{2})?)?$")
# 종목 칩 키 — 5개 family + 그 밖의 종목을 묶은 'other'(A-14)
SPORT_GROUPS = (*FAMILIES, "other")
SORT_COLUMNS = {"date": "start_time", "distance": "distance_m", "pace": "avg_pace_sec_km", "load": "load"}
_LOAD_SQL = ("(SELECT numeric_value FROM metric_store WHERE scope_type='activity' AND scope_id=CAST(v_canonical_activities.id AS TEXT)"
             " AND metric_name='hrss' AND provider LIKE 'runpulse%' LIMIT 1)")


def _valid_date_time(v: str) -> bool:
    m = _DATE_TIME_RE.match(v)
    if not m:
        return False
    try:
        date.fromisoformat(m.group(1))
    except ValueError:
        return False
    return True


def parse_args(args: Any) -> dict:
    """request.args 유사 매핑 → 필터 dict. 잘못된 값은 조용히 무시하지 않고 ValueError(필드 이름)(A-19, SIV)."""
    f: dict = {}
    for src, dst in (("sport", "activity_type"), ("from", "date_from"), ("to", "date_to"),
                     ("search", "search"), ("q", "q"), ("sport_group", "sport_group"), ("type", "type"),
                     ("month", "month"), ("sort", "sort")):
        if args.get(src):
            f[dst] = args[src]
    if f.get("type") and f["type"] not in TYPE_CLASSES:
        raise ValueError("type")
    if f.get("month") and not _MONTH_RE.match(f["month"]):
        raise ValueError("month")
    if f.get("sport_group") and f["sport_group"] not in SPORT_GROUPS:
        raise ValueError("sport_group")
    if f.get("sort") and f["sort"] != "date" and f["sort"] not in SORT_COLUMNS:
        raise ValueError("sort")
    for key, src in (("date_from", "from"), ("date_to", "to")):
        if f.get(key) and not _valid_date_time(f[key]):
            raise ValueError(src)
    if args.get("dist_min"):
        try:
            km = float(args["dist_min"])
        except (TypeError, ValueError):
            raise ValueError("dist_min") from None
        if not math.isfinite(km) or km < 0:
            raise ValueError("dist_min")
        f["min_distance_m"] = km * 1000
    return f


def like_pattern(text: str) -> str:
    """LIKE 부분 일치 패턴 — `%`·`_`·`\\` 는 글자 그대로 찾도록 이스케이프(A-18, ESCAPE '\\' 와 함께 쓴다)."""
    esc = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{esc}%"


def sport_types(conn: sqlite3.Connection, group: str) -> list[str]:
    """정규화 그룹(running 등)에 속하는 raw activity_type 목록. 'other' 는 5개 family 밖의 모든 종목(A-14)."""
    rows = conn.execute("SELECT DISTINCT activity_type, source FROM v_canonical_activities").fetchall()
    if group == "other":
        return sorted({r[0] for r in rows if r[0] is not None and sport_family(r[0], r[1]) == "other"})
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
        clause = f"activity_type IN ({','.join('?' * len(raws))})"
        cl.append(f"({clause} OR activity_type IS NULL)" if f["sport_group"] == "other" else clause); p.extend(raws)
    if f.get("date_from"):
        cl.append("start_time >= ?"); p.append(f["date_from"])
    if f.get("date_to"):
        cl.append("start_time <= ?"); p.append(f["date_to"])
    if f.get("month"):
        cl.append("substr(start_time,1,7) = ?"); p.append(f["month"])
    if f.get("min_distance_m") is not None:
        cl.append("distance_m >= ?"); p.append(f["min_distance_m"])
    if f.get("search"):
        cl.append("name LIKE ? ESCAPE '\\'"); p.append(like_pattern(f["search"]))
    if f.get("q"):
        cl.append("(name LIKE ? ESCAPE '\\' OR start_time LIKE ? ESCAPE '\\' OR description LIKE ? ESCAPE '\\')")
        p.extend([like_pattern(f["q"])] * 3)
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

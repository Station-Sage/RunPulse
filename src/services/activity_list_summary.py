"""활동 목록 facets·주간 요약 (UX 리뷰 20 §7-2 ⑤, B-3).

읽기 전용. 목록과 같은 필터(activity_list_filters.build_where)를 공유한다.
"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from src.metrics.workout_classifier import TAG_LABELS
from src.services.activity_list_filters import SPORT_LABELS, TYPE_CLASSES, build_where
from src.utils.activity_types import normalize_activity_type

_CLASS_TO_KEY = {v: k for k, vals in TYPE_CLASSES.items() for v in vals}
_CLASS_SQL = ("(SELECT text_value FROM metric_store WHERE scope_type='activity' AND scope_id=CAST(v_canonical_activities.id AS TEXT)"
              " AND metric_name='workout_type_classified' LIMIT 1)")
MIN_HISTORY_DAYS = 28
AVG_WEEKS = 12


def get_facets(conn: sqlite3.Connection, filters: dict) -> dict:
    """sports(전체), types(sport_group 적용), months(sport_group·type 적용) 건수."""
    sports: dict[str, int] = {}
    for raw, src, n in conn.execute(
            "SELECT activity_type, source, COUNT(*) FROM v_canonical_activities GROUP BY 1, 2"):
        key = normalize_activity_type(raw, src)
        sports[key] = sports.get(key, 0) + n
    sport_rows = [{"key": k, "label": SPORT_LABELS.get(k, k), "n": n}
                  for k, n in sorted(sports.items(), key=lambda kv: -kv[1])]

    where, params = build_where(conn, filters, skip=("type", "month"))
    types: dict[str, int] = {}
    for cls, n in conn.execute(f"SELECT {_CLASS_SQL}, COUNT(*) FROM v_canonical_activities{where} GROUP BY 1", params):
        key = _CLASS_TO_KEY.get(cls)
        if key:
            types[key] = types.get(key, 0) + n
    type_rows = [{"key": k, "label": TAG_LABELS.get(k, k), "n": types[k]} for k in TYPE_CLASSES if k in types]

    where, params = build_where(conn, filters, skip=("month",))
    months = conn.execute(
        f"SELECT substr(start_time,1,7) m, COUNT(*) FROM v_canonical_activities{where} GROUP BY m ORDER BY m DESC",
        params).fetchall()
    return {"sports": sport_rows, "types": type_rows, "months": [{"month": m, "n": n} for m, n in months]}


def _monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _month_bounds(month: str) -> tuple[date, date]:
    y, m = int(month[:4]), int(month[5:])
    nxt = date(y + (m == 12), m % 12 + 1, 1)
    return date(y, m, 1), nxt - timedelta(days=1)


def _prev_month(month: str) -> str:
    first, _ = _month_bounds(month)
    prev = first - timedelta(days=1)
    return f"{prev.year:04d}-{prev.month:02d}"


def _rows(conn: sqlite3.Connection, filters: dict) -> list[tuple]:
    where, params = build_where(conn, filters)
    return conn.execute(
        f"SELECT substr(start_time,1,10), COALESCE(distance_m,0), COALESCE(duration_sec,0), {_CLASS_SQL}"
        f" FROM v_canonical_activities{where}", params).fetchall()


def _avg_week_km(conn: sqlite3.Connection, today: date) -> float | None:
    where, params = build_where(conn, {"sport_group": "running"})
    first = conn.execute(f"SELECT MIN(substr(start_time,1,10)) FROM v_canonical_activities{where}", params).fetchone()[0]
    if not first or (today - date.fromisoformat(first)).days < MIN_HISTORY_DAYS:
        return None
    start = max(today - timedelta(days=AVG_WEEKS * 7 - 1), date.fromisoformat(first))
    rows = conn.execute(
        f"SELECT COALESCE(SUM(distance_m),0) FROM v_canonical_activities{where}"
        f"{' AND' if where else ' WHERE'} substr(start_time,1,10) >= ? AND substr(start_time,1,10) <= ?",
        params + [start.isoformat(), today.isoformat()]).fetchone()[0]
    weeks = max(1, min(AVG_WEEKS, -(-((today - start).days + 1) // 7)))
    return round(rows / 1000 / weeks, 1)


def get_summary(conn: sqlite3.Connection, filters: dict, today: date | None = None) -> dict:
    """주별(월~일) 합계·최근 12주 평균·월 요약. month 모드의 경계 주는 그 달 활동만 합산(in_range_only)."""
    today = today or date.today()
    rows = _rows(conn, filters)
    lo = hi = None
    if filters.get("month"):
        lo, hi = _month_bounds(filters["month"])
    else:
        if filters.get("date_from"):
            lo = date.fromisoformat(filters["date_from"][:10])
        if filters.get("date_to"):
            hi = date.fromisoformat(filters["date_to"][:10])
    weeks: dict[date, dict] = {}
    for d, dist, sec, _ in rows:
        w = weeks.setdefault(_monday(date.fromisoformat(d)), {"n": 0, "m": 0.0, "sec": 0})
        w["n"] += 1; w["m"] += dist; w["sec"] += sec
    out_weeks = []
    if weeks:
        cur = min(weeks) if lo is None else _monday(lo)
        last = max(weeks) if hi is None else _monday(hi)
        while cur <= last:
            w = weeks.get(cur, {"n": 0, "m": 0.0, "sec": 0})
            partial = (lo is not None and cur < lo) or (hi is not None and cur + timedelta(days=6) > hi)
            out_weeks.append({"start": cur.isoformat(), "n": w["n"], "km": round(w["m"] / 1000, 1),
                              "sec": int(w["sec"]), "in_range_only": bool(partial)})
            cur += timedelta(days=7)
    result: dict = {"weeks": out_weeks, "avg_week_km_12w": _avg_week_km(conn, today)}
    if filters.get("month"):
        km = sum(r[1] for r in rows) / 1000
        by_class: dict[str, int] = {}
        for r in rows:
            key = _CLASS_TO_KEY.get(r[3])
            if key:
                by_class[key] = by_class.get(key, 0) + 1
        prev = _rows(conn, {**filters, "month": _prev_month(filters["month"])})
        prev_km = sum(r[1] for r in prev) / 1000
        result["month"] = {
            "month": filters["month"], "n": len(rows), "km": round(km, 1),
            "by_class": [{"key": k, "label": TAG_LABELS.get(k, k), "n": by_class[k]} for k in TYPE_CLASSES if k in by_class],
            "prev_month_pct": round((km - prev_km) / prev_km * 100) if prev and prev_km > 0 else None,
        }
    return result

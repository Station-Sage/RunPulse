"""러닝 아카이브 — 누적 통계·월별 거리·365일 히트맵·개인 최고 기록(읽기 전용)."""
from __future__ import annotations

import sqlite3
from datetime import date as _date, timedelta

_RUN = "activity_type LIKE '%running%'"
_PB_EFFORTS = [("1K", "1K"), ("1 mile", "1마일"), ("5K", "5K"), ("10K", "10K"), ("15K", "15K"), ("10 mile", "10마일")]
HEATMAP_DAYS = 371  # 53주


def _months_back(today: _date, n: int) -> list[str]:
    """오늘이 속한 달부터 과거 n개월의 'YYYY-MM' (오래된 순)."""
    y, m = today.year, today.month
    out = []
    for _ in range(n):
        out.append(f"{y:04d}-{m:02d}")
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return out[::-1]


def get_archive(conn: sqlite3.Connection, today: str | None = None) -> dict:
    """러닝 활동 전체 요약.

    반환: {"as_of", "totals": {...}|None, "longest": {...}|None, "monthly": [{month, km, runs}],
           "heatmap": [{date, km}], "personal_bests": [{key, label, time_sec, date, activity_id}]}
    러닝 활동이 없으면 totals가 None(빈 리스트들).
    """
    conn.row_factory = sqlite3.Row
    now = _date.fromisoformat(today) if today else _date.today()

    t = conn.execute(
        f"SELECT COUNT(*) AS n, COALESCE(SUM(distance_m), 0) AS dist, COALESCE(SUM(duration_sec), 0) AS dur,"
        f" MIN(substr(start_time, 1, 10)) AS since FROM v_canonical_activities WHERE {_RUN}"
    ).fetchone()
    if not t["n"]:
        return {"as_of": now.isoformat(), "totals": None, "longest": None, "monthly": [], "heatmap": [], "personal_bests": []}

    hm_start = (now - timedelta(days=HEATMAP_DAYS - 1)).isoformat()
    heat_rows = conn.execute(
        f"SELECT substr(start_time, 1, 10) AS d, SUM(distance_m) AS dist FROM v_canonical_activities"
        f" WHERE {_RUN} AND substr(start_time, 1, 10) >= ? AND substr(start_time, 1, 10) <= ?"
        f" GROUP BY d ORDER BY d",
        (hm_start, now.isoformat()),
    ).fetchall()
    heatmap = [{"date": r["d"], "km": round((r["dist"] or 0) / 1000, 1)} for r in heat_rows]

    months = _months_back(now, 12)
    mrows = conn.execute(
        f"SELECT substr(start_time, 1, 7) AS m, SUM(distance_m) AS dist, COUNT(*) AS n"
        f" FROM v_canonical_activities WHERE {_RUN} AND substr(start_time, 1, 7) >= ? GROUP BY m",
        (months[0],),
    ).fetchall()
    by_m = {r["m"]: r for r in mrows}
    monthly = [
        {"month": m, "km": round(((by_m[m]["dist"] or 0) / 1000), 1) if m in by_m else 0.0,
         "runs": by_m[m]["n"] if m in by_m else 0}
        for m in months
    ]

    lg = conn.execute(
        f"SELECT id, name, substr(start_time, 1, 10) AS d, distance_m FROM v_canonical_activities"
        f" WHERE {_RUN} AND distance_m IS NOT NULL ORDER BY distance_m DESC LIMIT 1"
    ).fetchone()
    longest = (
        {"id": lg["id"], "name": lg["name"], "date": lg["d"], "distance_km": round(lg["distance_m"] / 1000, 1)}
        if lg else None
    )

    pbs = []
    for key, label in _PB_EFFORTS:
        row = conn.execute(
            "SELECT b.activity_id AS aid, b.elapsed_sec AS sec, substr(a.start_time, 1, 10) AS d"
            " FROM activity_best_efforts b JOIN activity_summaries a ON a.id = b.activity_id"
            " WHERE b.effort_name = ? AND b.elapsed_sec IS NOT NULL AND a.activity_type LIKE '%running%'"
            " ORDER BY b.elapsed_sec ASC LIMIT 1",
            (key,),
        ).fetchone()
        if row:
            pbs.append({"key": key, "label": label, "time_sec": int(row["sec"]), "date": row["d"], "activity_id": row["aid"]})

    return {
        "as_of": now.isoformat(),
        "totals": {
            "runs": t["n"],
            "distance_km": round(t["dist"] / 1000, 1),
            "hours": round(t["dur"] / 3600, 1),
            "since": t["since"],
            "active_days_365": len(heatmap),
        },
        "longest": longest,
        "monthly": monthly,
        "heatmap": heatmap,
        "personal_bests": pbs,
    }

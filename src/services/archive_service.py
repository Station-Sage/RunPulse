"""러닝 아카이브 — 누적 통계·월별 거리·365일 히트맵·개인 최고 기록(읽기 전용)."""
from __future__ import annotations

import sqlite3
from datetime import date as _date, timedelta

_RUN = "activity_type LIKE '%running%'"
_PB_EFFORTS = [("1K", "1K"), ("1 mile", "1마일"), ("5K", "5K"), ("10K", "10K")]
# 대회 기록(전력 allout)으로도 뽑는 표준 거리 — 대회 거리가 이 값의 ±1.5% 안이면 그 거리 기록으로 본다(시간은 거리 비로 환산)
_PB_RACES = [("5K", "5K", 5000.0), ("10K", "10K", 10000.0), ("half", "하프", 21097.5), ("full", "풀", 42195.0)]
_RACE_TOL = 0.015
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

    # 개인 최고 기록 — 활동 안 구간 기록(Strava best efforts)과 전력 대회 기록을 함께 본다. Strava 는 더 이상 동기화하지
    # 않아 구간 기록이 옛 시점에서 멈춰 있으므로 대회 기록(Garmin·Intervals 활동)이 최근 PB 를 채운다. 항목마다 출처를 표시.
    cand: dict[str, dict] = {}
    for key, label in _PB_EFFORTS:
        row = conn.execute(
            "SELECT b.activity_id AS aid, b.elapsed_sec AS sec, substr(a.start_time, 1, 10) AS d"
            " FROM activity_best_efforts b JOIN activity_summaries a ON a.id = b.activity_id"
            " WHERE b.effort_name = ? AND b.elapsed_sec IS NOT NULL AND a.activity_type LIKE '%running%'"
            " ORDER BY b.elapsed_sec ASC LIMIT 1",
            (key,),
        ).fetchone()
        if row:
            cand[key] = {"key": key, "label": label, "time_sec": int(row["sec"]), "date": row["d"],
                         "activity_id": row["aid"], "source": "구간 기록"}
    try:
        races = conn.execute(
            "SELECT r.activity_id AS aid, r.distance_m AS dist, COALESCE(r.official_time_sec, a.moving_time_sec) AS sec,"
            " substr(a.start_time, 1, 10) AS d FROM race_results r JOIN activity_summaries a ON a.id = r.activity_id"
            " WHERE r.effort = 'allout' AND COALESCE(r.official_time_sec, a.moving_time_sec) > 0"
        ).fetchall()
    except sqlite3.OperationalError:
        races = []
    for key, label, target in _PB_RACES:
        for r in races:
            if abs(r["dist"] - target) / target > _RACE_TOL:
                continue
            sec = int(round(r["sec"] * target / r["dist"]))
            if key not in cand or sec < cand[key]["time_sec"]:
                cand[key] = {"key": key, "label": label, "time_sec": sec, "date": r["d"], "activity_id": r["aid"],
                             "source": "대회"}
    order = [k for k, _ in _PB_EFFORTS] + [k for k, _, _ in _PB_RACES if k not in dict(_PB_EFFORTS)]
    pbs = [cand[k] for k in order if k in cand]

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

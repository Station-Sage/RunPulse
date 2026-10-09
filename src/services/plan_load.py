"""계획 조정의 부하 영향 추정 — 이번 주 부하 변화율과 주말 ACWR 전/후 (ADR-035, DESIGN-PLAN-ROW-ACTION-COACHING §5).

세션 부하 = 유형 계수 K × 거리(km) × u(이지 러닝 TRIMP/km 중앙값). 지난 날은 실제 TRIMP, 오늘 이후는 계획(overlay 적용)으로 채운다.
데이터가 부족하면 None (에러 raise 금지).
"""
from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta
from statistics import median

from src.metrics.pmc import ewma_loads
from src.training import plan_overlay

K = {"recovery": 0.95, "easy": 1.0, "long": 1.15, "tempo": 1.11, "threshold": 1.11, "marathon": 1.11,
     "long_mp": 1.11, "interval": 1.23, "race": 1.25}
DEFAULT_U = 8.8
EASY_MIN_PACE = 330
MIN_EASY_SAMPLES = 10
ATL_ALPHA, CTL_ALPHA = 1 / 7, 1 / 42
LOOKBACK = 180


def session_load(wtype: str | None, km: float | None, u: float) -> float:
    if not km or wtype in (None, "rest"):
        return 0.0
    return K.get(wtype, 1.0) * float(km) * u


def _activity_rows(conn: sqlite3.Connection, start: str, end: str) -> list[tuple]:
    return conn.execute(
        """SELECT substr(a.start_time,1,10), m.numeric_value, a.distance_m / 1000.0, a.avg_pace_sec_km
           FROM metric_store m JOIN v_canonical_activities a ON CAST(m.scope_id AS INTEGER) = a.id
           WHERE m.metric_name='trimp' AND m.scope_type='activity' AND m.is_primary=1
             AND a.activity_type='running' AND substr(a.start_time,1,10) >= ? AND substr(a.start_time,1,10) < ?""",
        (start, end)).fetchall()


def daily_actual(conn: sqlite3.Connection, start: str, end: str) -> dict[str, float]:
    """[start, end) 일별 실제 TRIMP 합."""
    out: dict[str, float] = {}
    for d, v, *_ in _activity_rows(conn, start, end):
        if v:
            out[d] = out.get(d, 0.0) + float(v)
    return out


def easy_u(conn: sqlite3.Connection, today: str) -> float:
    """최근 90일 이지 러닝(평균 페이스 ≥330s/km, 1km 초과)의 TRIMP/km 중앙값. 표본<10 이면 전체 러닝 중앙값, 없으면 기본값."""
    start = (date.fromisoformat(today) - timedelta(days=90)).isoformat()
    rows = [r for r in _activity_rows(conn, start, today) if r[1] and r[2] and r[2] > 1]
    easy = [r[1] / r[2] for r in rows if r[3] and r[3] >= EASY_MIN_PACE]
    pool = easy if len(easy) >= MIN_EASY_SAMPLES else [r[1] / r[2] for r in rows]
    return median(pool) if pool else DEFAULT_U


def _week_bounds(day: str) -> tuple[str, str]:
    d = date.fromisoformat(day)
    ws = d - timedelta(days=d.weekday())
    return ws.isoformat(), (ws + timedelta(days=7)).isoformat()


def _week_rows(conn: sqlite3.Connection, ws: str, we: str) -> list[dict]:
    cols = ("id", "date", "workout_type", "distance_km", "target_pace_min", "target_pace_max", "description",
            "interval_prescription", "structure_json")
    rows = [dict(zip(cols, r)) for r in conn.execute(
        f"SELECT {', '.join(cols)} FROM planned_workouts WHERE date >= ? AND date < ? ORDER BY date", (ws, we))]
    return plan_overlay.apply(rows, plan_overlay.live_adjustments(conn, ws, we))


def _acwr(daily: dict[str, float], at: str) -> float | None:
    atl, ctl, _ = ewma_loads(daily, datetime.strptime(at, "%Y-%m-%d"), LOOKBACK, ATL_ALPHA, CTL_ALPHA)
    return round(atl / ctl, 2) if ctl > 0 else None


def load_delta(conn: sqlite3.Connection, workout_id: int, after: dict | None, *, today: str) -> dict | None:
    """workout 이 after 로 바뀔 때의 {week_pct, acwr_before, acwr_after, week_load_before, week_load_after}.

    after=None(move 등 부하 불변)이거나 대상 세션이 이번 주가 아니면 None. 부하 기준 데이터가 없으면 None.
    """
    if after is None:
        return None
    ws, we = _week_bounds(today)
    rows = _week_rows(conn, ws, we)
    target = next((r for r in rows if r["id"] == workout_id), None)
    if target is None:
        return None
    u = easy_u(conn, today)
    daily = daily_actual(conn, (date.fromisoformat(ws) - timedelta(days=LOOKBACK)).isoformat(), today)
    if not daily:
        return None

    def week(override: dict | None) -> tuple[float, float | None]:
        d, total = dict(daily), sum(v for k, v in daily.items() if ws <= k < today)
        for r in rows:
            if r["date"] < today:
                continue
            w = {**r, **override} if override is not None and r["id"] == workout_id else r
            ld = session_load(w["workout_type"], w["distance_km"], u)
            d[r["date"]] = d.get(r["date"], 0.0) + ld
            total += ld
        return total, _acwr(d, (date.fromisoformat(we) - timedelta(days=1)).isoformat())

    b_total, b_acwr = week(None)
    a_total, a_acwr = week(after)
    if b_total <= 0:
        return None
    return {"week_pct": round((a_total - b_total) / b_total * 100, 1), "acwr_before": b_acwr, "acwr_after": a_acwr,
            "week_load_before": round(b_total), "week_load_after": round(a_total)}

"""CalcContext 러닝 이력 API(RunHistoryMixin) — canonical 러닝 + 트윈 HR 병합 + 랩(경사보정 속도) + 대회 판정.

Calculator 내부 raw SQL 금지(ADR-009) 원칙에 따라 예측 v2 계열 calculator 는 이 API만 쓴다.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta

RUN_TYPES = ("running", "trail_running", "treadmill", "indoor_running", "virtual_running")
RACE_NAME = re.compile(r"대회|마라톤|marathon|half|하프|10k|10km|race|레이스", re.I)
NOT_RACE_NAME = re.compile(r"TT|템포|tempo", re.I)
NOMINAL = ((5000.0, 0.04), (10000.0, 0.04), (21097.5, 0.03), (42195.0, 0.02))

_RUNS_SQL = f"""
SELECT v.id, v.name, v.activity_type, v.start_time, v.distance_m, v.moving_time_sec, v.elapsed_time_sec,
       v.duration_sec, v.elevation_gain, v.start_lat, v.start_lon, v.avg_temperature,
       COALESCE(v.avg_hr, (SELECT o.avg_hr FROM activity_summaries o WHERE o.matched_group_id = v.matched_group_id
                           AND o.avg_hr IS NOT NULL ORDER BY CASE o.source WHEN 'garmin' THEN 1 WHEN 'strava' THEN 2 ELSE 3 END LIMIT 1)) AS avg_hr,
       (SELECT max(o.max_hr) FROM activity_summaries o
         WHERE (o.id = v.id OR (v.matched_group_id IS NOT NULL AND o.matched_group_id = v.matched_group_id))
           AND NOT (o.source = 'intervals' AND o.max_hr >= 182)) AS max_hr,
       (SELECT group_concat(COALESCE(o.name, ''), ' | ') FROM activity_summaries o
         WHERE v.matched_group_id IS NOT NULL AND o.matched_group_id = v.matched_group_id) AS group_names,
       (SELECT count(*) FROM activity_summaries o
         WHERE (o.id = v.id OR (v.matched_group_id IS NOT NULL AND o.matched_group_id = v.matched_group_id))
           AND o.event_type = 'race') AS race_rows
FROM v_canonical_activities v
WHERE v.activity_type IN ({",".join("?" * len(RUN_TYPES))}) AND v.start_time >= ? AND v.start_time <= ?
ORDER BY v.start_time
"""

_LAPS_SQL = """
SELECT activity_id, lap_index, distance_m, duration_sec, elapsed_duration_sec, avg_hr, max_hr, avg_pace_sec_km,
       gap_speed_ms, elevation_gain, elevation_loss, avg_temperature_c, lap_trigger, compliance_score, wkt_step_index
FROM activity_laps WHERE activity_id IN ({ids}) ORDER BY activity_id, lap_index
"""


def nominal_distance(dist_m: float | None) -> float | None:
    if not dist_m:
        return None
    for n, tol in NOMINAL:
        if abs(dist_m - n) / n <= tol:
            return n
    return None


def lap_block(row) -> dict | None:
    """activity_laps 행 → segments 블록. speed_ms 는 GAP 우선."""
    d = row["distance_m"] or 0.0
    t = row["duration_sec"] or row["elapsed_duration_sec"] or 0.0
    if d <= 0 or t <= 0:
        return None
    raw = d / t
    return {"dist_m": d, "dur_s": t, "speed_ms": row["gap_speed_ms"] or raw, "raw_speed_ms": raw,
            "hr": row["avg_hr"], "max_hr": row["max_hr"], "itype": row["lap_trigger"],
            "temp_c": row["avg_temperature_c"], "compliance": row["compliance_score"], "wkt_step": row["wkt_step_index"],
            "elev_gain": row["elevation_gain"], "elev_loss": row["elevation_loss"]}


class RunHistoryMixin:
    """CalcContext 에 섞어 쓰는 러닝 이력 조회."""

    def _end_date(self, end_date: str | None) -> datetime:
        if end_date:
            return datetime.strptime(end_date[:10], "%Y-%m-%d")
        if getattr(self, "scope_type", None) == "daily":
            return datetime.strptime(self.scope_id, "%Y-%m-%d")
        return datetime.now()

    def get_runs(self, days: int, end_date: str | None = None, with_laps: bool = False,
                 include_end: bool = True) -> list[dict]:
        """[end_date-days, end_date] canonical 러닝. include_end=False 면 end_date 당일 제외(예측 누수 방지)."""
        end = self._end_date(end_date)
        start = (end - timedelta(days=days)).strftime("%Y-%m-%d")
        stop = end.strftime("%Y-%m-%d") + (" 23:59:59" if include_end else " 00:00:00")
        cur = self.conn.cursor()
        cur.row_factory = _row_factory          # 연결의 row_factory 는 건드리지 않는다
        rows = cur.execute(_RUNS_SQL, [*RUN_TYPES, start, stop]).fetchall()
        runs = []
        for r in rows:
            mv = r["moving_time_sec"] or r["duration_sec"] or 0
            el = r["elapsed_time_sec"] or r["duration_sec"] or mv
            names = f"{r['name'] or ''} | {r['group_names'] or ''}"
            is_race = bool(r["race_rows"]) or (bool(RACE_NAME.search(names)) and not NOT_RACE_NAME.search(names))
            runs.append({
                "id": r["id"], "date": r["start_time"][:10], "start_time": r["start_time"], "name": r["name"],
                "activity_type": r["activity_type"], "distance_m": r["distance_m"] or 0.0,
                "moving_s": mv, "elapsed_s": el,
                "perf_time_s": el if (el and mv and el <= mv * 1.05) or is_race else mv,
                "avg_hr": r["avg_hr"], "max_hr": r["max_hr"], "elevation_gain": r["elevation_gain"] or 0.0,
                "lat": r["start_lat"], "lon": r["start_lon"], "device_temp_c": r["avg_temperature"],
                "is_race": is_race, "nominal_m": nominal_distance(r["distance_m"]) if is_race else None,
            })
        if with_laps and runs:
            by_id = {x["id"]: x for x in runs}
            for x in runs:
                x["laps"] = []
            ids = ",".join(str(i) for i in by_id)
            for lr in cur.execute(_LAPS_SQL.format(ids=ids)).fetchall():
                b = lap_block(lr)
                if b:
                    by_id[lr["activity_id"]]["laps"].append(b)
        return runs

    def get_activity_metric_json(self, activity_id: int, metric_name: str) -> str | None:
        row = self.conn.execute(
            "SELECT json_value FROM metric_store WHERE scope_type='activity' AND scope_id=? AND metric_name=? AND is_primary=1",
            [str(activity_id), metric_name]).fetchone()
        return row[0] if row else None

    def get_active_goal(self, as_of: str | None = None) -> dict | None:
        d = (as_of or self._end_date(None).strftime("%Y-%m-%d"))[:10]
        row = self.conn.execute(
            "SELECT id, name, race_date, distance_km, target_time_sec FROM goals WHERE status='active' "
            "AND race_date IS NOT NULL AND race_date >= ? ORDER BY race_date, id DESC LIMIT 1", [d]).fetchone()
        if not row:
            return None
        return {"id": row[0], "name": row[1], "race_date": row[2], "distance_km": row[3], "target_time_sec": row[4]}

    def get_latest_daily_metric(self, metric_name: str, as_of: str, provider: str | None = None,
                                include_json: bool = False):
        """as_of(포함) 이전 가장 최근 일별 값. include_json 이면 (numeric, json) 튜플."""
        sql = ("SELECT numeric_value, json_value FROM metric_store WHERE scope_type='daily' AND metric_name=? "
               "AND scope_id <= ? " + ("AND provider=? " if provider else "AND is_primary=1 ") +
               "ORDER BY scope_id DESC LIMIT 1")
        params = [metric_name, as_of[:10]] + ([provider] if provider else [])
        row = self.conn.execute(sql, params).fetchone()
        if not row:
            return (None, None) if include_json else None
        return (row[0], row[1]) if include_json else row[0]

    def get_best_efforts(self, days: int, effort_name: str, end_date: str | None = None) -> list[dict]:
        """[end_date-days, end_date) 구간 best effort(Strava 등) → [{"activity_id","date","elapsed_s","distance_m"}] 빠른 순."""
        end = self._end_date(end_date)
        start = (end - timedelta(days=days)).strftime("%Y-%m-%d")
        rows = self.conn.execute(
            "SELECT b.activity_id, substr(a.start_time, 1, 10), b.elapsed_sec, b.distance_m FROM activity_best_efforts b "
            "JOIN activity_summaries a ON a.id = b.activity_id WHERE b.effort_name = ? AND a.start_time >= ? "
            "AND a.start_time < ? AND b.elapsed_sec > 0 ORDER BY b.elapsed_sec",
            [effort_name, start, end.strftime("%Y-%m-%d")]).fetchall()
        return [{"activity_id": r[0], "date": r[1], "elapsed_s": r[2], "distance_m": r[3]} for r in rows]

    def get_race_results(self) -> dict[int, dict]:
        """사용자 대회 확인(race_results) activity_id → {effort, official_time_sec, distance_m}."""
        rows = self.conn.execute("SELECT activity_id, effort, official_time_sec, distance_m FROM race_results").fetchall()
        return {r[0]: {"effort": r[1], "official_time_sec": r[2], "distance_m": r[3]} for r in rows}


def _row_factory(cursor, row):
    return {d[0]: v for d, v in zip(cursor.description, row)}

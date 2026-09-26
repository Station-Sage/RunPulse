"""활동별 외기 기상 인제스트(P7-PRED-32) — 1순위 Open-Meteo(시작 좌표·중간 시각), 2순위 손목 기기 온도 보정값.

저장: weather_cache(좌표·날짜별 24시간, source='open_meteo') + metric_store activity 스코프
  provider 'open_meteo'       : weather_temp_c, weather_humidity_pct, weather_dew_point_c, weather_feels_like_c,
                                weather_wind_speed_ms, weather_wbgt_c, weather_source(text)
  provider 'device_corrected' : weather_temp_c (= (기기온도 − 11)/0.65), weather_source(text)
충돌: 두 값 모두 있고 |차| > 6℃ 면 open_meteo 행 json 에 {"conflict": true, "device_corrected": x} 기록(실내·좌표 오류 의심).
우선순위: open_meteo(90) > device_corrected(999, 기본) — metric_priority 참조.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from typing import Any, Callable

from src.metrics.prediction.physio import ambient_from_device, round_coord
from src.utils.db_helpers import upsert_metric
from src.weather import provider as om

CONFLICT_C = 6.0
METRICS = {"temp_c": "weather_temp_c", "humidity_pct": "weather_humidity_pct", "dew_point_c": "weather_dew_point_c",
           "feels_like_c": "weather_feels_like_c", "wind_speed_ms": "weather_wind_speed_ms", "wbgt_c": "weather_wbgt_c"}
_TARGETS = """
SELECT id, start_time, start_lat, start_lon, COALESCE(elapsed_time_sec, duration_sec, 0), avg_temperature
FROM v_canonical_activities
WHERE start_time >= ? AND activity_type IN ('running', 'trail_running') AND NOT EXISTS (SELECT 1 FROM metric_store m WHERE m.scope_type='activity'
      AND m.scope_id = CAST(v_canonical_activities.id AS TEXT) AND m.metric_name='weather_temp_c' AND m.provider='open_meteo')
ORDER BY start_time DESC
"""


def _cached(conn, day, lat, lon) -> list[dict]:
    cur = conn.execute("SELECT hour, temp_c, humidity_pct, dew_point_c, feels_like_c, wind_speed_ms, shortwave_wm2 "
                       "FROM weather_cache WHERE date=? AND latitude=? AND longitude=? AND source='open_meteo' "
                       "ORDER BY hour", (day, lat, lon))
    keys = ["hour", "temp_c", "humidity_pct", "dew_point_c", "feels_like_c", "wind_speed_ms", "shortwave_wm2"]
    return [dict(zip(keys, r)) for r in cur.fetchall()]


def _store_cache(conn, day, lat, lon, rows: list[dict]) -> None:
    for r in rows:
        conn.execute(
            "INSERT INTO weather_cache (date, hour, latitude, longitude, source, temp_c, humidity_pct, dew_point_c, "
            "feels_like_c, wind_speed_ms, shortwave_wm2) VALUES (?,?,?,?, 'open_meteo', ?,?,?,?,?,?) "
            "ON CONFLICT(date, hour, latitude, longitude, source) DO UPDATE SET temp_c=excluded.temp_c, "
            "humidity_pct=excluded.humidity_pct, dew_point_c=excluded.dew_point_c, feels_like_c=excluded.feels_like_c, "
            "wind_speed_ms=excluded.wind_speed_ms, shortwave_wm2=excluded.shortwave_wm2, fetched_at=datetime('now')",
            (day, r["hour"], lat, lon, r["temp_c"], r["humidity_pct"] and int(round(r["humidity_pct"])),
             r["dew_point_c"], r["feels_like_c"], r["wind_speed_ms"], r["shortwave_wm2"]))


def ingest_activity_weather(conn: sqlite3.Connection, getter: Callable[..., Any], since: str = "2000-01-01",
                            max_requests: int = 500, today=None) -> dict:
    """반환 {"open_meteo", "device_corrected", "no_data", "requests", "failed_requests", "conflicts"}.
    요청 실패(오프라인 포함)는 기기 온도 보정값으로 대체하고 다음 실행에서 재시도된다(open_meteo 행이 없으므로)."""
    st = dict.fromkeys(("open_meteo", "device_corrected", "no_data", "requests", "failed_requests", "conflicts"), 0)
    for aid, start, lat, lon, dur, dev in conn.execute(_TARGETS, (since,)).fetchall():
        t0 = datetime.fromisoformat(start.replace("T", " ")[:19])       # start_time 은 현지 시각(가정 — 시각 분포로 확인)
        mid = t0 + timedelta(seconds=(dur or 0) / 2)
        dc = round(ambient_from_device(dev), 1) if dev is not None else None
        w = None
        if lat is not None and lon is not None:
            day, la, lo = mid.date().isoformat(), round_coord(lat), round_coord(lon)
            rows = _cached(conn, day, la, lo)
            if not rows and st["requests"] < max_requests:
                st["requests"] += 1
                h = om.fetch_hourly(la, lo, day, getter, today)
                rows = om.day_rows(h, day) if h else []
                if rows:
                    _store_cache(conn, day, la, lo, rows)
                else:
                    st["failed_requests"] += 1
            w = om.at_time(rows, mid.hour + mid.minute / 60) if rows else None
        if w and w.get("temp_c") is not None:
            extra = None
            if dc is not None and abs(dc - w["temp_c"]) > CONFLICT_C:
                extra, st["conflicts"] = {"conflict": True, "device_corrected": dc}, st["conflicts"] + 1
            for k, name in METRICS.items():
                if w.get(k) is not None:
                    upsert_metric(conn, "activity", str(aid), name, "open_meteo", numeric_value=round(w[k], 2),
                                  json_value=extra if name == "weather_temp_c" else None)
            upsert_metric(conn, "activity", str(aid), "weather_source", "open_meteo", text_value="open_meteo")
            st["open_meteo"] += 1
        if dc is not None:
            upsert_metric(conn, "activity", str(aid), "weather_temp_c", "device_corrected", numeric_value=dc)
            upsert_metric(conn, "activity", str(aid), "weather_source", "device_corrected", text_value="device_corrected")
            st["device_corrected"] += 0 if w else 1
        if not w and dc is None:
            st["no_data"] += 1
    conn.commit()
    return st


if __name__ == "__main__":        # python3 -m src.weather.activity_weather --db <path> --since 2025-01-01 [--max 2000]
    import argparse

    from src.utils.api import get as _get

    ap = argparse.ArgumentParser(description="활동별 외기 기상 백필(Open-Meteo, 실패 시 기기 온도 보정)")
    ap.add_argument("--db", required=True)
    ap.add_argument("--since", default="2025-01-01")
    ap.add_argument("--max", type=int, default=2000)
    a = ap.parse_args()
    with sqlite3.connect(a.db) as _c:
        print(ingest_activity_weather(_c, _get, since=a.since, max_requests=a.max))

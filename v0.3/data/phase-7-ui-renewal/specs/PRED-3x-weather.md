# PRED-3x — 날씨(외기) 인제스트와 기온 모델 (예측 리뉴얼 r4 — 날씨 모듈 통합 P7-PRED-86 포함)

근거: `REVIEW-07-prediction-renewal.md` r3 §2-9·4-7·4-8. 우선순위는 사용자 확정(1순위 Open-Meteo, 2순위 기기 온도).

> **실행 규칙(모든 PRED 유닛 공통)** — 이 명세의 코드·시그니처·상수·문구는 그대로 구현한다. "전문" 블록은 파일 내용 그대로 붙여 넣고, "diff" 블록은 그대로 적용한다(줄 위치가 조금 달라도 문맥이 같으면 같은 자리). 명세와 다르게 하고 싶으면 `v0.3/data/phase-7-ui-renewal/DECISIONS.md`에 사유를 적고 **중단**한다. 실DB(`data/users/*/running.db`)는 열지 않는다 — 테스트는 모두 `:memory:`다. 모든 코드는 `/tmp` 샌드박스(저장소 사본)에서 전체 테스트·`check_docs`·`check_data_consistency` 통과를 확인한 것이다. `pytest`가 없다는 오류가 나면 `/usr/bin/python3 -m pytest`로 같은 명령을 실행한다.

## P7-PRED-86 — 날씨 모듈 통합: `src/weather/provider.py`를 단일 Open-Meteo 클라이언트로 (r3 P7-PRED-31 대체)

- 의존: P7-PRED-22(physio) · UI 노출: 없음
- 파일: `src/weather/provider.py`(**전문 교체**), `tests/test_weather_provider.py`(신규). `src/weather/openmeteo.py`는 만들지 않는다.
- 왜(REVIEW-07 §R4-5, 사용자 결정 "삭제가 아니라 통합"): 기존 `provider.py`는 없는 `weather_data` 테이블에 쓰고 `_v02_backup/fearp.py`만 참조하는 죽은 코드다. 하지만 동작하는 Open-Meteo URL과 시간별 변수 목록을 갖고 있다. r3는 새 `openmeteo.py`를 만들어 모듈이 둘이 될 뻔했다. 한 파일로 수렴한다. 저장은 호출자(`activity_weather`, P7-PRED-32)가 `weather_cache`에 한다.
- 규칙(r3 P7-PRED-31과 같음):
  - archive(5일 이상 지난 날) / forecast(`past_days=7`)를 자동으로 고른다.
  - 변수: `temperature_2m, relative_humidity_2m, dew_point_2m, apparent_temperature, wind_speed_10m, shortwave_radiation`.
  - 좌표는 소수 2자리(≈1km)로만 보낸다. 요청 간 최소 0.2초.
  - HTTP는 주입받는다. 실패·오프라인이면 예외 없이 None을 돌려준다.
- `_v02_backup/fearp.py`의 `provider` import는 백업 코드라 실행 경로가 아니다. 손대지 않는다.

**`src/weather/provider.py`** — 신규(기존 파일이면 전문 교체), 전문 그대로(85줄)

````python
"""Open-Meteo 시간별 기상 클라이언트(단일 모듈) — 순수 파싱 + 주입 가능한 HTTP, 활동 중간 시각 보간, WBGT 근사(P7-PRED-86).

이전 provider.py(v0.2)는 없는 `weather_data` 테이블에 쓰고 백업 코드만 참조했다. URL·시간별 변수 목록을 이어받아
이 파일 하나로 수렴했다(별도 openmeteo.py 없음). 저장은 호출자(activity_weather)가 weather_cache 에 한다.

archive(5일 이상 지난 날) / forecast(past_days=7) 자동 선택. 좌표는 소수 2자리(약 1km)로 낮춰 보낸다(개인정보·캐시 적중).
"""
from __future__ import annotations

import time
from datetime import date, timedelta
from typing import Any, Callable

from src.metrics.prediction.physio import round_coord, wbgt_approx

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
HOURLY = ("temperature_2m,relative_humidity_2m,dew_point_2m,apparent_temperature,"
          "wind_speed_10m,shortwave_radiation")
ARCHIVE_LAG_DAYS = 5
MIN_INTERVAL_S = 0.2          # 요청 간 최소 간격(무료 10,000건/일 한도 대비 여유)
FIELDS = {"temperature_2m": "temp_c", "relative_humidity_2m": "humidity_pct", "dew_point_2m": "dew_point_c",
          "apparent_temperature": "feels_like_c", "wind_speed_10m": "wind_speed_ms",
          "shortwave_radiation": "shortwave_wm2"}
_last_call = [0.0]


def request_params(lat: float, lon: float, day: str, today: date) -> tuple[str, dict[str, Any]]:
    """(url, params). 좌표는 round_coord(2)."""
    use_archive = date.fromisoformat(day) <= today - timedelta(days=ARCHIVE_LAG_DAYS)
    p = {"latitude": round_coord(lat), "longitude": round_coord(lon), "hourly": HOURLY,
         "timezone": "auto", "wind_speed_unit": "ms"}
    if use_archive:
        p.update(start_date=day, end_date=day)
        return ARCHIVE_URL, p
    p.update(past_days=7, forecast_days=1)
    return FORECAST_URL, p


def fetch_hourly(lat: float, lon: float, day: str, getter: Callable[..., Any], today: date | None = None) -> dict | None:
    """getter(url, params=...) 는 src.utils.api.get (1회 재시도 내장). 실패·오프라인이면 None (예외 전파 금지)."""
    wait = MIN_INTERVAL_S - (time.monotonic() - _last_call[0])
    if wait > 0:
        time.sleep(wait)
    url, params = request_params(lat, lon, day, today or date.today())
    try:
        raw = getter(url, params=params)
    except Exception:
        return None
    finally:
        _last_call[0] = time.monotonic()
    h = (raw or {}).get("hourly") if isinstance(raw, dict) else None
    return h if h and h.get("time") else None


def day_rows(hourly: dict, day: str) -> list[dict]:
    """hourly → 해당 날짜 24개 행 [{"hour", "temp_c", ...}] (weather_cache 저장용)."""
    out = []
    for i, t in enumerate(hourly["time"]):
        if t[:10] != day:
            continue
        row = {"hour": int(t[11:13])}
        for k, name in FIELDS.items():
            vals = hourly.get(k) or []
            row[name] = vals[i] if i < len(vals) else None
        out.append(row)
    return out


def at_time(rows: list[dict], hour_frac: float) -> dict | None:
    """시간별 행 목록 → 소수 시각(예 7.75 = 07:45)에서 선형 보간. 한쪽이 None 이면 다른 쪽 값."""
    by = {r["hour"]: r for r in rows}
    h0 = int(hour_frac)
    a, b = by.get(h0), by.get(min(h0 + 1, 23))
    if a is None:
        return None
    b = b or a
    f = hour_frac - h0
    out = {}
    for name in FIELDS.values():
        x, y = a.get(name), b.get(name)
        out[name] = (x if y is None else y) if x is None or y is None else x + (y - x) * f
    t, rh = out.get("temp_c"), out.get("humidity_pct")
    out["wbgt_c"] = round(wbgt_approx(t, rh), 1) if t is not None and rh is not None else None
    return out
````

**`tests/test_weather_provider.py`** — 신규, 전문 그대로(25줄)

````python
"""P7-PRED-86: Open-Meteo 단일 클라이언트(provider.py) — 요청 파라미터·보간·WBGT."""
from datetime import date

from src.weather import provider as om


def _hourly(day="2026-07-01"):
    hrs = [f"{day}T{h:02d}:00" for h in range(24)]
    return {"hourly": {"time": hrs, "temperature_2m": [20.0 + h * 0.5 for h in range(24)],
                       "relative_humidity_2m": [70] * 24, "dew_point_2m": [15.0] * 24,
                       "apparent_temperature": [22.0] * 24, "wind_speed_10m": [2.0] * 24,
                       "shortwave_radiation": [100.0] * 24}}


def test_request_params_archive_vs_forecast():
    url, p = om.request_params(37.51234, 126.9876, "2026-07-01", date(2026, 9, 26))
    assert url == om.ARCHIVE_URL and (p["latitude"], p["longitude"]) == (37.51, 126.99) and p["start_date"] == "2026-07-01"
    url, p = om.request_params(37.5, 127.0, "2026-09-24", date(2026, 9, 26))
    assert url == om.FORECAST_URL and p["past_days"] == 7


def test_at_time_interpolates_and_wbgt():
    rows = om.day_rows(_hourly()["hourly"], "2026-07-01")
    w = om.at_time(rows, 7.5)                    # 07:30 → 23.5 + 0.25 = 23.75
    assert w["temp_c"] == 23.75 and w["wbgt_c"] == 25.5
````

검증:
```
python3 -m pytest tests/test_weather_provider.py -q
```

## P7-PRED-32 — 활동 외기 기상 인제스트(1순위 Open-Meteo, 2순위 손목 온도 보정) + 우선순위 + 동기화 훅

- 의존: P7-PRED-11, P7-PRED-86 · UI 노출: 활동 상세 날씨 칩(기존 `weather_*` 표시 경로가 있으면 자동 노출), P7-PRED-72 기온별 표 · **실DB: P7-PRED-61 3단계(백필, API 약 300회)**
- 파일: `src/weather/activity_weather.py`(신규), `src/utils/metric_priority.py`, `src/sync.py`, `tests/test_weather_ingest.py`(신규), `src/utils/metric_registry.py`
- 규칙:
  - 대상: `v_canonical_activities` 중 running·trail_running, open_meteo `weather_temp_c` 가 아직 없는 활동(재실행 시 실패분만 재시도).
  - 시각: 시작 시각(현지 시각 — **가정**, 실DB 시작 시각 분포가 06시·18~21시에 몰려 현지로 판단. Strava 행의 `Z` 접미사는 현지로 취급) + 경과시간/2 에서 시간별 값을 선형 보간.
  - 캐시: `weather_cache(date, hour, latitude, longitude, source='open_meteo')` 24행/일. 같은 좌표(2자리)·날짜는 재요청하지 않는다.
  - 저장: provider `open_meteo` — `weather_temp_c, weather_humidity_pct, weather_dew_point_c, weather_feels_like_c, weather_wind_speed_ms, weather_wbgt_c`, `weather_source`(text). 기기 온도(`avg_temperature`)가 있으면 provider `device_corrected` 로 `(기기−11)/0.65` 도 저장한다. 우선순위 `open_meteo`(90) > `device_corrected`(999).
  - 충돌: 두 값 차이 > 6℃ 면 open_meteo `weather_temp_c` json 에 `{"conflict": true, "device_corrected": x}`(실내·좌표 오류 의심).
  - 좌표 없음: 기기 온도 보정값만, 둘 다 없으면 저장 안 함(예측은 기온 보정 없이 15℃ 기준값을 쓴다).
  - 손목 편향 근거: 외기 대비 손목 +3.5℃(중앙), 5℃ 미만 +11℃, 27℃ 초과 +1℃ → 선형 `기기 ≈ 11.0 + 0.65·외기`(261개 활동 적합).
- Open-Meteo 호출은 P7-PRED-86의 `src.weather.provider`(단일 클라이언트)를 쓴다.

**`src/weather/activity_weather.py`** — 신규, 전문 그대로(105줄)

````python
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
````

**`src/utils/metric_priority.py`** — 수정, 아래 diff 그대로

````diff
--- a/src/utils/metric_priority.py
+++ b/src/utils/metric_priority.py
@@ -29,6 +29,7 @@
     ("runpulse:ml", 10),
     ("runpulse:formula", 20),
     ("runpulse:rule", 30),
+    ("open_meteo", 90),        # 외기 기상(P7-PRED-32) — 기기 온도 보정값(device_corrected, 999)보다 우선
     ("garmin", 100),
     ("intervals", 110),
     ("strava", 120),
````

**`src/sync.py`** — 수정, 아래 diff 그대로 — 메트릭 계산 직전에 기상 인제스트(실패해도 sync 계속)

````diff
--- a/src/sync.py
+++ b/src/sync.py
@@ -131,6 +131,12 @@
         start_date = (date.today() - timedelta(days=args.days)).isoformat()
         end_date = date.today().isoformat()
         with sqlite3.connect(str(db_path)) as conn:
+            try:  # 외기 기상(P7-PRED-32) — 예측·기온 보정 입력이므로 메트릭 계산 전에
+                from src.utils.api import get as api_get
+                from src.weather.activity_weather import ingest_activity_weather
+                log.info("기상 인제스트: %s", ingest_activity_weather(conn, api_get, since=start_date, max_requests=200))
+            except Exception as w_exc:
+                log.error("기상 인제스트 실패 (sync는 정상 완료): %s", w_exc)
             metrics_engine.run_for_date_range(conn, start_date, end_date)
             try:
                 filled = metrics_engine.backfill_missing_loads(conn)
````

**`tests/test_weather_ingest.py`** — 신규, 전문 그대로(57줄)

````python
"""P7-PRED-32: 활동 기상 인제스트·캐시·폴백·충돌."""
from datetime import date

from src.metrics.base import CalcContext
from src.weather import provider as om
from src.weather.activity_weather import ingest_activity_weather
from tests.helpers_pred import mem_conn, seed_run
from tests.test_weather_provider import _hourly

om.MIN_INTERVAL_S = 0.0


class FakeGet:
    def __init__(self, resp):
        self.resp, self.calls = resp, []

    def __call__(self, url, params=None):
        self.calls.append((url, params))
        if isinstance(self.resp, Exception):
            raise self.resp
        return self.resp


def test_ingest_open_meteo_then_cache_hit():
    c = mem_conn()
    a1 = seed_run(c, sid="1", date="2026-07-01", t="07:00:00", moving=3600, temp=None)   # 중간 07:30
    seed_run(c, sid="2", date="2026-07-01", t="18:00:00", moving=1800)                  # 같은 좌표·날짜 → 캐시
    g = FakeGet(_hourly())
    st = ingest_activity_weather(c, g, today=date(2026, 9, 26))
    assert len(g.calls) == 1 and st["open_meteo"] == 2 and st["requests"] == 1
    ctx = CalcContext(conn=c, scope_type="activity", scope_id=str(a1))
    assert ctx.get_activity_metric(a1, "weather_temp_c") == 23.75
    assert ingest_activity_weather(c, g, today=date(2026, 9, 26))["open_meteo"] == 0     # 재실행 시 대상 없음


def test_offline_falls_back_to_device_and_retries_later():
    c = mem_conn()
    aid = seed_run(c, sid="1", date="2026-07-01", temp=24.0)
    st = ingest_activity_weather(c, FakeGet(OSError("offline")), today=date(2026, 9, 26))
    assert st["failed_requests"] == 1 and st["device_corrected"] == 1
    ctx = CalcContext(conn=c, scope_type="activity", scope_id=str(aid))
    assert ctx.get_activity_metric(aid, "weather_temp_c") == 20.0            # (24−11)/0.65
    st2 = ingest_activity_weather(c, FakeGet(_hourly()), today=date(2026, 9, 26))
    assert st2["open_meteo"] == 1 and ctx.get_activity_metric(aid, "weather_temp_c") != 20.0   # open_meteo 가 primary


def test_no_coords_no_device():
    c = mem_conn()
    seed_run(c, sid="1", lat=None, lon=None, temp=None)
    g = FakeGet(_hourly())
    assert ingest_activity_weather(c, g)["no_data"] == 1 and g.calls == []


def test_conflict_flag():
    c = mem_conn()
    seed_run(c, sid="1", date="2026-07-01", t="07:00:00", moving=3600, temp=40.0)   # 기기 보정 44.6 vs 23.75
    assert ingest_activity_weather(c, FakeGet(_hourly()), today=date(2026, 9, 26))["conflicts"] == 1
````

**`src/utils/metric_registry.py`** — 수정, 아래 diff 그대로

````diff
--- a/src/utils/metric_registry.py
+++ b/src/utils/metric_registry.py
@@ -419,4 +419,7 @@
     MetricDef("weather_pressure_hpa", "weather", "metric", "hPa", "기압"),
     MetricDef("weather_condition", "weather", "metric", "", "날씨 상태 텍스트"),
+    MetricDef("weather_feels_like_c", "weather", "metric", "°C", "체감 기온"),
+    MetricDef("weather_wbgt_c", "weather", "metric", "°C", "WBGT 근사(그늘, BoM 식)"),
+    MetricDef("weather_source", "weather", "metric", "", "기상값 출처(open_meteo/device_corrected/device_raw)"),
 
     # ── body (metric_store) ──
````

검증:
```
python3 -m pytest tests/test_weather_provider.py tests/test_weather_ingest.py tests/test_doc_sync.py -q
python3 scripts/gen_metric_dictionary.py
python3 scripts/check_data_consistency.py
```

## P7-PRED-33 — 개인 기온 영향 모델(일별 `heat_model`)

- 의존: P7-PRED-14, P7-PRED-22, P7-PRED-32 · UI 노출: P7-PRED-72(기온별 예측 표의 근거 문구) · 실DB: 재계산 시 생성
- 파일: `src/metrics/heat_model.py`(신규), `tests/test_heat_model.py`(신규), `src/metrics/engine.py`, `src/utils/metric_registry.py`, `scripts/check_docs.py`
- 식: 최근 365일 정상 주행 1km 랩(3번째 랩부터, HR 110~190, 3:50~7:30/km, 비대회·실외)에서 `speed = a + b·HR + h·max(0,T−15) + c·max(0,5−T)` 최소제곱 → `heat = h/v160·100`, `cold = c/v160·100` (%/℃, v160 = a+160b). 점이 60개 미만이면 기본값. **수축**: 가중 `n/(n+400)` 으로 기본값(heat −0.62, cold −0.84 — 2025-05~12 학습 구간 적합값)에 당긴다. 양수(더위에 빨라짐)는 0으로 자른다.
- 실측(사본 DB, 2026-09-26): 점 886개, 원추정 heat −0.762·cold −0.729, 가중 0.689 → heat −0.718·cold −0.764 %/℃. 외기 기온 모델 R² 0.42(심박만 0.34). 겨울 잔차 −4~−7%는 설명되지 않는다(열린 질문).

**`src/metrics/heat_model.py`** — 신규, 전문 그대로(70줄)

````python
"""개인 기온 영향 모델(일별) — 정상 주행 랩의 HR·속도·외기 기온 회귀로 더위/추위 계수(%/℃)를 추정해 기본값으로 수축(P7-PRED-33).

speed = a + b·HR + h·max(0, T−15) + c·max(0, 5−T)  →  heat = h/v160·100, cold = c/v160·100 (v160 = a + 160b)
수축: 가중 n/(n+400) (n = 적합 점 수), 기본값 heat −0.62 / cold −0.84 %/℃ (2025-05~12 학습 구간 적합값).
"""
from __future__ import annotations

from src.metrics.base import CalcContext, CalcResult, MetricCalculator
from src.metrics.prediction.signals import steady_points

DEFAULT_HEAT, DEFAULT_COLD = -0.62, -0.84
SHRINK_N = 400
MIN_POINTS = 60


def ols(X: list[list[float]], y: list[float]) -> list[float] | None:
    """정규방정식 가우스-조던. 특이행렬이면 None."""
    k = len(X[0])
    A = [[sum(r[i] * r[j] for r in X) for j in range(k)] for i in range(k)]
    b = [sum(r[i] * v for r, v in zip(X, y)) for i in range(k)]
    for i in range(k):
        pv = A[i][i]
        if abs(pv) < 1e-12:
            return None
        A[i] = [v / pv for v in A[i]]
        b[i] /= pv
        for j in range(k):
            if j != i:
                f = A[j][i]
                A[j] = [v - f * w for v, w in zip(A[j], A[i])]
                b[j] -= f * b[i]
    return b


def fit_heat(points: list[tuple[float, float, float]]) -> dict:
    """points: [(hr, speed_ms, ambient_c)] → {"heat","cold","n","raw_heat","raw_cold"} (수축 후)."""
    n = len(points)
    raw_h = raw_c = None
    if n >= MIN_POINTS:
        co = ols([[1.0, h, max(0.0, t - 15), max(0.0, 5 - t)] for h, _, t in points], [v for _, v, _ in points])
        if co:
            v160 = co[0] + co[1] * 160
            if v160 > 0:
                raw_h, raw_c = co[2] / v160 * 100, co[3] / v160 * 100
    w = n / (n + SHRINK_N) if raw_h is not None else 0.0
    heat = DEFAULT_HEAT + w * ((raw_h or 0.0) - DEFAULT_HEAT)
    cold = DEFAULT_COLD + w * ((raw_c or 0.0) - DEFAULT_COLD)
    return {"heat": round(min(0.0, heat), 3), "cold": round(min(0.0, cold), 3), "n": n,
            "raw_heat": raw_h and round(raw_h, 3), "raw_cold": raw_c and round(raw_c, 3), "weight": round(w, 3)}


class HeatModelCalculator(MetricCalculator):
    name = "heat_model"
    provider = "runpulse:formula_v1"
    version = "1.0"
    scope_type = "daily"
    category = "weather"
    display_name = "기온 영향 계수"
    description = "15℃ 대비 기온 1℃당 속도 변화(%). 더위(15℃ 초과)·추위(5℃ 미만) 각각, 개인 데이터로 기본값을 보정."
    unit = "%/℃"
    format_type = "json"
    requires = []
    produces = ["heat_model"]

    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        runs = ctx.get_runs(365, with_laps=True, include_end=False)
        for r in runs:
            r["ambient_c"] = ctx.get_activity_metric(r["id"], "weather_temp_c")
        fit = fit_heat([p for r in runs for p in steady_points(r)])
        return [self._result(value=fit["heat"], json_val=fit, confidence=round(0.3 + 0.6 * fit["weight"], 2))]
````

**`tests/test_heat_model.py`** — 신규, 전문 그대로(25줄)

````python
"""P7-PRED-33: 기온 계수 적합 + 수축."""
from src.metrics.heat_model import fit_heat, ols


def test_ols_exact():
    X = [[1, x] for x in range(5)]
    assert [round(v, 6) for v in ols(X, [2 + 3 * x for x in range(5)])] == [2.0, 3.0]


def test_few_points_returns_default():
    f = fit_heat([(150, 3.0, 20)] * 10)
    assert (f["heat"], f["cold"], f["weight"]) == (-0.62, -0.84, 0.0)


def test_shrinkage_toward_truth():
    pts = []
    for i in range(400):
        hr = 140 + (i % 30)
        t = -5 + (i % 37)
        v = (1.0 + 0.0125 * hr) * (1 - 0.01 * max(0, t - 15) - 0.005 * max(0, 5 - t))
        pts.append((hr, v, t))
    f = fit_heat(pts)
    assert f["weight"] == 0.5
    assert -1.0 < f["raw_heat"] < -0.9 and -0.55 < f["raw_cold"] < -0.45
    assert round(f["heat"], 2) == round((-0.62 + f["raw_heat"]) / 2, 2)
````

**`src/metrics/engine.py`** — 수정, 아래 diff 그대로

````diff
--- a/src/metrics/engine.py
+++ b/src/metrics/engine.py
@@ -35,4 +35,5 @@
 from src.metrics.darp import DARPCalculator
 from src.metrics.hr_profile import HRProfileCalculator
+from src.metrics.heat_model import HeatModelCalculator
 from src.metrics.tids import TIDSCalculator
 from src.metrics.rmr import RMRCalculator
@@ -92,4 +93,5 @@
     DICalculator(),
     HRProfileCalculator(),
+    HeatModelCalculator(),
     DARPCalculator(),
     TIDSCalculator(),
````

**`src/utils/metric_registry.py`** — 수정, 아래 diff 그대로

````diff
--- a/src/utils/metric_registry.py
+++ b/src/utils/metric_registry.py
@@ -422,4 +422,5 @@
     MetricDef("weather_wbgt_c", "weather", "metric", "°C", "WBGT 근사(그늘, BoM 식)"),
     MetricDef("weather_source", "weather", "metric", "", "기상값 출처(open_meteo/device_corrected/device_raw)"),
+    MetricDef("heat_model", "weather", "metric", "%/℃", "개인 기온 영향 계수(더위·추위)", scope="daily"),
 
     # ── body (metric_store) ──
````

**`scripts/check_docs.py`** — 수정, 아래 diff 그대로 — calculator 수 33 → 34

````diff
--- a/scripts/check_docs.py
+++ b/scripts/check_docs.py
@@ -816,11 +816,11 @@
         else:
             ok(f"engine.py: 실행 함수 {required_fns} 전부 존재")
-        # ALL_CALCULATORS 수 검증 (설계: 33개)
+        # ALL_CALCULATORS 수 검증 (설계: 34개)
         try:
             from src.metrics.engine import ALL_CALCULATORS
-            if len(ALL_CALCULATORS) != 33:
-                error(f"ALL_CALCULATORS 수: {len(ALL_CALCULATORS)}개 (설계: 33개)")
+            if len(ALL_CALCULATORS) != 34:
+                error(f"ALL_CALCULATORS 수: {len(ALL_CALCULATORS)}개 (설계: 34개)")
             else:
-                ok(f"ALL_CALCULATORS 수: {len(ALL_CALCULATORS)}개 (설계 33개 일치)")
+                ok(f"ALL_CALCULATORS 수: {len(ALL_CALCULATORS)}개 (설계 34개 일치)")
         except Exception:
             warn("ALL_CALCULATORS import 실패 — 수 검증 건너뜀")
````

검증:
```
python3 scripts/gen_metric_dictionary.py
python3 -m pytest tests/test_heat_model.py tests/test_doc_sync.py tests/test_metric_naming.py tests/test_validator.py -q
python3 scripts/check_docs.py
python3 scripts/check_data_consistency.py
```


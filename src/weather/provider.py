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

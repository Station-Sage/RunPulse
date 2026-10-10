"""예보 기온 → 날짜별 폭염 보정(%) (E10) — 최근 러닝 시작 좌표의 7일 예보(아침 6~8시 평균)로 페이스 완화 폭을 구한다.

네트워크·좌표 실패는 빈 dict(보정 없음). 계수는 heat_model 기본값(DEFAULT_HEAT %/℃, 15℃ 초과분).
"""
from __future__ import annotations

import sqlite3
from datetime import date
from typing import Any, Callable

from src.metrics.heat_model import DEFAULT_HEAT
from src.weather import provider as om

MORNING_HOURS = (6, 7, 8)


def home_coords(conn: sqlite3.Connection) -> tuple[float, float] | None:
    """가장 최근 러닝의 시작 좌표."""
    r = conn.execute("SELECT start_lat, start_lon FROM v_canonical_activities WHERE start_lat IS NOT NULL"
                     " AND start_lon IS NOT NULL AND activity_type IN ('running','trail_running')"
                     " ORDER BY start_time DESC LIMIT 1").fetchone()
    return (r[0], r[1]) if r else None


def morning_temps(hourly: dict) -> dict[str, float]:
    """hourly(open-meteo) → {날짜: 아침 6~8시 평균 기온}."""
    acc: dict[str, list[float]] = {}
    for i, t in enumerate(hourly.get("time") or []):
        v = (hourly.get("temperature_2m") or [None] * (i + 1))[i]
        if v is not None and int(t[11:13]) in MORNING_HOURS:
            acc.setdefault(t[:10], []).append(float(v))
    return {d: sum(v) / len(v) for d, v in acc.items()}


def heat_pcts(temps: dict[str, float], coef: float = DEFAULT_HEAT) -> dict[str, float]:
    """기온 → 페이스 완화 %(양수). 15℃ 이하는 0."""
    return {d: round(-coef * max(0.0, t - 15.0), 2) for d, t in temps.items()}


def forecast_heat_pct(conn: sqlite3.Connection, getter: Callable[..., Any], today: date | None = None) -> dict[str, float]:
    today = today or date.today()
    xy = home_coords(conn)
    if not xy:
        return {}
    url, params = om.request_params(xy[0], xy[1], today.isoformat(), today)
    params.update(past_days=0, forecast_days=7)
    try:
        raw = getter(url, params=params)
    except Exception:
        return {}
    h = raw.get("hourly") if isinstance(raw, dict) else None
    return heat_pcts(morning_temps(h)) if h else {}

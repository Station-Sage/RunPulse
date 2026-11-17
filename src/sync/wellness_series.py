"""Garmin 웰니스 raw payload → wellness_series 시계열 + 파생 요약 (REVIEW-10 A6).

순수 파서(parse_*)와 저장(save_series)을 분리한다. 요약 지표는 파생값만 metric_store 에 둔다.
보존: 최근 RETENTION_DAYS 일(오래된 날짜는 저장하지 않고 기존 행은 정리).
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date as _date, datetime, timedelta, timezone

from src.utils.db_helpers import upsert_metric

RETENTION_DAYS = 400
SOURCE = "garmin"
_STAGE_NAMES = {0: "deep", 1: "light", 2: "rem", 3: "awake"}

Row = tuple[str, int, float | None, str | None]  # kind, ts, value, meta_json


def _epoch(v) -> int | None:
    """ms epoch(int/float) 또는 GMT 문자열 → UTC epoch 초."""
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return int(v / 1000) if v > 1e11 else int(v)
    try:
        dt = datetime.fromisoformat(str(v).replace("Z", ""))
    except ValueError:
        return None
    return int(dt.replace(tzinfo=timezone.utc).timestamp())


def _num(v) -> float | None:
    if isinstance(v, bool) or v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _pairs(kind: str, arr, min_value: float = 0.0) -> list[Row]:
    """[[ts, value, ...], ...] 배열 → 행(body_battery 는 [ts, status, level, ver]). min_value 미만(측정 불가 -1 등)은 제외."""
    rows: list[Row] = []
    for item in arr or []:
        if not isinstance(item, (list, tuple)) or len(item) < 2:
            continue
        ts = _epoch(item[0])
        val = _num(item[2] if kind == "body_battery" and len(item) > 2 else item[1])
        if ts is None or val is None or val < min_value:
            continue
        rows.append((kind, ts, val, None))
    return rows


def _dicts(kind: str, arr, ts_key: str, val_key: str) -> list[Row]:
    rows: list[Row] = []
    for item in arr or []:
        if not isinstance(item, dict):
            continue
        ts, val = _epoch(item.get(ts_key)), _num(item.get(val_key))
        if ts is not None and val is not None:
            rows.append((kind, ts, val, None))
    return rows


def parse_hrv(payload: dict | None) -> list[Row]:
    return _dicts("hrv_5min", (payload or {}).get("hrvReadings"), "readingTimeGMT", "hrvValue")


def parse_sleep(payload: dict | None) -> list[Row]:
    p = payload or {}
    rows: list[Row] = []
    for lv in p.get("sleepLevels") or []:
        if not isinstance(lv, dict):
            continue
        start, end, lvl = _epoch(lv.get("startGMT")), _epoch(lv.get("endGMT")), _num(lv.get("activityLevel"))
        if start is None or lvl is None:
            continue
        meta = json.dumps({"end": end}) if end is not None else None
        rows.append(("sleep_stage", start, lvl, meta))
    rows += _dicts("sleep_hr", p.get("sleepHeartRate"), "startGMT", "value")
    rows += _dicts("spo2", p.get("wellnessEpochSPO2DataDTOList"), "epochTimestamp", "spo2Reading")
    rows += _dicts("respiration", p.get("wellnessEpochRespirationDataDTOList"),
                   "startTimeGMT", "respirationValue")
    return rows


def parse_body_battery(payload) -> list[Row]:
    data = payload.get("data") if isinstance(payload, dict) else payload
    rows: list[Row] = []
    for day in data or []:
        if isinstance(day, dict):
            rows += _pairs("body_battery", day.get("bodyBatteryValuesArray"))
    return rows


def parse_stress(payload: dict | None) -> list[Row]:
    return _pairs("stress", (payload or {}).get("stressValuesArray"))


def parse_hr_day(payload: dict | None) -> list[Row]:
    return _pairs("hr_day", (payload or {}).get("heartRateValues"), min_value=1.0)


def _percentile(sorted_vals: list[float], q: float) -> float:
    k = (len(sorted_vals) - 1) * q
    lo = int(k)
    hi = min(lo + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (k - lo)


def derive_summary(rows: list[Row]) -> dict[str, float]:
    """시계열 → 파생 요약(야간 HRV 분포, 수면 중 최저 HR, 수면 단계 분)."""
    out: dict[str, float] = {}
    hrv = sorted(v for k, _, v, _ in rows if k == "hrv_5min" and v is not None)
    if hrv:
        out["hrv_night_min"] = hrv[0]
        out["hrv_night_p10"] = round(_percentile(hrv, 0.10), 1)
        out["hrv_night_p90"] = round(_percentile(hrv, 0.90), 1)
    hr = [v for k, _, v, _ in rows if k == "sleep_hr" and v is not None and v > 0]
    if hr:
        out["sleep_hr_min"] = min(hr)
    stage_sec: dict[str, float] = {}
    for k, ts, lvl, meta in rows:
        if k != "sleep_stage" or not meta:
            continue
        name = _STAGE_NAMES.get(int(lvl)) if lvl is not None else None
        end = json.loads(meta).get("end")
        if name and end and end > ts:
            stage_sec[name] = stage_sec.get(name, 0) + (end - ts)
    for name, sec in stage_sec.items():
        out[f"sleep_stage_{name}_min"] = round(sec / 60.0, 1)
    return out


def save_series(conn: sqlite3.Connection, date_str: str, rows: list[Row],
                source: str = SOURCE, today: _date | None = None) -> int:
    """(date, source, kind) 단위 교체 저장 + 보존 기간 밖 행 정리. 저장 행 수 반환."""
    today = today or datetime.now(timezone.utc).date()
    cutoff = (today - timedelta(days=RETENTION_DAYS)).isoformat()
    conn.execute("DELETE FROM wellness_series WHERE date < ?", (cutoff,))
    if date_str < cutoff or not rows:
        return 0
    for kind in {r[0] for r in rows}:
        conn.execute(
            "DELETE FROM wellness_series WHERE date=? AND source=? AND kind=?",
            (date_str, source, kind),
        )
    conn.executemany(
        "INSERT OR REPLACE INTO wellness_series (date, source, kind, ts, value, meta) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        [(date_str, source, k, ts, v, m) for k, ts, v, m in rows],
    )
    return len(rows)


def ingest_day(conn: sqlite3.Connection, date_str: str, raw_payloads: dict,
               today: _date | None = None) -> int:
    """하루치 raw payload 묶음에서 시계열을 저장하고 파생 요약을 metric_store 에 기록."""
    rows = (
        parse_hrv(raw_payloads.get("wellness_hrv"))
        + parse_sleep(raw_payloads.get("wellness_sleep"))
        + parse_body_battery(raw_payloads.get("wellness_body_battery"))
        + parse_stress(raw_payloads.get("wellness_stress"))
    )
    return _save_with_summary(conn, date_str, rows, today)


def ingest_hr_day(conn: sqlite3.Connection, date_str: str, payload: dict,
                  today: _date | None = None) -> int:
    return _save_with_summary(conn, date_str, parse_hr_day(payload), today)


def _save_with_summary(conn, date_str, rows, today) -> int:
    n = save_series(conn, date_str, rows, today=today)
    if n:
        for name, val in derive_summary(rows).items():
            upsert_metric(conn, "daily", date_str, name, SOURCE,
                          numeric_value=val, category="wellness")
    return n

"""Garmin 참조값 동기화(P7-PRED-25) — 젖산역치(LTHR·역치속도) 일별 스냅샷, 레이스 예측 일별 스냅샷 + 이력 백필.

저장: metric_store daily, provider='garmin' — lthr_ref, lt_speed_ref, garmin_ftp, race_pred_{5k,10k,half,marathon}_sec.
원본은 source_payloads(entity_type 'lactate_threshold_day' / 'race_predictions' / 이력은 '*_range') 에 보존.
API 실패는 로그 후 0 반환(동기화 중단 금지). client 는 garminconnect.Garmin (테스트는 가짜 객체).
"""
from __future__ import annotations

import logging
import sqlite3
from datetime import date, timedelta

from src.sync.garmin_helpers import _store_raw_payload
from src.sync.garmin_ref_parsers import parse_lactate_threshold, parse_race_predictions
from src.utils.db_helpers import upsert_metric

log = logging.getLogger(__name__)
RACE_METRICS = ("race_pred_5k_sec", "race_pred_10k_sec", "race_pred_half_sec", "race_pred_marathon_sec")


def _store_lt(conn, items: list[dict]) -> int:
    n = 0
    for it in items:
        for name, key in (("lthr_ref", "lthr_ref"), ("lt_speed_ref", "lt_speed_ref"), ("garmin_ftp", "ftp")):
            if it.get(key) is not None:
                upsert_metric(conn, "daily", it["date"], name, "garmin", numeric_value=it[key])
                n += 1
    return n


def _store_rp(conn, items: list[dict]) -> int:
    n = 0
    for it in items:
        for name in RACE_METRICS:
            if it.get(name) is not None:
                upsert_metric(conn, "daily", it["date"], name, "garmin", numeric_value=it[name])
                n += 1
    return n


def sync_lactate_threshold(conn: sqlite3.Connection, client, date_str: str) -> int:
    """최신 LT 스냅샷(측정일 기준 저장). 반환: 저장한 값 수."""
    try:
        raw = client.get_lactate_threshold()
    except Exception as e:
        log.warning("garmin lactate_threshold 실패 %s: %s", date_str, e)
        return 0
    if not raw:
        return 0
    _store_raw_payload(conn, "lactate_threshold_day", date_str, raw)
    return _store_lt(conn, parse_lactate_threshold(raw, date_str))


def sync_race_predictions(conn: sqlite3.Connection, client, date_str: str) -> int:
    """오늘 레이스 예측 스냅샷."""
    try:
        raw = client.get_race_predictions()
    except Exception as e:
        log.warning("garmin race_predictions 실패 %s: %s", date_str, e)
        return 0
    if not raw:
        return 0
    _store_raw_payload(conn, "race_predictions", date_str, raw)
    return _store_rp(conn, parse_race_predictions(raw, date_str))


_MAX_WINDOW_DAYS = 360  # Garmin 이력 API 는 조회 기간이 366일을 넘으면 400(실측 2026-09-26)


def _windows(start: str, end: str):
    s, e = date.fromisoformat(start), date.fromisoformat(end)
    while s <= e:
        w_end = min(s + timedelta(days=_MAX_WINDOW_DAYS - 1), e)
        yield s.isoformat(), w_end.isoformat()
        s = w_end + timedelta(days=1)


def backfill_history(conn: sqlite3.Connection, client, start: str, end: str) -> dict:
    """이력 백필: get_race_predictions(start, end, 'daily'), get_lactate_threshold(latest=False, ...).
    조회 기간 제한(366일) 때문에 360일 창으로 나눠 호출한다. 창 하나가 실패해도 나머지는 계속한다.
    파싱 0건이면 raw 만 남기고 {"*_parsed": 0} 로 보고한다."""
    out = {"race_parsed": 0, "lt_parsed": 0}
    for ws, we in _windows(start, end):
        try:
            raw = client.get_race_predictions(ws, we, "daily")
            if raw:
                _store_raw_payload(conn, "race_predictions_range", f"{ws}_{we}", raw)
                out["race_parsed"] += _store_rp(conn, parse_race_predictions(raw, we))
        except Exception as e:
            log.warning("garmin race_predictions 이력 실패 %s~%s: %s", ws, we, e)
        try:
            raw = client.get_lactate_threshold(latest=False, start_date=ws, end_date=we)
            if raw:
                _store_raw_payload(conn, "lactate_threshold_range", f"{ws}_{we}", raw)
                out["lt_parsed"] += _store_lt(conn, parse_lactate_threshold(raw, we))
        except Exception as e:
            log.warning("garmin lactate_threshold 이력 실패 %s~%s: %s", ws, we, e)
    conn.commit()
    return out

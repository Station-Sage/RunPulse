"""Strava 활동의 Lap(`/laps`)·HR 존(`/zones`) 조회·저장."""

from __future__ import annotations

import logging

import requests

from src.sync._helpers import save_laps, save_metrics
from src.sync.raw_store import upsert_raw_payload

log = logging.getLogger(__name__)

STRAVA_API = "https://www.strava.com/api/v3"


def _get(headers, limiter, result, sid, suffix):
    """GET 한 번. 429 는 호출자가 중단 판단하도록 다시 던지고, 그 외 실패는 None."""
    try:
        limiter.pre_request()
        resp = requests.get(f"{STRAVA_API}/activities/{sid}/{suffix}", headers=headers, timeout=30)
        resp.raise_for_status()
        payload = resp.json()
        limiter.post_request(True)
        result.api_calls += 1
        return payload
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 429:
            raise
        log.warning("[strava] %s 조회 실패 %s: %s", suffix, sid, e)
    except (requests.RequestException, ValueError) as e:
        log.warning("[strava] %s 조회 실패 %s: %s", suffix, sid, e)
    return None


def fetch_and_save_laps_zones(conn, headers, extractor, limiter, result, sid, aid) -> None:
    """Lap 과 HR 존을 받아 저장. 존은 유료 계정만 응답(그 외 4xx 는 건너뜀)."""
    laps_raw = _get(headers, limiter, result, sid, "laps")
    if laps_raw:
        upsert_raw_payload(conn, "strava", "activity_laps", sid, {"laps": laps_raw}, activity_id=aid)
        laps = extractor.extract_activity_laps(laps_raw)
        if laps:
            save_laps(conn, aid, laps)

    zones_raw = _get(headers, limiter, result, sid, "zones")
    if zones_raw:
        upsert_raw_payload(conn, "strava", "activity_zones", sid, {"zones": zones_raw}, activity_id=aid)
        metrics = extractor.extract_zone_metrics(zones_raw)
        if metrics:
            save_metrics(conn, "activity", str(aid), "strava", metrics)

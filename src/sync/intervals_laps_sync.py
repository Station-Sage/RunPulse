"""Intervals.icu 활동의 구간(icu_intervals) 조회·Lap 저장."""

from __future__ import annotations

import logging

import requests

from src.sync._helpers import save_laps
from src.sync.raw_store import upsert_raw_payload

log = logging.getLogger(__name__)

_RUN_TYPES = {"Run", "TrailRun", "VirtualRun"}


def fetch_and_save_interval_laps(conn, extractor, limiter, result, base, auth, raw, aid) -> int:
    """러닝 활동의 `/activity/{id}/intervals` 를 받아 activity_laps 에 저장. 실패는 로그만 남기고 계속."""
    sid = str(raw.get("id", ""))
    if not sid or raw.get("type") not in _RUN_TYPES:
        return 0
    try:
        limiter.pre_request()
        resp = requests.get(f"{base}/activity/{sid}/intervals", auth=auth, timeout=30)
        resp.raise_for_status()
        payload = resp.json()
        limiter.post_request(True)
        result.api_calls += 1
    except (requests.RequestException, ValueError) as e:
        log.warning("[intervals] 구간 조회 실패 %s: %s", sid, e)
        return 0
    upsert_raw_payload(conn, "intervals", "activity_intervals", sid, payload, activity_id=aid)
    laps = extractor.extract_activity_laps(payload)
    return save_laps(conn, aid, laps) if laps else 0

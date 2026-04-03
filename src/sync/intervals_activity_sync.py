"""Intervals.icu 활동 + wellness 동기화 Orchestrator."""

from __future__ import annotations

import logging
import requests
from datetime import datetime, timedelta, timezone

from src.sync.extractors import get_extractor
from src.sync.rate_limiter import RateLimiter
from src.sync.raw_store import upsert_raw_payload, update_raw_activity_id
from src.sync.sync_result import SyncResult
from src.sync._helpers import (
    save_activity_core, save_metrics, save_laps,
    save_daily_wellness, save_daily_fitness, resolve_primaries,
)

log = logging.getLogger(__name__)


def sync(
    conn, days: int = 7, include_streams: bool = False,
    *, config: dict = None, _sleep_fn=None,
) -> SyncResult:
    result = SyncResult(source="intervals", job_type="activity")
    extractor = get_extractor("intervals")
    limiter = RateLimiter("intervals", sleep_fn=_sleep_fn)

    if config is None:
        from src.utils.config import load_config
        config = load_config()
    icu = config.get("intervals", {})
    athlete_id = icu.get("athlete_id")
    api_key = icu.get("api_key")
    if not athlete_id or not api_key:
        result.status = "skipped"
        result.last_error = "Intervals.icu credentials not configured"
        return result

    base = f"https://intervals.icu/api/v1/athlete/{athlete_id}"
    auth = ("API_KEY", api_key)

    end_date = datetime.now(timezone.utc).date()
    start_date = end_date - timedelta(days=days)

    try:
        limiter.pre_request()
        resp = requests.get(f"{base}/activities", auth=auth, params={
            "oldest": start_date.isoformat(), "newest": end_date.isoformat(),
        })
        resp.raise_for_status()
        activities = resp.json()
        limiter.post_request(True)
        result.api_calls += 1
    except Exception as e:
        result.status = "failed"
        result.last_error = str(e)
        return result

    result.total_items = len(activities)

    for raw in activities:
        sid = str(raw.get("id", ""))
        try:
            is_new = upsert_raw_payload(conn, "intervals", "activity_summary", sid, raw)
            if not is_new:
                result.skipped_count += 1
                continue

            core = extractor.extract_activity_core(raw)
            aid = save_activity_core(conn, core)
            update_raw_activity_id(conn, "intervals", "activity_summary", sid, aid)

            metrics = extractor.extract_activity_metrics(raw, raw)
            if metrics:
                save_metrics(conn, "activity", str(aid), "intervals", metrics)

            laps = extractor.extract_activity_laps(raw)
            if laps:
                save_laps(conn, aid, laps)

            resolve_primaries(conn, "activity", str(aid))
            result.synced_count += 1
            conn.commit()

        except Exception as e:
            log.error("[intervals] Error for %s: %s", sid, e)
            result.error_count += 1
            result.errors.append((sid, str(e)))
            conn.rollback()

    if result.error_count == 0:
        result.status = "success"
    return result


def sync_wellness(
    conn, days: int = 7, *, config: dict = None, _sleep_fn=None,
) -> SyncResult:
    result = SyncResult(source="intervals", job_type="wellness")
    extractor = get_extractor("intervals")
    limiter = RateLimiter("intervals", sleep_fn=_sleep_fn)

    if config is None:
        from src.utils.config import load_config
        config = load_config()
    icu = config.get("intervals", {})
    athlete_id = icu.get("athlete_id")
    api_key = icu.get("api_key")
    if not athlete_id or not api_key:
        result.status = "skipped"
        return result

    base = f"https://intervals.icu/api/v1/athlete/{athlete_id}"
    auth = ("API_KEY", api_key)

    end_date = datetime.now(timezone.utc).date()
    start_date = end_date - timedelta(days=days)

    try:
        limiter.pre_request()
        resp = requests.get(f"{base}/wellness", auth=auth, params={
            "oldest": start_date.isoformat(), "newest": end_date.isoformat(),
        })
        resp.raise_for_status()
        wellness_list = resp.json()
        limiter.post_request(True)
        result.api_calls += 1
    except Exception as e:
        result.status = "failed"
        result.last_error = str(e)
        return result

    result.total_items = len(wellness_list)

    for w in wellness_list:
        ds = w.get("id", "")
        if not ds:
            continue
        try:
            is_new = upsert_raw_payload(conn, "intervals", "wellness_day", ds, w, entity_date=ds)
            if not is_new:
                result.skipped_count += 1
                continue

            core = extractor.extract_wellness_core(ds, wellness=w)
            if core:
                save_daily_wellness(conn, ds, core)

            metrics = extractor.extract_wellness_metrics(ds, wellness=w)
            if metrics:
                save_metrics(conn, "daily", ds, "intervals", metrics)

            fitness = extractor.extract_fitness(ds, w)
            if fitness.get("ctl") is not None or fitness.get("vo2max") is not None:
                save_daily_fitness(conn, ds, "intervals", fitness)

            resolve_primaries(conn, "daily", ds)
            result.synced_count += 1
            conn.commit()
        except Exception as e:
            log.error("[intervals/wellness] Error for %s: %s", ds, e)
            result.error_count += 1
            conn.rollback()

    if result.error_count == 0:
        result.status = "success"
    return result

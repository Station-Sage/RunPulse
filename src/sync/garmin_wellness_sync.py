"""Garmin 일별 wellness 동기화 Orchestrator."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from src.sync.extractors import get_extractor
from src.sync.rate_limiter import RateLimiter
from src.sync.raw_store import upsert_raw_payload
from src.sync.sync_result import SyncResult
from src.sync._helpers import (
    save_daily_wellness,
    save_metrics,
    save_daily_fitness,
    resolve_primaries,
)

log = logging.getLogger(__name__)


class _RateLimitStop(Exception):
    pass


WELLNESS_ENDPOINTS = {
    "sleep_day": lambda api, d: api.get_sleep_data(d),
    "hrv_day": lambda api, d: api.get_hrv_data(d),
    "body_battery_day": lambda api, d: api.get_body_battery(d),
    "stress_day": lambda api, d: api.get_stress_data(d),
    "user_summary_day": lambda api, d: api.get_user_summary(d),
    "training_readiness": lambda api, d: api.get_training_readiness(d),
}


def sync(conn, api, days: int = 7, *, _sleep_fn=None) -> SyncResult:
    """Garmin wellness 동기화."""
    result = SyncResult(source="garmin", job_type="wellness")
    extractor = get_extractor("garmin")
    limiter = RateLimiter("garmin", sleep_fn=_sleep_fn)

    end_date = datetime.now(timezone.utc).date()
    start_date = end_date - timedelta(days=days - 1)
    dates = []
    cur = start_date
    while cur <= end_date:
        dates.append(cur.isoformat())
        cur += timedelta(days=1)

    result.total_items = len(dates)

    for date_str in dates:
        try:
            synced = _sync_day(conn, api, extractor, limiter, result, date_str)
            if synced:
                result.synced_count += 1
            else:
                result.skipped_count += 1
            conn.commit()

        except _RateLimitStop:
            result.status = "partial"
            result.retry_after = _retry_after(limiter)
            conn.commit()
            break

        except Exception as e:
            log.error("[garmin/wellness] Error for %s: %s", date_str, e)
            result.error_count += 1
            result.errors.append((date_str, str(e)))
            result.last_error = str(e)
            conn.rollback()

    if result.error_count == 0 and not result.is_rate_limited():
        result.status = "success"
    elif result.synced_count > 0:
        result.status = "partial"

    return result


def _sync_day(conn, api, extractor, limiter, result, date_str) -> bool:
    raw_payloads = {}
    any_new = False

    for entity_type, fetch_fn in WELLNESS_ENDPOINTS.items():
        try:
            limiter.pre_request()
            raw = fetch_fn(api, date_str)
            limiter.post_request(success=True)
            result.api_calls += 1

            if raw:
                payload = raw if isinstance(raw, dict) else {"data": raw}
                is_new = upsert_raw_payload(
                    conn, "garmin", entity_type, date_str,
                    payload, entity_date=date_str,
                )
                if is_new:
                    any_new = True
                raw_payloads[entity_type] = payload

        except Exception as e:
            if _is_rate_limit_error(e):
                if not limiter.handle_rate_limit():
                    raise _RateLimitStop()
                continue
            log.warning("[garmin/wellness] %s failed for %s: %s", entity_type, date_str, e)

    if not any_new:
        return False

    core = extractor.extract_wellness_core(date_str, **raw_payloads)
    if core:
        save_daily_wellness(conn, date_str, core)

    metrics = extractor.extract_wellness_metrics(date_str, **raw_payloads)
    if metrics:
        save_metrics(conn, "daily", date_str, "garmin", metrics)

    user_summary = raw_payloads.get("user_summary_day", {})
    fitness = extractor.extract_fitness(date_str, user_summary)
    if fitness.get("vo2max") is not None:
        save_daily_fitness(conn, date_str, "garmin", fitness)

    resolve_primaries(conn, "daily", date_str)
    return True


def _is_rate_limit_error(e):
    s = str(e).lower()
    return "429" in s or "too many requests" in s or "TooManyRequests" in type(e).__name__


def _retry_after(limiter):
    wait = limiter.policy.backoff_base * (limiter.policy.backoff_multiplier ** limiter._consecutive_429)
    at = datetime.now(timezone.utc) + timedelta(seconds=wait)
    return at.isoformat() + "Z"

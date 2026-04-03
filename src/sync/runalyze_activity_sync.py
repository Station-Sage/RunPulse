"""Runalyze 활동 동기화 Orchestrator."""

from __future__ import annotations

import logging
import requests
from datetime import datetime, timedelta, timezone

from src.sync.extractors import get_extractor
from src.sync.rate_limiter import RateLimiter
from src.sync.raw_store import upsert_raw_payload, update_raw_activity_id
from src.sync.sync_result import SyncResult
from src.sync._helpers import save_activity_core, save_metrics, resolve_primaries

log = logging.getLogger(__name__)

RUNALYZE_API = "https://runalyze.com/api/v1"


def sync(
    conn, days: int = 7, *, config: dict = None, _sleep_fn=None,
) -> SyncResult:
    result = SyncResult(source="runalyze", job_type="activity")
    extractor = get_extractor("runalyze")
    limiter = RateLimiter("runalyze", sleep_fn=_sleep_fn)

    if config is None:
        from src.utils.config import load_config
        config = load_config()
    rc = config.get("runalyze", {})
    token = rc.get("token") or rc.get("api_key")
    if not token:
        result.status = "skipped"
        result.last_error = "Runalyze token not configured"
        return result

    headers = {"token": token}
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

    try:
        limiter.pre_request()
        resp = requests.get(
            f"{RUNALYZE_API}/activities", headers=headers,
            params={"since": since},
        )
        resp.raise_for_status()
        activities = resp.json()
        limiter.post_request(True)
        result.api_calls += 1
    except Exception as e:
        result.status = "failed"
        result.last_error = str(e)
        return result

    if isinstance(activities, dict):
        activities = activities.get("data", [])
    result.total_items = len(activities)

    for raw in activities:
        sid = str(raw.get("id", ""))
        try:
            is_new = upsert_raw_payload(conn, "runalyze", "activity_summary", sid, raw)
            if not is_new:
                result.skipped_count += 1
                continue

            core = extractor.extract_activity_core(raw)
            aid = save_activity_core(conn, core)
            update_raw_activity_id(conn, "runalyze", "activity_summary", sid, aid)

            metrics = extractor.extract_activity_metrics(raw)
            if metrics:
                save_metrics(conn, "activity", str(aid), "runalyze", metrics)

            resolve_primaries(conn, "activity", str(aid))
            result.synced_count += 1
            conn.commit()
        except Exception as e:
            log.error("[runalyze] Error for %s: %s", sid, e)
            result.error_count += 1
            result.errors.append((sid, str(e)))
            conn.rollback()

    if result.error_count == 0:
        result.status = "success"
    return result

"""Strava 활동 동기화 Orchestrator."""

from __future__ import annotations

import logging
import requests
from datetime import datetime, timedelta, timezone

from src.sync.extractors import get_extractor
from src.sync.rate_limiter import RateLimiter
from src.sync.raw_store import upsert_raw_payload, update_raw_activity_id
from src.sync.sync_result import SyncResult
from src.sync._helpers import (
    save_activity_core, save_metrics,
    save_streams, save_best_efforts, resolve_primaries,
)

log = logging.getLogger(__name__)

STRAVA_API = "https://www.strava.com/api/v3"
STREAM_KEYS = "time,distance,heartrate,velocity_smooth,cadence,altitude,grade_smooth,watts,temp,latlng"


def sync(
    conn, days: int = 7, include_streams: bool = True,
    *, config: dict = None, _sleep_fn=None,
) -> SyncResult:
    result = SyncResult(source="strava", job_type="activity")
    extractor = get_extractor("strava")
    limiter = RateLimiter("strava", sleep_fn=_sleep_fn)

    if config is None:
        from src.utils.config import load_config
        config = load_config()
    token = _ensure_token(config)
    if not token:
        result.status = "failed"
        result.last_error = "No valid Strava access token"
        return result

    headers = {"Authorization": f"Bearer {token}"}
    after_ts = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp())

    try:
        limiter.pre_request()
        resp = requests.get(
            f"{STRAVA_API}/athlete/activities", headers=headers,
            params={"after": after_ts, "per_page": 100},
        )
        resp.raise_for_status()
        activities = resp.json()
        limiter.post_request(True)
        result.api_calls += 1
    except requests.HTTPError:
        result.status = "failed"
        result.last_error = "Strava activity list fetch failed"
        return result

    result.total_items = len(activities)

    for raw in activities:
        sid = str(raw.get("id", ""))
        try:
            is_new = upsert_raw_payload(conn, "strava", "activity_summary", sid, raw)
            if not is_new:
                result.skipped_count += 1
                continue

            core = extractor.extract_activity_core(raw)
            aid = save_activity_core(conn, core)
            update_raw_activity_id(conn, "strava", "activity_summary", sid, aid)

            # Detail
            detail = _fetch_detail(headers, sid, limiter, result)
            if detail:
                upsert_raw_payload(conn, "strava", "activity_detail", sid, detail, activity_id=aid)
                metrics = extractor.extract_activity_metrics(raw, detail)
                efforts = extractor.extract_best_efforts(detail)
                if efforts:
                    save_best_efforts(conn, aid, efforts)
            else:
                metrics = extractor.extract_activity_metrics(raw)

            if metrics:
                save_metrics(conn, "activity", str(aid), "strava", metrics)

            if include_streams:
                _fetch_and_save_streams(conn, headers, extractor, limiter, result, sid, aid)

            resolve_primaries(conn, "activity", str(aid))
            result.synced_count += 1
            conn.commit()

        except Exception as e:
            if "429" in str(e):
                result.status = "partial"
                conn.commit()
                break
            log.error("[strava] Error for %s: %s", sid, e)
            result.error_count += 1
            result.errors.append((sid, str(e)))
            conn.rollback()

    if result.error_count == 0 and not result.is_rate_limited():
        result.status = "success"
    return result


def _fetch_detail(headers, sid, limiter, result):
    try:
        limiter.pre_request()
        resp = requests.get(f"{STRAVA_API}/activities/{sid}", headers=headers)
        resp.raise_for_status()
        limiter.post_request(True)
        result.api_calls += 1
        return resp.json()
    except Exception as e:
        log.warning("[strava] Detail failed for %s: %s", sid, e)
        return None


def _fetch_and_save_streams(conn, headers, extractor, limiter, result, sid, aid):
    try:
        limiter.pre_request()
        resp = requests.get(
            f"{STRAVA_API}/activities/{sid}/streams", headers=headers,
            params={"keys": STREAM_KEYS, "key_by_type": "true"},
        )
        resp.raise_for_status()
        raw = resp.json()
        limiter.post_request(True)
        result.api_calls += 1
        if raw:
            payload = raw if isinstance(raw, dict) else {"streams": raw}
            upsert_raw_payload(conn, "strava", "activity_streams", sid, payload, activity_id=aid)
            rows = extractor.extract_activity_streams(raw)
            if rows:
                save_streams(conn, aid, rows)
    except Exception as e:
        log.warning("[strava] Streams failed for %s: %s", sid, e)


def _ensure_token(config):
    sc = config.get("strava", {})
    if datetime.now(timezone.utc).timestamp() < sc.get("expires_at", 0) - 600:
        return sc.get("access_token")
    try:
        resp = requests.post("https://www.strava.com/oauth/token", data={
            "client_id": sc.get("client_id"),
            "client_secret": sc.get("client_secret"),
            "refresh_token": sc.get("refresh_token"),
            "grant_type": "refresh_token",
        })
        resp.raise_for_status()
        data = resp.json()
        sc["access_token"] = data["access_token"]
        sc["refresh_token"] = data["refresh_token"]
        sc["expires_at"] = data["expires_at"]
        from src.utils.config import save_config
        save_config(config)
        return data["access_token"]
    except Exception as e:
        log.error("[strava] Token refresh failed: %s", e)
        return None

"""Garmin 활동 동기화 Orchestrator.

책임: API 호출 → raw 저장 → Extractor 호출 → DB 적재 → primary 결정.
비즈니스 로직(필드 매핑)은 GarminExtractor에 위임합니다.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from src.sync.extractors import get_extractor
from src.sync.rate_limiter import RateLimiter
from src.sync.raw_store import upsert_raw_payload, update_raw_activity_id
from src.sync.sync_result import SyncResult
from src.sync._helpers import (
    save_activity_core,
    save_metrics,
    save_laps,
    save_streams,
    resolve_primaries,
)

log = logging.getLogger(__name__)


class _RateLimitStop(Exception):
    """rate-limit으로 전체 sync 중단 시그널."""


def sync(
    conn,
    api,
    days: int = 7,
    include_streams: bool = False,
    *,
    _sleep_fn=None,
) -> SyncResult:
    """Garmin 활동 동기화.

    Args:
        conn: SQLite connection
        api: garminconnect.Garmin 인스턴스 (로그인 완료)
        days: 날짜 범위
        include_streams: 스트림 데이터도 가져올지
        _sleep_fn: 테스트용 sleep 오버라이드
    """
    result = SyncResult(source="garmin", job_type="activity")
    extractor = get_extractor("garmin")
    limiter = RateLimiter("garmin", sleep_fn=_sleep_fn)

    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    # [1] Activity List
    try:
        limiter.pre_request()
        activities_raw = api.get_activities_by_date(
            start_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d"),
        )
        limiter.post_request(success=True)
        result.api_calls += 1
    except Exception as e:
        if _is_rate_limit_error(e):
            result.status = "failed"
            result.last_error = "Rate limited on activity list fetch"
            result.retry_after = _retry_after(limiter)
            return result
        raise

    if not activities_raw:
        log.info("[garmin] No activities found in date range")
        return result

    result.total_items = len(activities_raw)
    log.info("[garmin] Found %d activities to process", len(activities_raw))

    for raw_activity in activities_raw:
        aid_str = str(raw_activity.get("activityId", ""))
        try:
            synced = _sync_single(
                conn, api, extractor, limiter, result,
                raw_activity, include_streams,
            )
            if synced:
                result.synced_count += 1
            else:
                result.skipped_count += 1
            conn.commit()

        except _RateLimitStop:
            log.warning(
                "[garmin] Rate limit reached. Synced %d/%d",
                result.synced_count, result.total_items,
            )
            result.status = "partial"
            result.retry_after = _retry_after(limiter)
            conn.commit()
            break

        except Exception as e:
            log.error("[garmin] Error for activity %s: %s", aid_str, e)
            result.error_count += 1
            result.errors.append((aid_str, str(e)))
            result.last_error = str(e)
            conn.rollback()

    if result.error_count == 0 and not result.is_rate_limited():
        result.status = "success"
    elif result.synced_count > 0:
        result.status = "partial"

    return result


def _sync_single(conn, api, extractor, limiter, result, raw, include_streams) -> bool:
    source_id = str(raw.get("activityId", ""))

    # [2] Raw summary
    is_new = upsert_raw_payload(
        conn, "garmin", "activity_summary", source_id, raw,
        endpoint="activitylist-service/activities/search/activities",
    )
    if not is_new:
        return False

    # [3-4] Core
    core = extractor.extract_activity_core(raw)
    activity_id = save_activity_core(conn, core)

    # [5] 역참조
    update_raw_activity_id(conn, "garmin", "activity_summary", source_id, activity_id)

    # [6-7] Detail
    detail = _fetch_detail(conn, api, limiter, result, source_id, activity_id)

    # [8-9] Metrics
    metrics = extractor.extract_activity_metrics(raw, detail)
    if metrics:
        save_metrics(conn, "activity", str(activity_id), "garmin", metrics)

    # [10-11] Laps
    if detail:
        laps = extractor.extract_activity_laps(detail)
        if laps:
            save_laps(conn, activity_id, laps)

    # [12-15] Streams
    if include_streams and detail:
        _fetch_streams(conn, api, extractor, limiter, result, source_id, activity_id)

    # [16] Primary
    resolve_primaries(conn, "activity", str(activity_id))

    log.info(
        "[garmin] Synced activity %s → id=%d, metrics=%d",
        source_id, activity_id, len(metrics),
    )
    return True


def _fetch_detail(conn, api, limiter, result, source_id, activity_id):
    try:
        limiter.pre_request()
        detail = api.get_activity(int(source_id))
        limiter.post_request(success=True)
        result.api_calls += 1
        if detail:
            upsert_raw_payload(
                conn, "garmin", "activity_detail", source_id, detail,
                endpoint=f"activity-service/activity/{source_id}",
                activity_id=activity_id,
            )
        return detail
    except Exception as e:
        if _is_rate_limit_error(e):
            if not limiter.handle_rate_limit():
                raise _RateLimitStop()
            try:
                limiter.pre_request()
                detail = api.get_activity(int(source_id))
                limiter.post_request(success=True)
                result.api_calls += 1
                return detail
            except Exception:
                return None
        log.warning("[garmin] Detail fetch failed for %s: %s", source_id, e)
        return None



def _fetch_streams(conn, api, extractor, limiter, result, source_id, activity_id):
    try:
        limiter.pre_request()
        streams_raw = api.get_activity_splits(int(source_id))
        limiter.post_request(success=True)
        result.api_calls += 1
        if streams_raw:
            payload = streams_raw if isinstance(streams_raw, dict) else {"data": streams_raw}
            upsert_raw_payload(
                conn, "garmin", "activity_streams", source_id,
                payload, activity_id=activity_id,
            )
            rows = extractor.extract_activity_streams(streams_raw)
            if rows:
                save_streams(conn, activity_id, rows)
    except Exception as e:
        log.warning("[garmin] Streams fetch failed for %s: %s", source_id, e)


def _is_rate_limit_error(e: Exception) -> bool:
    s = str(e).lower()
    if "429" in s or "too many requests" in s or "1015" in s:
        return True
    if "TooManyRequests" in type(e).__name__:
        return True
    return False


def _retry_after(limiter: RateLimiter) -> str:
    wait = limiter.policy.backoff_base * (
        limiter.policy.backoff_multiplier ** limiter._consecutive_429
    )
    at = datetime.utcnow() + timedelta(seconds=wait)
    return at.isoformat() + "Z"

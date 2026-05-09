"""Garmin 활동 동기화 Orchestrator.

책임: API 호출 → raw 저장 → Extractor 호출 → DB 적재 → primary 결정.
비즈니스 로직(필드 매핑)은 GarminExtractor에 위임합니다.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

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
    start_date: str | None = None,
    end_date: str | None = None,
    _sleep_fn=None,
) -> SyncResult:
    """Garmin 활동 동기화.

    Args:
        conn: SQLite connection
        api: garminconnect.Garmin 인스턴스 (로그인 완료)
        days: 날짜 범위 (start_date/end_date 미지정 시 사용)
        include_streams: 스트림 데이터도 가져올지
        start_date: ISO 날짜 문자열 (YYYY-MM-DD), 지정 시 days 무시
        end_date: ISO 날짜 문자열 (YYYY-MM-DD), 지정 시 days 무시
        _sleep_fn: 테스트용 sleep 오버라이드
    """
    result = SyncResult(source="garmin", job_type="activity")
    extractor = get_extractor("garmin")
    limiter = RateLimiter("garmin", sleep_fn=_sleep_fn)

    if start_date and end_date:
        end_dt = datetime.fromisoformat(end_date).replace(tzinfo=timezone.utc)
        start_dt = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
    else:
        end_dt = datetime.now(timezone.utc)
        start_dt = end_dt - timedelta(days=days)

    log.info("[garmin/activity] sync 시작: %s ~ %s", start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d"))

    # [1] Activity List
    try:
        limiter.pre_request()
        activities_raw = api.get_activities_by_date(
            start_dt.strftime("%Y-%m-%d"),
            end_dt.strftime("%Y-%m-%d"),
        )
        limiter.post_request(success=True)
        result.api_calls += 1
        log.info("[garmin/activity] get_activities_by_date 응답: %s건",
                 len(activities_raw) if activities_raw else 0)
    except Exception as e:
        if _is_rate_limit_error(e):
            log.warning("[garmin/activity] 활동 목록 조회 중 429: %s", e)
            result.status = "failed"
            result.last_error = "Rate limited on activity list fetch"
            result.retry_after = _retry_after(limiter)
            return result
        log.error("[garmin/activity] 활동 목록 조회 실패: %s", e, exc_info=True)
        raise

    if not activities_raw:
        log.info("[garmin/activity] 해당 기간 활동 없음")
        return result

    result.total_items = len(activities_raw)
    log.info("[garmin/activity] 처리 대상 %d건 — IDs: %s",
             len(activities_raw),
             [a.get("activityId") for a in activities_raw[:5]])

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
    act_type = raw.get("activityType", {}).get("typeKey", "unknown") if isinstance(raw.get("activityType"), dict) else str(raw.get("activityType", ""))
    log.info("[garmin/activity] 처리: activityId=%s, type=%s", source_id, act_type)

    # [2] Raw summary
    is_new = upsert_raw_payload(
        conn, "garmin", "activity_summary", source_id, raw,
        endpoint="activitylist-service/activities/search/activities",
    )
    log.debug("[garmin/activity] upsert_raw_payload is_new=%s for %s", is_new, source_id)

    # [3-4] Core
    core = extractor.extract_activity_core(raw)
    activity_id = save_activity_core(conn, core)
    log.debug("[garmin/activity] save_activity_core → activity_id=%s", activity_id)

    # [5] 역참조
    update_raw_activity_id(conn, "garmin", "activity_summary", source_id, activity_id)

    # [6-7] Detail — summary가 기존에도 detail이 없으면 재시도
    has_detail = conn.execute(
        "SELECT 1 FROM source_payloads WHERE source='garmin' "
        "AND entity_type='activity_detail' AND entity_id=?",
        (source_id,),
    ).fetchone() is not None
    if not is_new and has_detail:
        log.debug("[garmin/activity] skip (summary+detail 모두 기존): %s", source_id)
        return False  # summary·detail 모두 이미 있음 → skip

    log.info("[garmin/activity] detail 조회: %s (is_new=%s, has_detail=%s)", source_id, is_new, has_detail)
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
                if detail:
                    upsert_raw_payload(
                        conn, "garmin", "activity_detail", source_id, detail,
                        endpoint=f"activity-service/activity/{source_id}",
                        activity_id=activity_id,
                    )
                return detail
            except Exception:
                return None
        log.warning("[garmin] Detail fetch failed for %s: %s", source_id, e)
        return None



def _fetch_streams(conn, api, extractor, limiter, result, source_id, activity_id):
    try:
        limiter.pre_request()
        streams_raw = api.get_activity_details(int(source_id), maxpoly=9999999)
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
    at = datetime.now(timezone.utc) + timedelta(seconds=wait)
    return at.isoformat() + "Z"

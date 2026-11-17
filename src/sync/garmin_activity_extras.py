"""Garmin 활동 부가 엔드포인트(/hrTimeInZones·/weather) 조회·저장·재조립.

detail(`/activity`)에는 심박존·날씨가 없어 별도 호출이 필요하다.
실패해도 활동 동기화는 계속한다(429 만 전체 중단 시그널).
"""

from __future__ import annotations

import json
import logging

from src.sync._helpers import save_metrics
from src.sync.raw_store import upsert_raw_payload

log = logging.getLogger(__name__)

# (payload entity_type, detail 에 합쳐 넣을 키, 라이브러리 메서드, endpoint 접미사)
EXTRAS = (
    ("activity_hr_zones", "hrTimeInZones", "get_activity_hr_in_timezones", "hrTimeInZones"),
    ("activity_weather", "activityWeather", "get_activity_weather", "weather"),
)


class RateLimitStop(Exception):
    """rate-limit 으로 전체 sync 중단 시그널."""


def _is_rate_limit(e: Exception) -> bool:
    s = str(e).lower()
    return "429" in s or "too many requests" in s or "1015" in s


def fetch_activity_extras(conn, api, limiter, result, source_id, activity_id) -> dict:
    """부가 엔드포인트를 호출·저장하고 {detail 키: 응답} 을 돌려준다."""
    out: dict = {}
    for entity, key, method, suffix in EXTRAS:
        try:
            limiter.pre_request()
            data = getattr(api, method)(int(source_id))
            limiter.post_request(success=True)
            result.api_calls += 1
        except Exception as e:
            if _is_rate_limit(e) and not limiter.handle_rate_limit():
                raise RateLimitStop() from e
            log.warning("[garmin] %s fetch failed for %s: %s", entity, source_id, e)
            continue
        if not data:
            continue
        out[key] = data
        upsert_raw_payload(
            conn, "garmin", entity, source_id,
            data if isinstance(data, dict) else {"data": data},
            endpoint=f"activity-service/activity/{source_id}/{suffix}",
            activity_id=activity_id,
        )
    return out


def load_activity_extras(conn, source_id) -> dict:
    """저장된 부가 payload → {detail 키: 응답} (reprocess 용)."""
    out: dict = {}
    for entity, key, _m, _s in EXTRAS:
        row = conn.execute(
            "SELECT payload FROM source_payloads WHERE source='garmin' "
            "AND entity_type=? AND entity_id=?", (entity, str(source_id)),
        ).fetchone()
        if row:
            data = json.loads(row[0])
            out[key] = data["data"] if isinstance(data, dict) and set(data) == {"data"} else data
    return out


def save_detail_metrics(conn, extractor, raw, activity_id, source_id):
    """저장된 detail+부가 payload 로 메트릭만 재계산·저장."""
    row = conn.execute(
        "SELECT payload FROM source_payloads WHERE source='garmin' "
        "AND entity_type='activity_detail' AND entity_id=?", (source_id,),
    ).fetchone()
    detail = {**(json.loads(row[0]) if row else {}), **load_activity_extras(conn, source_id)}
    metrics = extractor.extract_activity_metrics(raw, detail)
    if metrics:
        save_metrics(conn, "activity", str(activity_id), "garmin", metrics)

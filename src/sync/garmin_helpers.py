"""Garmin 동기화 공통 헬퍼."""
from __future__ import annotations

import json
import sqlite3

from src.utils.db_helpers import upsert_metric
from src.utils.raw_payload import store_raw_payload as _store_rp
from src.utils.sync_state import set_retry_after


def _store_raw_payload(
    conn: sqlite3.Connection,
    entity_type: str,
    entity_id: str,
    payload,
    activity_id: int | None = None,
) -> None:
    """Garmin raw payload를 source_payloads에 저장."""
    _store_rp(conn, "garmin", entity_type, entity_id, payload, activity_id=activity_id)


def _upsert_vo2max(conn: sqlite3.Connection, date_str: str, vo2max: float) -> None:
    """Garmin vo2max를 metric_store(scope=daily)에 저장."""
    upsert_metric(conn, "daily", date_str, "vo2max", "garmin",
                  numeric_value=float(vo2max), category="capacity")


def _upsert_daily_detail_metric(
    conn: sqlite3.Connection,
    date_str: str,
    metric_name: str,
    metric_value=None,
    metric_json=None,
) -> None:
    """Upsert a Garmin daily detail metric into metric_store."""
    try:
        # metric_json이 이미 직렬화된 문자열인 경우 역직렬화 후 upsert_metric에 전달
        json_obj = None
        if metric_json is not None:
            if isinstance(metric_json, str):
                json_obj = json.loads(metric_json)
            else:
                json_obj = metric_json
        upsert_metric(
            conn, "daily", date_str, metric_name, "garmin",
            numeric_value=float(metric_value) if metric_value is not None else None,
            json_value=json_obj,
        )
    except (TypeError, ValueError, json.JSONDecodeError):
        pass


def _store_daily_detail_metrics(
    conn: sqlite3.Connection,
    date_str: str,
    numeric_metrics: dict[str, float | int | None],
    json_metrics: dict[str, object] | None = None,
) -> None:
    """Store multiple Garmin daily detail metrics."""
    for metric_name, metric_value in numeric_metrics.items():
        if metric_value is not None:
            _upsert_daily_detail_metric(conn, date_str, metric_name, metric_value=metric_value)

    if json_metrics:
        for metric_name, payload in json_metrics.items():
            if payload is not None:
                _upsert_daily_detail_metric(
                    conn,
                    date_str,
                    metric_name,
                    metric_json=json.dumps(payload, ensure_ascii=False, sort_keys=True),
                )


def _handle_rate_limit(service: str, source_id: str = "") -> None:
    """rate limit 발생 시 공통 처리 — exponential backoff + 메시지 출력.

    이미 대기 중이면 대기 시간을 2배로 증가 (최대 24시간).
    첫 발생 시 15분.
    """
    from src.utils.sync_state import get_retry_after_sec

    current = get_retry_after_sec(service)
    if current and current > 0:
        next_wait = min(current * 2, 86400)  # 2배, 최대 24시간
    else:
        next_wait = 900  # 첫 번째: 15분

    hours = next_wait // 3600
    mins = (next_wait % 3600) // 60
    if hours > 0:
        wait_str = f"{hours}시간 {mins}분" if mins else f"{hours}시간"
    else:
        wait_str = f"{mins}분"

    msg = (
        f"[{service}] ⚠️ API 요청 제한(429). "
        f"{wait_str} 후 재시도합니다."
    )
    if source_id:
        msg += f" (마지막 처리: {source_id})"
    print(msg)
    set_retry_after(service, next_wait)

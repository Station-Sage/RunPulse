"""Reprocess — Raw payload에서 Layer 1/2 재구축. 설계서 4-7 기준.

source_payloads → extractor → activity_summaries + metric_store 재생성
→ recompute_all → resolve_all_primaries
"""
from __future__ import annotations

import json
import logging
import sqlite3

from src.sync.extractors import get_extractor
from src.utils.db_helpers import upsert_activity_summary, upsert_metric
from src.utils.metric_priority import resolve_all_primaries
from src.metrics.engine import recompute_all

log = logging.getLogger(__name__)


def reprocess_from_payloads(conn: sqlite3.Connection, days: int = 9999) -> dict:
    """Layer 0(source_payloads)에서 Layer 1/2를 완전 재구축."""

    # 1. 소스 메트릭 + activity_summaries 삭제 (RunPulse 메트릭도 함께)
    conn.execute(
        "DELETE FROM metric_store WHERE provider NOT LIKE 'runpulse%'"
    )
    conn.execute("DELETE FROM metric_store WHERE provider LIKE 'runpulse%'")
    conn.execute("DELETE FROM activity_summaries")
    conn.commit()
    log.info("reprocess: Layer 1/2 초기화 완료")

    # 2. source_payloads에서 activity 유형 재추출
    rows = conn.execute(
        "SELECT source, entity_type, entity_id, payload FROM source_payloads "
        "WHERE entity_type = 'activity' ORDER BY fetched_at"
    ).fetchall()

    activity_count = 0
    metric_count = 0

    for source, entity_type, entity_id, payload_str in rows:
        try:
            raw = json.loads(payload_str)
            extractor = get_extractor(source)

            # Core → activity_summaries
            core = extractor.extract_activity_core(raw)
            core["source"] = source
            core["source_id"] = entity_id
            aid = upsert_activity_summary(conn, core)
            activity_count += 1

            # Metrics → metric_store
            metrics = extractor.extract_activity_metrics(raw)
            for m in metrics:
                upsert_metric(
                    conn,
                    scope_type="activity",
                    scope_id=aid,
                    metric_name=m.metric_name,
                    provider=m.provider,
                    numeric_value=m.numeric_value,
                    text_value=m.text_value,
                    json_value=m.json_value,
                    category=m.category,
                    raw_name=m.raw_name,
                )
                metric_count += 1

        except Exception:
            log.exception("reprocess 실패: source=%s, entity_id=%s", source, entity_id)

    conn.commit()
    log.info("reprocess: %d activities, %d metrics 재추출", activity_count, metric_count)

    # 3. RunPulse 메트릭 재계산
    results = recompute_all(conn, days=days)

    # 4. Primary 재결정
    resolve_all_primaries(conn)
    conn.commit()

    return {
        "activities_reprocessed": activity_count,
        "metrics_reextracted": metric_count,
        "recompute_results": results,
    }

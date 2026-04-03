"""Raw payload(Layer 0)에서 Layer 1/2 재구축.

API 호출 없이 source_payloads의 JSON만으로
activity_summaries, metric_store, activity_laps, activity_streams,
daily_wellness, daily_fitness를 재생성합니다.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from collections import defaultdict

from src.sync.extractors import get_extractor
from src.sync.dedup import run as run_dedup
from src.sync._helpers import (
    save_activity_core,
    save_metrics,
    save_laps,
    save_streams,
    save_best_efforts,
    save_daily_wellness,
    save_daily_fitness,
    resolve_primaries,
)

log = logging.getLogger(__name__)


def reprocess_all(
    conn: sqlite3.Connection,
    source: str | None = None,
    clear_first: bool = True,
) -> dict:
    """Layer 0 → Layer 1 + Layer 2 전체 재구축.

    Args:
        conn: SQLite connection
        source: 특정 소스만 재처리 (None이면 전체)
        clear_first: True면 Layer 1/2 해당 데이터를 먼저 삭제

    Returns:
        {"activities": int, "metrics": int, "wellness": int, "errors": int}
    """
    stats = {"activities": 0, "metrics": 0, "wellness": 0, "errors": 0}

    log.info("Starting reprocess: source=%s, clear_first=%s", source or "all", clear_first)

    if clear_first:
        _clear_derived_data(conn, source)

    # ── 1. Activity summaries 재구축 ──
    activity_id_map = _reprocess_activity_summaries(conn, source, stats)
    conn.commit()

    # ── 2. Activity detail → metrics, laps ──
    _reprocess_activity_details(conn, source, activity_id_map, stats)
    conn.commit()

    # ── 3. Activity streams ──
    _reprocess_activity_streams(conn, source, stats)
    conn.commit()

    # ── 4. Best efforts (Strava) ──
    _reprocess_best_efforts(conn, source, activity_id_map, stats)
    conn.commit()

    # ── 5. Wellness ──
    _reprocess_wellness(conn, source, stats)
    conn.commit()

    # ── 6. Dedup ──
    try:
        run_dedup(conn)
    except Exception as e:
        log.error("Dedup failed: %s", e)

    log.info(
        "Reprocess complete: activities=%d, metrics=%d, wellness=%d, errors=%d",
        stats["activities"], stats["metrics"], stats["wellness"], stats["errors"],
    )
    return stats


def _clear_derived_data(conn: sqlite3.Connection, source: str | None):
    """Layer 1/2 데이터 삭제 (source_payloads는 유지)."""
    if source:
        conn.execute("DELETE FROM activity_summaries WHERE source = ?", (source,))
        conn.execute("DELETE FROM metric_store WHERE provider = ?", (source,))
        # laps/streams는 activity_id 기준이라 cascade 안 되므로 별도 처리
        aids = [r[0] for r in conn.execute(
            "SELECT id FROM activity_summaries WHERE source = ?", (source,)
        ).fetchall()]
        if aids:
            ph = ",".join("?" * len(aids))
            conn.execute(f"DELETE FROM activity_laps WHERE activity_id IN ({ph})", aids)
            conn.execute(f"DELETE FROM activity_streams WHERE activity_id IN ({ph})", aids)
            conn.execute(f"DELETE FROM activity_best_efforts WHERE activity_id IN ({ph})", aids)
    else:
        conn.execute("DELETE FROM activity_summaries")
        conn.execute("DELETE FROM metric_store")
        conn.execute("DELETE FROM activity_laps")
        conn.execute("DELETE FROM activity_streams")
        conn.execute("DELETE FROM activity_best_efforts")
        conn.execute("DELETE FROM daily_wellness")
        conn.execute("DELETE FROM daily_fitness")
    conn.commit()
    log.info("Cleared derived data for source=%s", source or "all")


def _reprocess_activity_summaries(conn, source, stats) -> dict:
    """activity_summary payloads → activity_summaries."""
    query = (
        "SELECT id, source, entity_id, payload "
        "FROM source_payloads WHERE entity_type = 'activity_summary'"
    )
    params = []
    if source:
        query += " AND source = ?"
        params.append(source)
    query += " ORDER BY source, entity_id"

    activity_id_map: dict[tuple[str, str], int] = {}

    for sp_id, src, eid, payload_json in conn.execute(query, params).fetchall():
        try:
            raw = json.loads(payload_json)
            extractor = get_extractor(src)
            core = extractor.extract_activity_core(raw)
            activity_id = save_activity_core(conn, core)
            activity_id_map[(src, eid)] = activity_id

            conn.execute(
                "UPDATE source_payloads SET activity_id = ? WHERE id = ?",
                (activity_id, sp_id),
            )
            stats["activities"] += 1
        except Exception as e:
            log.error("Reprocess summary %s/%s: %s", src, eid, e)
            stats["errors"] += 1

    return activity_id_map


def _reprocess_activity_details(conn, source, activity_id_map, stats):
    """activity_detail payloads → metrics, laps."""
    query = (
        "SELECT id, source, entity_id, payload, activity_id "
        "FROM source_payloads WHERE entity_type = 'activity_detail'"
    )
    params = []
    if source:
        query += " AND source = ?"
        params.append(source)

    for sp_id, src, eid, payload_json, existing_aid in conn.execute(query, params).fetchall():
        try:
            detail = json.loads(payload_json)
            extractor = get_extractor(src)
            activity_id = existing_aid or activity_id_map.get((src, eid))
            if not activity_id:
                continue

            # summary raw도 필요
            summary_row = conn.execute(
                "SELECT payload FROM source_payloads "
                "WHERE source = ? AND entity_type = 'activity_summary' AND entity_id = ?",
                (src, eid),
            ).fetchone()
            summary_raw = json.loads(summary_row[0]) if summary_row else {}

            metrics = extractor.extract_activity_metrics(summary_raw, detail)
            if metrics:
                count = save_metrics(conn, "activity", str(activity_id), src, metrics)
                stats["metrics"] += count

            laps = extractor.extract_activity_laps(detail)
            if laps:
                save_laps(conn, activity_id, laps)

            resolve_primaries(conn, "activity", str(activity_id))

        except Exception as e:
            log.error("Reprocess detail %s/%s: %s", src, eid, e)
            stats["errors"] += 1


def _reprocess_activity_streams(conn, source, stats):
    """activity_streams payloads → activity_streams 테이블."""
    query = (
        "SELECT source, entity_id, payload, activity_id "
        "FROM source_payloads "
        "WHERE entity_type = 'activity_streams' AND activity_id IS NOT NULL"
    )
    params = []
    if source:
        query += " AND source = ?"
        params.append(source)

    for src, eid, payload_json, activity_id in conn.execute(query, params).fetchall():
        try:
            raw = json.loads(payload_json)
            extractor = get_extractor(src)
            rows = extractor.extract_activity_streams(raw)
            if rows:
                save_streams(conn, activity_id, rows)
        except Exception as e:
            log.error("Reprocess streams %s/%s: %s", src, eid, e)
            stats["errors"] += 1


def _reprocess_best_efforts(conn, source, activity_id_map, stats):
    """Strava best_efforts 등 — detail에서 재추출."""
    query = (
        "SELECT source, entity_id, payload, activity_id "
        "FROM source_payloads "
        "WHERE entity_type = 'activity_detail'"
    )
    params = []
    if source:
        query += " AND source = ?"
        params.append(source)

    for src, eid, payload_json, existing_aid in conn.execute(query, params).fetchall():
        try:
            detail = json.loads(payload_json)
            extractor = get_extractor(src)
            activity_id = existing_aid or activity_id_map.get((src, eid))
            if not activity_id:
                continue

            efforts = extractor.extract_best_efforts(detail)
            if efforts:
                save_best_efforts(conn, activity_id, efforts)
        except Exception as e:
            log.error("Reprocess best_efforts %s/%s: %s", src, eid, e)
            stats["errors"] += 1


def _reprocess_wellness(conn, source, stats):
    """Wellness payloads → daily_wellness + metric_store + daily_fitness."""
    wellness_types = (
        "sleep_day", "hrv_day", "body_battery_day", "stress_day",
        "user_summary_day", "training_readiness", "wellness_day", "wellness",
    )
    placeholders = ",".join("?" * len(wellness_types))
    query = (
        f"SELECT source, entity_type, entity_date, payload "
        f"FROM source_payloads WHERE entity_type IN ({placeholders})"
    )
    params: list = list(wellness_types)

    if source:
        query += " AND source = ?"
        params.append(source)

    query += " ORDER BY entity_date, source"

    # (source, date) → {entity_type: payload}
    day_payloads: dict[tuple[str, str], dict] = defaultdict(dict)

    for src, etype, edate, payload_json in conn.execute(query, params).fetchall():
        if edate:
            day_payloads[(src, edate)][etype] = json.loads(payload_json)

    for (src, date_str), payloads in day_payloads.items():
        try:
            extractor = get_extractor(src)

            core = extractor.extract_wellness_core(date_str, **payloads)
            if core:
                save_daily_wellness(conn, date_str, core)
                stats["wellness"] += 1

            metrics = extractor.extract_wellness_metrics(date_str, **payloads)
            if metrics:
                save_metrics(conn, "daily", date_str, src, metrics)
                stats["metrics"] += len(metrics)

            # fitness 추출 시도
            for p in payloads.values():
                fitness = extractor.extract_fitness(date_str, p)
                if fitness and (fitness.get("vo2max") is not None or fitness.get("ctl") is not None):
                    save_daily_fitness(conn, date_str, src, fitness)
                    break

            resolve_primaries(conn, "daily", date_str)

        except Exception as e:
            log.error("Reprocess wellness %s/%s: %s", src, date_str, e)
            stats["errors"] += 1

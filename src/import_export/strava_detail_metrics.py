"""Strava CSV 상세 지표(detail metrics) 저장·백필 — strava_csv 에서 분리 (300줄 규칙)."""
from __future__ import annotations

import sqlite3
from typing import Any

from src.utils.db_helpers import upsert_metric

_DETAIL_METRIC_KEYS: list[tuple[str, str]] = [
    # (metric_name, parsed_key)
    ("relative_effort",              "relative_effort"),
    ("training_load_csv",            "training_load"),
    ("intensity_csv",                "intensity"),
    ("moving_time_sec",              "moving_time_sec"),
    ("elapsed_time_sec",             "elapsed_time_sec"),
    ("max_speed_mps",                "max_speed"),
    ("elevation_loss",               "elevation_loss"),
    ("elevation_low",                "elevation_low"),
    ("elevation_high",               "elevation_high"),
    ("avg_grade",                    "avg_grade"),
    ("grade_adjusted_distance_m",    "grade_adjusted_distance_m"),
    ("avg_grade_adjusted_pace",      "avg_grade_adjusted_pace_sec_km"),
    ("total_work_joules",            "total_work_joules"),
    ("total_steps",                  "total_steps"),
    ("avg_temp_c",                   "avg_temp_c"),
    ("weather_temp_c",               "weather_temp_c"),
    ("weather_humidity",             "weather_humidity"),
    ("wind_speed_ms",                "wind_speed_ms"),
    ("wind_gust_ms",                 "wind_gust_ms"),
    ("uv_index",                     "uv_index"),
    ("cloud_cover",                  "cloud_cover"),
]


def _upsert_strava_detail_metrics(
    conn: sqlite3.Connection, activity_id: int, parsed: dict[str, Any]
) -> None:
    """CSV 파싱 데이터 → metric_store UPSERT.

    ON CONFLICT DO UPDATE로 최신 CSV값으로 갱신한다.
    best_efforts, stream_file 등 API 전용 metrics는 건드리지 않는다.
    """
    for metric_name, parsed_key in _DETAIL_METRIC_KEYS:
        val = parsed.get(parsed_key)
        if val is None:
            continue
        upsert_metric(conn, "activity", str(activity_id), metric_name, "strava",
                      numeric_value=float(val))


def backfill_strava_detail_metrics(
    conn: sqlite3.Connection,
    activities_csv: Path | None = None,
) -> dict[str, int]:
    """activity_detail_metrics를 역채움.

    activities_csv가 주어지면 CSV를 직접 파싱한다 (training_load 등 신규 필드 포함).
    없으면 raw_source_payloads(csv_export)에서 읽는다.

    Returns:
        {"processed": n, "skipped": n, "inserted_activities": n}
    """
    stats: dict[str, int] = {"processed": 0, "skipped": 0, "inserted_activities": 0}

    if activities_csv is not None and activities_csv.exists():
        with open(activities_csv, encoding="utf-8") as f:
            raw_rows = list(csv.DictReader(f))
        source_data: list[tuple[int, dict]] = []
        for raw in raw_rows:
            try:
                parsed = _parse_activity_row(raw)
            except Exception:
                stats["skipped"] += 1
                continue
            source_id = parsed.get("source_id", "").strip()
            if not source_id:
                continue
            row = conn.execute(
                "SELECT id FROM activity_summaries WHERE source = 'strava' AND source_id = ?",
                (source_id,),
            ).fetchone()
            if row:
                source_data.append((row[0], parsed))
            else:
                stats["skipped"] += 1
    else:
        payload_rows = conn.execute(
            "SELECT a.id, p.payload "
            "FROM activity_summaries a "
            "JOIN source_payloads p ON p.activity_id = a.id "
            "WHERE a.source = 'strava' AND p.entity_type = 'csv_export'",
        ).fetchall()
        source_data = []
        for activity_id, payload_json in payload_rows:
            try:
                source_data.append((activity_id, json.loads(payload_json)))
            except Exception:
                stats["skipped"] += 1

    for activity_id, parsed in source_data:
        before = conn.execute(
            "SELECT COUNT(*) FROM metric_store WHERE scope_type='activity' AND scope_id=? AND provider='strava'",
            (str(activity_id),),
        ).fetchone()[0]
        _upsert_strava_detail_metrics(conn, activity_id, parsed)
        after = conn.execute(
            "SELECT COUNT(*) FROM metric_store WHERE scope_type='activity' AND scope_id=? AND provider='strava'",
            (str(activity_id),),
        ).fetchone()[0]
        if after > before:
            stats["inserted_activities"] += 1
        stats["processed"] += 1

    conn.commit()
    return stats



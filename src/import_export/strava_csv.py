"""Strava export CSV → DB 임포트.

Strava > 내 계정 데이터 내보내기에서 얻은 파일을 파싱:
- activities.csv : 활동 메타데이터 + 파일명
- shoes.csv      : 신발 목록

activities/ 폴더의 GPX/FIT/TCX 파일은 별도 처리 (향후 확장).
"""
from __future__ import annotations

import csv
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from src.import_export.strava_detail_metrics import (  # noqa: F401  (재노출)
    _upsert_strava_detail_metrics,
    backfill_strava_detail_metrics,
)
from src.import_export.strava_tz_apply import TzContext, apply_to_existing, tz_payload_fields
from src.utils.dedup import assign_group_id
from src.utils.raw_payload import update_changed_fields

from src.import_export.strava_row import (  # noqa: F401  (재노출)
    _LOCAL_UTC_OFFSET, _TYPE_MAP, _clean, _float, _int, _parse_activity_row,
    _parse_strava_date, _speed_to_pace,
)

# ── 활동 임포트 ──────────────────────────────────────────────────────────

def import_strava_activities(
    conn: sqlite3.Connection,
    activities_csv: Path,
    config: dict | None = None,
) -> dict[str, Any]:
    """activities.csv → activity_summaries 적재 (start_time 은 시간대 체인으로 결정, 네트워크 호출 없음).

    Returns:
        {"inserted", "skipped", "errors", + TzContext.summary()}
    """
    inserted = skipped = errors = 0
    tz = TzContext(conn, config)

    with open(activities_csv, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    for raw in rows:
        try:
            parsed = _parse_activity_row(raw)
        except Exception as e:
            print(f"[strava_csv] 파싱 오류: {e}")
            errors += 1
            continue

        source_id = parsed["source_id"]
        if not source_id or not parsed["start_time"]:
            errors += 1
            continue

        utc = datetime.fromisoformat(parsed["start_date_utc"]) if parsed.get("start_date_utc") else None
        tz_source, peer = "fallback", None
        if utc is not None:
            parsed["start_time"], tz_source, peer = tz.resolve(
                source_id, utc, (parsed["distance_km"] or 0) * 1000)
        parsed.update(tz_payload_fields(utc, tz_source, peer))

        try:
            cursor = conn.execute(
                """INSERT OR IGNORE INTO activity_summaries
                   (source, source_id, activity_type, start_time,
                    distance_m, duration_sec, avg_pace_sec_km,
                    avg_hr, max_hr, avg_cadence, elevation_gain,
                    description, avg_power)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    "strava", source_id,
                    parsed["activity_type"],
                    parsed["start_time"],
                    (parsed["distance_km"] or 0) * 1000,
                    parsed["duration_sec"],
                    parsed["avg_pace_sec_km"],
                    parsed["avg_hr"],
                    parsed["max_hr"],
                    parsed["avg_cadence"],
                    parsed["elevation_gain"],
                    parsed["description"],
                    parsed["avg_power"],
                ),
            )
        except sqlite3.Error as e:
            print(f"[strava_csv] DB 삽입 오류 (source_id={source_id}): {e}")
            errors += 1
            continue

        if cursor.rowcount == 0:
            # 이미 존재 — 변경/누락 필드 업데이트 + detail metrics 갱신
            existing_id = update_changed_fields(conn, "strava", source_id, {
                "distance_m": (d * 1000 if (d := parsed.get("distance_km")) else None),
                "duration_sec": parsed.get("duration_sec"),
                "avg_pace_sec_km": parsed.get("avg_pace_sec_km"),
                "avg_hr": parsed.get("avg_hr"),
                "max_hr": parsed.get("max_hr"),
                "avg_cadence": parsed.get("avg_cadence"),
                "elevation_gain": parsed.get("elevation_gain"),
                "avg_power": parsed.get("avg_power"),
            })
            if existing_id:
                if utc is not None:
                    apply_to_existing(conn, source_id, parsed["start_time"], tz_source, peer)
                _upsert_strava_detail_metrics(conn, existing_id, parsed)
            skipped += 1
            continue

        activity_id = cursor.lastrowid
        inserted += 1

        # raw payload 저장
        payload = {k: v for k, v in parsed.items() if v is not None}
        try:
            conn.execute(
                """INSERT OR REPLACE INTO source_payloads
                   (source, entity_type, entity_id, activity_id, payload)
                   VALUES ('strava', 'csv_export', ?, ?, ?)""",
                (source_id, activity_id, json.dumps(payload, ensure_ascii=False)),
            )
        except sqlite3.Error:
            pass

        _upsert_strava_detail_metrics(conn, activity_id, parsed)
        assign_group_id(conn, activity_id)

    conn.commit()
    if tz.counts:
        print(tz.log_line())
    return {"inserted": inserted, "skipped": skipped, "errors": errors, **tz.summary()}


# ── 통합 임포트 ──────────────────────────────────────────────────────────

def import_strava_folder(
    conn: sqlite3.Connection,
    folder: Path,
    config: dict | None = None,
) -> dict[str, Any]:
    """Strava export 폴더에서 activities.csv + shoes.csv 임포트.

    Args:
        folder: strava export 루트 폴더 (activities.csv, shoes.csv가 있는 곳)
    """
    from src.import_export.strava_shoes import import_strava_shoes

    result: dict[str, Any] = {}

    activities_csv = folder / "activities.csv"
    if activities_csv.exists():
        r = import_strava_activities(conn, activities_csv, config)
        result["activities"] = r
        print(
            f"[strava_csv] activities.csv: "
            f"+{r['inserted']} 신규, {r['skipped']} 중복, {r['errors']} 오류"
        )
    else:
        result["activities"] = {"error": "activities.csv 없음"}

    shoes_csv = folder / "shoes.csv"
    if shoes_csv.exists():
        r = import_strava_shoes(conn, shoes_csv)
        result["shoes"] = r
        print(f"[strava_csv] shoes.csv: +{r['inserted']} 신규, {r['skipped']} 중복")
    else:
        result["shoes"] = {"error": "shoes.csv 없음"}

    return result

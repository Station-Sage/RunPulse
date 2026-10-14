"""Strava full-archive import + backfill.

Strava > 내 계정 > 데이터 내보내기 ZIP 내부 구조:
    activities.csv
    activities/
        12345678901234.fit.gz
        12345678901234.tcx.gz
        12345678901234.gpx.gz
        12345678901234.fit
        ...

import_strava_archive(): CSV + 파일 통합 임포트 (신규 row 삽입)
backfill_strava_archive(): 기존 CSV-only row에 파일 파싱 정밀값 강제 덮어쓰기

source_id = CSV의 Activity ID (항상, 파일명 숫자 사용 금지)
"""
from __future__ import annotations

import csv
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from src.import_export.strava_archive_backfill import (  # noqa: F401  (재노출)
    _backfill_file_data, backfill_strava_archive, find_activity_file,
)
from src.import_export.strava_csv import _parse_activity_row, _upsert_strava_detail_metrics
from src.import_export.strava_tz_apply import TzContext, apply_to_existing, tz_payload_fields
from src.import_history import parse_file_data
from src.utils.dedup import assign_group_id
from src.utils.raw_payload import update_changed_fields


def _merge(csv_meta: dict[str, Any], file_data: dict[str, Any] | None) -> dict[str, Any]:
    """CSV 메타 + 파일 파싱 데이터 병합.

    우선순위:
    - start_time, activity_type, description, calories, avg_power: CSV 우선
    - distance_km, duration_sec, avg_hr, max_hr, avg_cadence, elevation_gain:
      파일 데이터 우선 (GPS/센서 정밀값), CSV는 fallback
    - avg_pace_sec_km: 병합 후 재계산
    """
    merged: dict[str, Any] = dict(csv_meta)
    if not file_data:
        return merged

    for key in ("distance_km", "duration_sec", "avg_hr", "max_hr",
                "avg_cadence", "elevation_gain"):
        if file_data.get(key) is not None:
            merged[key] = file_data[key]

    # activity_type: CSV에 값 없으면 TCX/파일값 사용
    if not merged.get("activity_type") and file_data.get("activity_type"):
        merged["activity_type"] = file_data["activity_type"]

    # 페이스 재계산 (파일 데이터로 거리/시간이 갱신됐을 수 있음)
    dist = merged.get("distance_km")
    dur = merged.get("duration_sec")
    if dist and dur and dist > 0:
        merged["avg_pace_sec_km"] = int(dur / dist)

    return merged


def import_strava_archive(
    conn: sqlite3.Connection,
    folder: Path,
    config: dict | None = None,
) -> dict[str, int]:
    """Strava archive 폴더 → activity_summaries 적재 (start_time 은 시간대 체인, 네트워크 호출 없음).

    Args:
        conn:   SQLite 연결 (commit은 이 함수 내에서 수행)
        folder: Strava archive 루트 폴더 (activities.csv가 있는 위치)

    Returns:
        {
          "csv_total":   CSV에서 읽은 전체 행 수,
          "inserted":    신규 삽입 수,
          "skipped":     source_id 중복으로 건너뜀,
          "file_linked": 파일 파싱 성공 후 병합된 수,
          "csv_only":    파일 없음/파싱 실패로 CSV-only fallback 생성 수,
          "gz_ok":       .gz 압축 해제 성공 수,
          "errors":      처리 불가 오류 수,
          + TzContext.summary() (tz_resolved, tz_lookup_status, tz_peer_conflicts, tz_backfill_pending)
        }
    """
    activities_csv = folder / "activities.csv"
    if not activities_csv.exists():
        print(f"[strava_archive] activities.csv 없음: {activities_csv}")
        return {
            "csv_total": 0, "inserted": 0, "skipped": 0,
            "file_linked": 0, "csv_only": 0, "gz_ok": 0, "errors": 1,
        }

    activities_dir = folder / "activities"
    stats: dict[str, Any] = {
        "csv_total": 0, "inserted": 0, "skipped": 0,
        "file_linked": 0, "csv_only": 0, "gz_ok": 0, "errors": 0,
    }
    tz = TzContext(conn, config)

    with open(activities_csv, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    stats["csv_total"] = len(rows)

    for raw in rows:
        # ── 1. CSV 파싱 ────────────────────────────────────────────────
        try:
            csv_meta = _parse_activity_row(raw)
        except Exception as e:
            print(f"[strava_archive] CSV 파싱 오류: {e}")
            stats["errors"] += 1
            continue

        source_id = csv_meta.get("source_id", "").strip()
        if not source_id or not csv_meta.get("start_time"):
            stats["errors"] += 1
            continue

        # ── 2. 원본 파일 탐색 ──────────────────────────────────────────
        file_path = find_activity_file(activities_dir, csv_meta.get("filename"))
        file_data: dict[str, Any] | None = None
        is_gz = False

        if file_path is not None:
            is_gz = file_path.suffix.lower() == ".gz"
            file_data = parse_file_data(file_path)
            if file_data is None:
                print(f"[strava_archive] 파일 파싱 실패: {file_path.name}")
            elif is_gz:
                stats["gz_ok"] += 1

        # ── 3. 병합 ────────────────────────────────────────────────────
        merged = _merge(csv_meta, file_data)
        is_file_linked = file_data is not None
        utc = datetime.fromisoformat(csv_meta["start_date_utc"]) if csv_meta.get("start_date_utc") else None
        tz_source, peer = "fallback", None
        if utc is not None:
            merged["start_time"], tz_source, peer = tz.resolve(
                source_id, utc, (merged.get("distance_km") or 0) * 1000,
                fit_local=(file_data or {}).get("fit_local"))
        merged.update(tz_payload_fields(utc, tz_source, peer))

        # ── 4. DB 삽입 ─────────────────────────────────────────────────
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
                    merged.get("activity_type") or "running",
                    merged["start_time"],
                    (merged.get("distance_km") or 0) * 1000,
                    merged.get("duration_sec"),
                    merged.get("avg_pace_sec_km"),
                    merged.get("avg_hr"),
                    merged.get("max_hr"),
                    merged.get("avg_cadence"),
                    merged.get("elevation_gain"),
                    merged.get("description"),
                    merged.get("avg_power"),
                ),
            )
        except sqlite3.Error as e:
            print(f"[strava_archive] DB 삽입 오류 (source_id={source_id}): {e}")
            stats["errors"] += 1
            continue

        if cursor.rowcount == 0:
            # 이미 존재 — 변경/누락 필드 업데이트 + detail metrics 갱신
            existing_id = update_changed_fields(conn, "strava", source_id, {
                "distance_m": (d * 1000 if (d := merged.get("distance_km")) else None),
                "duration_sec": merged.get("duration_sec"),
                "avg_pace_sec_km": merged.get("avg_pace_sec_km"),
                "avg_hr": merged.get("avg_hr"),
                "max_hr": merged.get("max_hr"),
                "avg_cadence": merged.get("avg_cadence"),
                "elevation_gain": merged.get("elevation_gain"),
                "avg_power": merged.get("avg_power"),
            })
            if existing_id:
                if utc is not None:
                    apply_to_existing(conn, source_id, merged["start_time"], tz_source, peer)
                _upsert_strava_detail_metrics(conn, existing_id, csv_meta)
            stats["skipped"] += 1
            continue

        activity_id = cursor.lastrowid
        stats["inserted"] += 1
        if is_file_linked:
            stats["file_linked"] += 1
        else:
            stats["csv_only"] += 1

        # ── 5. detail metrics 저장 ─────────────────────────────────────
        _upsert_strava_detail_metrics(conn, activity_id, csv_meta)

        # ── 6. raw payload 저장 ────────────────────────────────────────
        payload = {k: v for k, v in merged.items() if v is not None}
        try:
            conn.execute(
                """INSERT OR REPLACE INTO source_payloads
                   (source, entity_type, entity_id, activity_id, payload)
                   VALUES ('strava', 'archive_import', ?, ?, ?)""",
                (source_id, activity_id, json.dumps(payload, ensure_ascii=False)),
            )
        except sqlite3.Error:
            pass  # raw payload 실패는 무시

        assign_group_id(conn, activity_id)

    conn.commit()
    if tz.counts:
        print(tz.log_line())
    stats.update(tz.summary())
    return stats

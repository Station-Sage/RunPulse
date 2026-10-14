"""Strava archive 백필 — 기존 strava row 에 파일 파싱 정밀값을 강제 덮어쓴다.

`strava_archive` 에서 분리 (300줄 상한). `strava_archive` 가 재노출한다.
"""
from __future__ import annotations

import csv
import sqlite3
from pathlib import Path
from typing import Any

from src.import_export.strava_row import _parse_activity_row
from src.import_history import parse_file_data


def find_activity_file(activities_dir: Path, filename: str | None) -> Path | None:
    """CSV Filename 컬럼값으로 activities/ 폴더에서 파일을 탐색한다.

    Strava CSV의 Filename 컬럼 예시: "activities/12345678901234.fit.gz"
    activities/ 폴더가 없거나 파일이 없으면 None 반환.
    """
    if not filename:
        return None
    # "activities/12345678.fit.gz" → "12345678.fit.gz"
    bare = Path(filename).name
    if not bare:
        return None
    candidate = activities_dir / bare
    return candidate if candidate.exists() else None


def _backfill_file_data(
    conn: sqlite3.Connection,
    source_id: str,
    file_data: dict[str, Any],
) -> bool:
    """기존 strava row에 파일 파싱 정밀값을 강제 덮어쓴다.

    fill_null_columns()과 달리 COALESCE 없이 파일값으로 직접 UPDATE한다.
    대상 필드: distance_km, duration_sec, avg_hr, max_hr, avg_cadence,
              elevation_gain, avg_pace_sec_km (재계산).

    CSV 우선 필드(activity_type, description, start_time, calories, avg_power)는
    건드리지 않는다.

    Returns:
        True if row found and updated, False if not found in DB.
    """
    fields = {
        "distance_km":   file_data.get("distance_km"),
        "duration_sec":  file_data.get("duration_sec"),
        "avg_hr":        file_data.get("avg_hr"),
        "max_hr":        file_data.get("max_hr"),
        "avg_cadence":   file_data.get("avg_cadence"),
        "elevation_gain": file_data.get("elevation_gain"),
    }
    non_null = {k: v for k, v in fields.items() if v is not None}
    if not non_null:
        return False

    # 거리·시간으로 페이스 재계산
    dist = non_null.get("distance_km")
    dur = non_null.get("duration_sec")
    if dist and dur and dist > 0:
        non_null["avg_pace_sec_km"] = int(dur / dist)

    if "distance_km" in non_null:
        non_null["distance_m"] = non_null.pop("distance_km") * 1000
    set_clause = ", ".join(f"{col} = ?" for col in non_null)
    result = conn.execute(
        f"UPDATE activity_summaries SET {set_clause} "
        f"WHERE source = 'strava' AND source_id = ?",
        (*non_null.values(), source_id),
    )
    return result.rowcount > 0


def backfill_strava_archive(
    conn: sqlite3.Connection,
    folder: Path,
) -> dict[str, int]:
    """이미 임포트된 strava row에 파일 파싱 정밀값을 백필한다.

    INSERT 없이 UPDATE만 수행한다. 파일 없는 row는 건너뛴다.

    Args:
        conn:   SQLite 연결
        folder: Strava archive 루트 폴더 (activities.csv가 있는 위치)

    Returns:
        {
          "csv_total":          CSV 전체 행 수,
          "updated":            파일 파싱 성공 + UPDATE된 수,
          "skipped_no_file":    activities/ 파일 없음,
          "skipped_parse_fail": 파일 파싱 실패,
          "skipped_not_in_db":  source_id가 DB에 없음,
          "gz_ok":              gz 압축 해제 성공 수,
          "errors":             CSV 파싱 오류 수,
        }
    """
    activities_csv = folder / "activities.csv"
    if not activities_csv.exists():
        print(f"[strava_archive] activities.csv 없음: {activities_csv}")
        return {
            "csv_total": 0, "updated": 0, "skipped_no_file": 0,
            "skipped_parse_fail": 0, "skipped_not_in_db": 0,
            "gz_ok": 0, "errors": 1,
        }

    activities_dir = folder / "activities"
    stats: dict[str, int] = {
        "csv_total": 0, "updated": 0, "skipped_no_file": 0,
        "skipped_parse_fail": 0, "skipped_not_in_db": 0,
        "gz_ok": 0, "errors": 0,
    }

    with open(activities_csv, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    stats["csv_total"] = len(rows)

    for raw in rows:
        try:
            csv_meta = _parse_activity_row(raw)
        except Exception as e:
            print(f"[strava_archive] CSV 파싱 오류: {e}")
            stats["errors"] += 1
            continue

        source_id = csv_meta.get("source_id", "").strip()
        if not source_id:
            stats["errors"] += 1
            continue

        # 파일 탐색
        file_path = find_activity_file(activities_dir, csv_meta.get("filename"))
        if file_path is None:
            stats["skipped_no_file"] += 1
            continue

        is_gz = file_path.suffix.lower() == ".gz"
        file_data = parse_file_data(file_path)
        if file_data is None:
            stats["skipped_parse_fail"] += 1
            continue
        if is_gz:
            stats["gz_ok"] += 1

        # 기존 row 강제 업데이트
        if _backfill_file_data(conn, source_id, file_data):
            stats["updated"] += 1
        else:
            stats["skipped_not_in_db"] += 1

    conn.commit()
    return stats

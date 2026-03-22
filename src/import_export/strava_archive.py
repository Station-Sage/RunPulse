"""Strava full-archive import.

Strava > 내 계정 > 데이터 내보내기 ZIP 내부 구조:
    activities.csv
    activities/
        12345678901234.fit.gz
        12345678901234.tcx.gz
        12345678901234.gpx.gz
        12345678901234.fit
        ...

임포트 순서:
1. activities.csv 파싱 → Activity ID, 메타데이터, Filename 컬럼 수집
2. Filename으로 activities/ 폴더에서 원본 파일 탐색
3. 파일 파싱 성공 → 파일 데이터(정밀) + CSV 메타 병합
4. 파일 없음 / 파싱 실패 → CSV-only fallback row 생성
5. source_id = CSV의 Activity ID (항상, 파일명 숫자 사용 금지)
"""
from __future__ import annotations

import csv
import json
import sqlite3
from pathlib import Path
from typing import Any

from src.import_export.strava_csv import _parse_activity_row
from src.import_history import parse_file_data
from src.utils.dedup import assign_group_id


def _find_activity_file(activities_dir: Path, filename: str | None) -> Path | None:
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
) -> dict[str, int]:
    """Strava archive 폴더 → activity_summaries 적재.

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
    stats: dict[str, int] = {
        "csv_total": 0, "inserted": 0, "skipped": 0,
        "file_linked": 0, "csv_only": 0, "gz_ok": 0, "errors": 0,
    }

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
        file_path = _find_activity_file(activities_dir, csv_meta.get("filename"))
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

        # ── 4. DB 삽입 ─────────────────────────────────────────────────
        try:
            cursor = conn.execute(
                """INSERT OR IGNORE INTO activity_summaries
                   (source, source_id, activity_type, start_time,
                    distance_km, duration_sec, avg_pace_sec_km,
                    avg_hr, max_hr, avg_cadence, elevation_gain,
                    calories, description, avg_power, export_filename)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    "strava", source_id,
                    merged.get("activity_type") or "running",
                    merged["start_time"],
                    merged.get("distance_km"),
                    merged.get("duration_sec"),
                    merged.get("avg_pace_sec_km"),
                    merged.get("avg_hr"),
                    merged.get("max_hr"),
                    merged.get("avg_cadence"),
                    merged.get("elevation_gain"),
                    merged.get("calories"),
                    merged.get("description"),
                    merged.get("avg_power"),
                    csv_meta.get("filename"),
                ),
            )
        except sqlite3.Error as e:
            print(f"[strava_archive] DB 삽입 오류 (source_id={source_id}): {e}")
            stats["errors"] += 1
            continue

        if cursor.rowcount == 0:
            stats["skipped"] += 1
            continue

        activity_id = cursor.lastrowid
        stats["inserted"] += 1
        if is_file_linked:
            stats["file_linked"] += 1
        else:
            stats["csv_only"] += 1

        # ── 5. raw payload 저장 ────────────────────────────────────────
        payload = {k: v for k, v in merged.items() if v is not None}
        try:
            conn.execute(
                """INSERT OR REPLACE INTO raw_source_payloads
                   (source, entity_type, entity_id, activity_id, payload_json,
                    created_at, updated_at)
                   VALUES ('strava', 'archive_import', ?, ?, ?,
                           datetime('now'), datetime('now'))""",
                (source_id, activity_id, json.dumps(payload, ensure_ascii=False)),
            )
        except sqlite3.Error:
            pass  # raw payload 실패는 무시

        assign_group_id(conn, activity_id)

    conn.commit()
    return stats

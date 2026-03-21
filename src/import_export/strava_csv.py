"""Strava export CSV → DB 임포트.

Strava > 내 계정 데이터 내보내기에서 얻은 파일을 파싱:
- activities.csv : 활동 메타데이터 + 파일명
- shoes.csv      : 신발 목록

activities/ 폴더의 GPX/FIT/TCX 파일은 별도 처리 (향후 확장).
"""
from __future__ import annotations

import csv
import gzip
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from src.utils.dedup import assign_group_id

# ── Strava 활동 유형 → 내부 유형 ─────────────────────────────────────────
_TYPE_MAP: dict[str, str] = {
    "Run": "running",
    "Walk": "walking",
    "Hike": "hiking",
    "Swim": "swimming",
    "Ride": "cycling",
    "VirtualRide": "cycling",
    "VirtualRun": "running",
    "WeightTraining": "strength",
    "Weight Training": "strength",
    "Workout": "workout",
    "Elliptical": "elliptical",
    "Yoga": "yoga",
    "HIIT": "hiit",
}


# ── 파싱 헬퍼 ────────────────────────────────────────────────────────────

def _clean(v: str | None) -> str | None:
    if v is None:
        return None
    v = v.strip()
    return None if v == "" else v


def _float(v: str | None) -> float | None:
    v = _clean(v)
    if v is None:
        return None
    try:
        return float(v)
    except ValueError:
        return None


def _int(v: str | None) -> int | None:
    f = _float(v)
    return int(f) if f is not None else None


def _parse_strava_date(v: str) -> str | None:
    """'Nov 17, 2023, 10:56:10 PM' → ISO 8601."""
    v = (v or "").strip()
    if not v:
        return None
    for fmt in (
        "%b %d, %Y, %I:%M:%S %p",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
    ):
        try:
            return datetime.strptime(v, fmt).isoformat()
        except ValueError:
            continue
    return v


def _speed_to_pace(speed_m_s: float | None) -> int | None:
    """m/s → sec/km."""
    if not speed_m_s or speed_m_s <= 0:
        return None
    return int(1000 / speed_m_s)


def _parse_activity_row(row: dict[str, str]) -> dict[str, Any]:
    """activities.csv 단일 행 → 정규화된 dict."""
    activity_type_raw = _clean(row.get("Activity Type")) or "Run"
    activity_type = _TYPE_MAP.get(activity_type_raw, activity_type_raw.lower())

    start_time = _parse_strava_date(row.get("Activity Date", ""))
    distance_m = _float(row.get("Distance"))
    distance_km = distance_m / 1000 if distance_m else None

    moving_time_sec = _int(row.get("Moving Time"))
    elapsed_time_sec = _int(row.get("Elapsed Time"))
    duration_sec = moving_time_sec or elapsed_time_sec

    avg_speed = _float(row.get("Average Speed"))
    avg_pace_sec_km = _speed_to_pace(avg_speed)

    # pace가 없으면 distance/time으로 계산
    if avg_pace_sec_km is None and distance_km and duration_sec and distance_km > 0:
        avg_pace_sec_km = int(duration_sec / distance_km)

    return {
        "source_id": str(row.get("Activity ID", "")).strip(),
        "activity_type": activity_type,
        "start_time": start_time,
        "description": _clean(row.get("Activity Name")),
        "distance_km": distance_km,
        "duration_sec": duration_sec,
        "avg_pace_sec_km": avg_pace_sec_km,
        "avg_hr": _int(row.get("Average Heart Rate")),
        "max_hr": _int(row.get("Max Heart Rate")),
        "avg_cadence": _int(row.get("Average Cadence")),
        "elevation_gain": _float(row.get("Elevation Gain")),
        "calories": _int(row.get("Calories")),
        "avg_power": _int(row.get("Average Watts")),
        # 확장 필드 (raw payload로만 저장)
        "max_speed": _float(row.get("Max Speed")),
        "max_power": _int(row.get("Max Watts")),
        "elevation_loss": _float(row.get("Elevation Loss")),
        "max_cadence": _int(row.get("Max Cadence")),
        "relative_effort": _int(row.get("Relative Effort")),
        "gear": _clean(row.get("Activity Gear")),
        "filename": _clean(row.get("Filename")),
        "activity_type_raw": activity_type_raw,
        "moving_time_sec": moving_time_sec,
        "elapsed_time_sec": elapsed_time_sec,
    }


# ── 활동 임포트 ──────────────────────────────────────────────────────────

def import_strava_activities(
    conn: sqlite3.Connection,
    activities_csv: Path,
) -> dict[str, int]:
    """activities.csv → activity_summaries 적재.

    Returns:
        {"inserted": n, "skipped": n, "errors": n}
    """
    inserted = skipped = errors = 0

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
                    parsed["activity_type"],
                    parsed["start_time"],
                    parsed["distance_km"],
                    parsed["duration_sec"],
                    parsed["avg_pace_sec_km"],
                    parsed["avg_hr"],
                    parsed["max_hr"],
                    parsed["avg_cadence"],
                    parsed["elevation_gain"],
                    parsed["calories"],
                    parsed["description"],
                    parsed["avg_power"],
                    parsed.get("filename"),
                ),
            )
        except sqlite3.Error as e:
            print(f"[strava_csv] DB 삽입 오류 (source_id={source_id}): {e}")
            errors += 1
            continue

        if cursor.rowcount == 0:
            # 이미 존재 — NULL 필드 보완
            _fill_null_fields(conn, source_id, parsed)
            skipped += 1
            continue

        activity_id = cursor.lastrowid
        inserted += 1

        # raw payload 저장
        payload = {k: v for k, v in parsed.items() if v is not None}
        try:
            conn.execute(
                """INSERT OR REPLACE INTO raw_source_payloads
                   (source, entity_type, entity_id, activity_id, payload_json,
                    created_at, updated_at)
                   VALUES ('strava', 'csv_export', ?, ?, ?, datetime('now'), datetime('now'))""",
                (source_id, activity_id, json.dumps(payload, ensure_ascii=False)),
            )
        except sqlite3.Error:
            pass

        assign_group_id(conn, activity_id)

    conn.commit()
    return {"inserted": inserted, "skipped": skipped, "errors": errors}


def _fill_null_fields(
    conn: sqlite3.Connection, source_id: str, parsed: dict[str, Any]
) -> None:
    """기존 row의 NULL 필드를 새로 파싱한 값으로 보완."""
    updatable = {
        "avg_hr": parsed.get("avg_hr"),
        "max_hr": parsed.get("max_hr"),
        "avg_cadence": parsed.get("avg_cadence"),
        "elevation_gain": parsed.get("elevation_gain"),
        "calories": parsed.get("calories"),
        "avg_power": parsed.get("avg_power"),
        "export_filename": parsed.get("filename"),
    }
    sets = []
    vals = []
    for col, val in updatable.items():
        if val is not None:
            sets.append(f"{col} = COALESCE({col}, ?)")
            vals.append(val)
    if sets:
        vals.extend(["strava", source_id])
        conn.execute(
            f"UPDATE activity_summaries SET {', '.join(sets)} WHERE source=? AND source_id=?",
            vals,
        )


# ── 신발 임포트 ──────────────────────────────────────────────────────────

def import_strava_shoes(
    conn: sqlite3.Connection,
    shoes_csv: Path,
) -> dict[str, int]:
    """shoes.csv → shoes 테이블 적재.

    Returns:
        {"inserted": n, "skipped": n}
    """
    inserted = skipped = 0

    with open(shoes_csv, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    for raw in rows:
        brand = _clean(raw.get("Shoe Brand"))
        model = _clean(raw.get("Shoe Model"))
        name = _clean(raw.get("Shoe Name"))
        sport = _clean(raw.get("Shoe Default Sport Types"))

        if not brand and not model:
            skipped += 1
            continue

        try:
            cursor = conn.execute(
                """INSERT OR IGNORE INTO shoes
                   (source, brand, model, name, default_sport_types)
                   VALUES ('strava', ?, ?, ?, ?)""",
                (brand, model, name, sport),
            )
            if cursor.rowcount == 0:
                skipped += 1
            else:
                inserted += 1
        except sqlite3.Error as e:
            print(f"[strava_csv] shoes 삽입 오류: {e}")
            skipped += 1

    conn.commit()
    return {"inserted": inserted, "skipped": skipped}


# ── 통합 임포트 ──────────────────────────────────────────────────────────

def import_strava_folder(
    conn: sqlite3.Connection,
    folder: Path,
) -> dict[str, Any]:
    """Strava export 폴더에서 activities.csv + shoes.csv 임포트.

    Args:
        folder: strava export 루트 폴더 (activities.csv, shoes.csv가 있는 곳)
    """
    result: dict[str, Any] = {}

    activities_csv = folder / "activities.csv"
    if activities_csv.exists():
        r = import_strava_activities(conn, activities_csv)
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

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
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# Strava export CSV는 UTC 기준. Garmin CSV는 로컬(KST) 기준.
# dedup이 동작하려면 동일 기준으로 맞춰야 하므로 UTC → KST(+9h) 변환.
_LOCAL_UTC_OFFSET = timedelta(hours=9)

from src.utils.dedup import assign_group_id
from src.utils.raw_payload import update_changed_fields

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
    """'Nov 17, 2023, 10:56:10 PM' (UTC) → ISO 8601 로컬 시간 (KST +9h).

    Strava export CSV의 날짜는 UTC 기준이므로 로컬 오프셋을 더해
    Garmin CSV(로컬 시간) 기준의 dedup과 맞춘다.
    """
    v = (v or "").strip()
    if not v:
        return None
    for fmt in (
        "%b %d, %Y, %I:%M:%S %p",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
    ):
        try:
            dt_utc = datetime.strptime(v, fmt)
            return (dt_utc + _LOCAL_UTC_OFFSET).isoformat()
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
        "activity_description": _clean(row.get("Activity Description")),
        "distance_km": distance_km,
        "duration_sec": duration_sec,
        "avg_pace_sec_km": avg_pace_sec_km,
        "avg_hr": _int(row.get("Average Heart Rate")),
        "max_hr": _int(row.get("Max Heart Rate")),
        "avg_cadence": _int(row.get("Average Cadence")),
        "elevation_gain": _float(row.get("Elevation Gain")),
        "calories": _int(row.get("Calories")),
        "avg_power": _int(row.get("Average Watts")),
        # 확장 필드 (raw payload + activity_detail_metrics 저장)
        "max_speed": _float(row.get("Max Speed")),
        "max_power": _int(row.get("Max Watts")),
        "elevation_loss": _float(row.get("Elevation Loss")),
        "elevation_low": _float(row.get("Elevation Low")),
        "elevation_high": _float(row.get("Elevation High")),
        "max_cadence": _int(row.get("Max Cadence")),
        "relative_effort": _float(row.get("Relative Effort")),
        "training_load": _float(row.get("Training Load")),
        "intensity": _float(row.get("Intensity")),
        "avg_grade": _float(row.get("Average Grade")),
        "grade_adjusted_distance_m": _float(row.get("Grade Adjusted Distance")),
        "avg_grade_adjusted_pace_sec_km": _int(row.get("Average Grade Adjusted Pace")),
        "total_work_joules": _float(row.get("Total Work")),
        "total_steps": _int(row.get("Total Steps")),
        "avg_temp_c": _float(row.get("Average Temperature")),
        # 날씨 데이터
        "weather_condition": _clean(row.get("Weather Condition")),
        "weather_temp_c": _float(row.get("Weather Temperature")),
        "weather_humidity": _float(row.get("Humidity")),
        "wind_speed_ms": _float(row.get("Wind Speed")),
        "wind_gust_ms": _float(row.get("Wind Gust")),
        "uv_index": _float(row.get("UV Index")),
        "cloud_cover": _float(row.get("Cloud Cover")),
        "gear": _clean(row.get("Activity Gear")),
        "filename": _clean(row.get("Filename")),
        "activity_type_raw": activity_type_raw,
        "moving_time_sec": moving_time_sec,
        "elapsed_time_sec": elapsed_time_sec,
    }


# ── Detail Metrics 저장 ──────────────────────────────────────────────────

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
    """CSV 파싱 데이터 → activity_detail_metrics INSERT/UPDATE.

    이미 존재하는 metric은 값을 교체(DELETE+INSERT)하여 최신 CSV값으로 갱신한다.
    best_efforts, stream_file 등 API 전용 metrics는 건드리지 않는다.
    """
    for metric_name, parsed_key in _DETAIL_METRIC_KEYS:
        val = parsed.get(parsed_key)
        if val is None:
            continue
        conn.execute(
            "DELETE FROM activity_detail_metrics "
            "WHERE activity_id=? AND source='strava' AND metric_name=?",
            (activity_id, metric_name),
        )
        conn.execute(
            "INSERT INTO activity_detail_metrics "
            "(activity_id, source, metric_name, metric_value) VALUES (?,?,?,?)",
            (activity_id, "strava", metric_name, float(val)),
        )


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
            "SELECT a.id, p.payload_json "
            "FROM activity_summaries a "
            "JOIN raw_source_payloads p ON p.activity_id = a.id "
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
            "SELECT COUNT(*) FROM activity_detail_metrics "
            "WHERE activity_id = ? AND source = 'strava'",
            (activity_id,),
        ).fetchone()[0]
        _upsert_strava_detail_metrics(conn, activity_id, parsed)
        after = conn.execute(
            "SELECT COUNT(*) FROM activity_detail_metrics "
            "WHERE activity_id = ? AND source = 'strava'",
            (activity_id,),
        ).fetchone()[0]
        if after > before:
            stats["inserted_activities"] += 1
        stats["processed"] += 1

    conn.commit()
    return stats


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
            # 이미 존재 — 변경/누락 필드 업데이트 + detail metrics 갱신
            existing_id = update_changed_fields(conn, "strava", source_id, {
                "start_time": parsed.get("start_time"),
                "distance_km": parsed.get("distance_km"),
                "duration_sec": parsed.get("duration_sec"),
                "avg_pace_sec_km": parsed.get("avg_pace_sec_km"),
                "avg_hr": parsed.get("avg_hr"),
                "max_hr": parsed.get("max_hr"),
                "avg_cadence": parsed.get("avg_cadence"),
                "elevation_gain": parsed.get("elevation_gain"),
                "calories": parsed.get("calories"),
                "avg_power": parsed.get("avg_power"),
                "export_filename": parsed.get("filename"),
            })
            if existing_id:
                _upsert_strava_detail_metrics(conn, existing_id, parsed)
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

        _upsert_strava_detail_metrics(conn, activity_id, parsed)
        assign_group_id(conn, activity_id)

    conn.commit()
    return {"inserted": inserted, "skipped": skipped, "errors": errors}


def _fill_null_fields(
    conn: sqlite3.Connection, source_id: str, parsed: dict[str, Any]
) -> None:
    """기존 row의 NULL 필드를 보완하고, start_time을 CSV 파싱값으로 교정.

    start_time은 COALESCE 없이 강제 업데이트한다.
    기존 row가 UTC로 저장되어 있을 경우(이전 임포트 버그)를 교정하기 위해.
    """
    sets = []
    vals = []

    # start_time: 강제 업데이트 (UTC→KST 교정)
    if parsed.get("start_time"):
        sets.append("start_time = ?")
        vals.append(parsed["start_time"])

    # 나머지 필드: NULL인 경우만 채움
    null_fill = {
        "avg_hr": parsed.get("avg_hr"),
        "max_hr": parsed.get("max_hr"),
        "avg_cadence": parsed.get("avg_cadence"),
        "elevation_gain": parsed.get("elevation_gain"),
        "calories": parsed.get("calories"),
        "avg_power": parsed.get("avg_power"),
        "export_filename": parsed.get("filename"),
    }
    for col, val in null_fill.items():
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

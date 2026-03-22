"""Garmin export CSV → DB 임포트.

Garmin Connect > 활동 내보내기 CSV 파일을 파싱하여
activity_summaries 테이블에 적재한다.

지원 파일: garmin_running_*.csv, garmin_all_activities_*.csv 등
(공통 헤더: 한국어 컬럼명, UTF-8 인코딩)
"""
from __future__ import annotations

import csv
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from src.utils.dedup import assign_group_id
from src.utils.raw_payload import update_changed_fields

# ── Garmin CSV → activity_detail_metrics 매핑 ────────────────────────────
# (metric_name: DB 컬럼명, parsed_key: _parse_row() 반환 키)
_GARMIN_DETAIL_METRICS: list[tuple[str, str]] = [
    ("training_effect_aerobic",  "aerobic_te"),
    ("avg_stride_length",        "avg_stride"),
    ("avg_vertical_ratio",       "avg_vertical_ratio"),
    ("avg_vertical_oscillation", "avg_vertical_oscillation"),
    ("avg_ground_contact_time",  "avg_ground_contact"),
    ("normalized_power",         "np_watts"),
    ("training_stress_score",    "tss"),
    ("max_power",                "max_power"),
    ("steps",                    "steps"),
    ("body_battery_drain",       "body_battery_drain"),
    ("elevation_loss",           "elevation_loss"),
    ("lap_count",                "lap_count"),
    ("avg_run_cadence",          "avg_cadence"),
    ("max_run_cadence",          "max_cadence"),
]

# ── 한국어 컬럼명 → 내부 필드명 매핑 ────────────────────────────────────
_COL = {
    "활동 종류": "activity_type",
    "날짜": "start_time",
    "즐겨찾기": "favorite",
    "제목": "description",
    "거리": "distance_km",
    "칼로리": "calories",
    "시간": "duration_hms",
    "평균 심박": "avg_hr",
    "최대심박": "max_hr",
    "유산소 훈련 효과": "aerobic_te",
    "평균 달리기 케이던스": "avg_cadence",
    "최고 달리기 케이던스": "max_cadence",
    "평균 페이스": "avg_pace_str",
    "최대 페이스": "max_pace_str",
    "총 상승": "elevation_gain",
    "총 하강": "elevation_loss",
    "평균 보폭": "avg_stride",
    "평균 수직 비율": "avg_vertical_ratio",
    "평균 수직 진동": "avg_vertical_oscillation",
    "평균 지면 접촉 시간": "avg_ground_contact",
    "평균 GAP": "avg_gap_str",
    "Normalized Power® (NP®)": "np_watts",
    "Training Stress Score®": "tss",
    "평균 파워": "avg_power",
    "최대 파워": "max_power",
    "걸음": "steps",
    "바디 배터리 방전": "body_battery_drain",
    "최저 온도": "min_temp",
    "최고 온도": "max_temp",
    "이동 시간": "moving_time_hms",
    "경과 시간": "elapsed_time_hms",
    "최저 해발": "min_elevation",
    "최고 해발": "max_elevation",
    "랩 수": "lap_count",
}

# ── 활동 유형 한국어 → 영어 ──────────────────────────────────────────────
_TYPE_MAP: dict[str, str] = {
    "러닝": "running",
    "트레드밀 러닝": "treadmill",
    "실내 달리기": "treadmill",
    "트레일 러닝": "trail_running",
    "트랙 러닝": "track_running",
    "수영": "swimming",
    "풀 수영": "swimming",
    "실외 수영": "open_water_swimming",
    "하이킹": "hiking",
    "보행": "walking",
    "근력 훈련": "strength",
    "HIIT": "hiit",
    "요가": "yoga",
    "일립티컬": "elliptical",
}


# ── Detail Metrics 저장 헬퍼 ─────────────────────────────────────────────

def _upsert_garmin_detail_metrics(
    conn: sqlite3.Connection, activity_id: int, parsed: dict[str, Any]
) -> None:
    """CSV 파싱 데이터 → activity_detail_metrics INSERT/UPDATE.

    이미 존재하는 metric은 값을 교체(DELETE+INSERT)하여 최신 CSV값으로 갱신한다.
    """
    for metric_name, parsed_key in _GARMIN_DETAIL_METRICS:
        val = parsed.get(parsed_key)
        if val is None:
            continue
        conn.execute(
            "DELETE FROM activity_detail_metrics "
            "WHERE activity_id=? AND source='garmin' AND metric_name=?",
            (activity_id, metric_name),
        )
        conn.execute(
            "INSERT INTO activity_detail_metrics "
            "(activity_id, source, metric_name, metric_value) VALUES (?,?,?,?)",
            (activity_id, "garmin", metric_name, float(val)),
        )


def backfill_garmin_detail_metrics(
    conn: sqlite3.Connection,
    csv_folder: Path | None = None,
) -> dict[str, int]:
    """raw_source_payloads에서 Garmin CSV activity_detail_metrics 역채움.

    csv_folder가 주어지면 CSV를 직접 파싱(최신 필드 보장)한다.

    Returns:
        {"processed": n, "inserted_activities": n, "skipped": n}
    """
    stats: dict[str, int] = {"processed": 0, "inserted_activities": 0, "skipped": 0}

    if csv_folder is not None and csv_folder.is_dir():
        source_data: list[tuple[int, dict]] = []
        for csv_path in sorted(csv_folder.glob("*.csv")):
            try:
                with open(csv_path, encoding="utf-8-sig") as f:
                    raw_rows = list(csv.DictReader(f))
            except Exception:
                try:
                    with open(csv_path, encoding="utf-8") as f:
                        raw_rows = list(csv.DictReader(f))
                except Exception:
                    stats["skipped"] += 1
                    continue
            for raw in raw_rows:
                try:
                    parsed = _parse_row(raw)
                except Exception:
                    stats["skipped"] += 1
                    continue
                if not parsed.get("start_time"):
                    continue
                source_id = f"exp_{parsed['start_time']}"
                row = conn.execute(
                    "SELECT id FROM activity_summaries WHERE source='garmin' AND source_id=?",
                    (source_id,),
                ).fetchone()
                if row:
                    source_data.append((row[0], parsed))
    else:
        payload_rows = conn.execute(
            "SELECT a.id, p.payload_json "
            "FROM activity_summaries a "
            "JOIN raw_source_payloads p ON p.activity_id = a.id "
            "WHERE a.source = 'garmin' AND p.entity_type = 'csv_export'",
        ).fetchall()
        source_data = []
        for activity_id, pj in payload_rows:
            try:
                source_data.append((activity_id, json.loads(pj)))
            except Exception:
                stats["skipped"] += 1

    for activity_id, parsed in source_data:
        before = conn.execute(
            "SELECT COUNT(*) FROM activity_detail_metrics WHERE activity_id=? AND source='garmin'",
            (activity_id,),
        ).fetchone()[0]
        _upsert_garmin_detail_metrics(conn, activity_id, parsed)
        after = conn.execute(
            "SELECT COUNT(*) FROM activity_detail_metrics WHERE activity_id=? AND source='garmin'",
            (activity_id,),
        ).fetchone()[0]
        if after > before:
            stats["inserted_activities"] += 1
        stats["processed"] += 1

    conn.commit()
    return stats


# ── 파싱 헬퍼 ────────────────────────────────────────────────────────────

def _clean(v: str | None) -> str | None:
    """빈 문자열, '--', None → None."""
    if v is None:
        return None
    v = v.strip()
    return None if v in ("", "--", "아니오") else v


def _float(v: str | None) -> float | None:
    if v is None:
        return None
    try:
        return float(v.replace(",", ""))
    except (ValueError, AttributeError):
        return None


def _int(v: str | None) -> int | None:
    f = _float(v)
    return int(f) if f is not None else None


def _hms_to_sec(v: str | None) -> int | None:
    """'HH:MM:SS' 또는 'MM:SS' → 초."""
    if not v:
        return None
    parts = v.split(":")
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
    except (ValueError, IndexError):
        pass
    return None


def _pace_to_sec(v: str | None) -> int | None:
    """'M:SS' 형식 페이스 → 초/km."""
    if not v:
        return None
    parts = v.split(":")
    try:
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
    except (ValueError, IndexError):
        pass
    return None


def _parse_row(raw: dict[str, str]) -> dict[str, Any]:
    """CSV 행 → 정규화된 dict."""
    # 한국어 컬럼명 → 내부 필드명으로 변환
    mapped: dict[str, str | None] = {}
    for kr_key, en_key in _COL.items():
        mapped[en_key] = _clean(raw.get(kr_key, ""))

    # 활동 유형
    act_type_kr = (mapped.get("activity_type") or "").strip()
    activity_type = _TYPE_MAP.get(act_type_kr, act_type_kr.lower() if act_type_kr else "unknown")

    # start_time: "2026-03-21 15:50:13" → ISO 8601
    start_raw = mapped.get("start_time") or ""
    try:
        dt = datetime.strptime(start_raw, "%Y-%m-%d %H:%M:%S")
        start_time = dt.isoformat()
    except ValueError:
        start_time = start_raw

    # 거리 단위 변환: 수영·트랙러닝은 Garmin CSV에서 미터로 기록됨 → km 변환
    raw_dist = _float(mapped.get("distance_km"))
    _METER_TYPES = {"swimming", "open_water_swimming", "track_running"}
    if raw_dist is not None and activity_type in _METER_TYPES and raw_dist > 10:
        raw_dist = round(raw_dist / 1000, 4)

    return {
        "activity_type": activity_type,
        "start_time": start_time,
        "description": mapped.get("description"),
        "distance_km": raw_dist,
        "calories": _int(mapped.get("calories")),
        "duration_sec": _hms_to_sec(mapped.get("duration_hms")),
        "avg_hr": _int(mapped.get("avg_hr")),
        "max_hr": _int(mapped.get("max_hr")),
        "avg_cadence": _int(mapped.get("avg_cadence")),
        "elevation_gain": _float(mapped.get("elevation_gain")),
        "avg_pace_sec_km": _pace_to_sec(mapped.get("avg_pace_str")),
        "avg_power": _int(mapped.get("avg_power")),
        # 원본 payload에 저장할 확장 필드
        "aerobic_te": _float(mapped.get("aerobic_te")),
        "avg_stride": _float(mapped.get("avg_stride")),
        "avg_vertical_ratio": _float(mapped.get("avg_vertical_ratio")),
        "avg_vertical_oscillation": _float(mapped.get("avg_vertical_oscillation")),
        "avg_ground_contact": _int(mapped.get("avg_ground_contact")),
        "np_watts": _int(mapped.get("np_watts")),
        "tss": _float(mapped.get("tss")),
        "max_power": _int(mapped.get("max_power")),
        "steps": _int(mapped.get("steps")),
        "body_battery_drain": _int(mapped.get("body_battery_drain")),
        "elevation_loss": _float(mapped.get("elevation_loss")),
        "min_elevation": _float(mapped.get("min_elevation")),
        "max_elevation": _float(mapped.get("max_elevation")),
        "min_temp": _float(mapped.get("min_temp")),
        "max_temp": _float(mapped.get("max_temp")),
        "lap_count": _int(mapped.get("lap_count")),
    }


# ── DB 적재 ──────────────────────────────────────────────────────────────

def import_garmin_csv(
    conn: sqlite3.Connection,
    csv_path: Path,
) -> dict[str, int]:
    """단일 Garmin CSV 파일을 DB에 적재.

    Returns:
        {"inserted": n, "skipped": n, "errors": n}
    """
    inserted = skipped = errors = 0

    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    for raw in rows:
        try:
            parsed = _parse_row(raw)
        except Exception as e:
            print(f"[garmin_csv] 파싱 오류 ({csv_path.name}): {e}")
            errors += 1
            continue

        if not parsed["start_time"]:
            errors += 1
            continue

        # source_id: "exp_" + start_time (API 동기화 ID와 구분)
        source_id = f"exp_{parsed['start_time']}"

        try:
            cursor = conn.execute(
                """INSERT OR IGNORE INTO activity_summaries
                   (source, source_id, activity_type, start_time,
                    distance_km, duration_sec, avg_pace_sec_km,
                    avg_hr, max_hr, avg_cadence, elevation_gain,
                    calories, description, avg_power, export_filename)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    "garmin", source_id,
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
                    csv_path.name,
                ),
            )
        except sqlite3.Error as e:
            print(f"[garmin_csv] DB 삽입 오류: {e}")
            errors += 1
            continue

        if cursor.rowcount == 0:
            # 이미 존재 — 변경/누락 필드 업데이트 + detail metrics 갱신
            existing_id = update_changed_fields(conn, "garmin", source_id, {
                "distance_km": parsed.get("distance_km"),
                "duration_sec": parsed.get("duration_sec"),
                "avg_pace_sec_km": parsed.get("avg_pace_sec_km"),
                "avg_hr": parsed.get("avg_hr"),
                "max_hr": parsed.get("max_hr"),
                "avg_cadence": parsed.get("avg_cadence"),
                "elevation_gain": parsed.get("elevation_gain"),
                "calories": parsed.get("calories"),
                "avg_power": parsed.get("avg_power"),
            })
            if existing_id:
                _upsert_garmin_detail_metrics(conn, existing_id, parsed)
            skipped += 1
            continue

        activity_id = cursor.lastrowid
        inserted += 1

        # raw payload 저장
        payload = {k: v for k, v in parsed.items() if v is not None}
        payload["_source_file"] = csv_path.name
        try:
            conn.execute(
                """INSERT OR REPLACE INTO raw_source_payloads
                   (source, entity_type, entity_id, activity_id, payload_json,
                    created_at, updated_at)
                   VALUES ('garmin', 'csv_export', ?, ?, ?, datetime('now'), datetime('now'))""",
                (source_id, activity_id, json.dumps(payload, ensure_ascii=False)),
            )
        except sqlite3.Error:
            pass  # raw payload 실패는 무시

        _upsert_garmin_detail_metrics(conn, activity_id, parsed)
        assign_group_id(conn, activity_id)

    conn.commit()
    return {"inserted": inserted, "skipped": skipped, "errors": errors}


def import_garmin_folder(
    conn: sqlite3.Connection,
    folder: Path,
) -> dict[str, Any]:
    """폴더 내 모든 Garmin CSV를 순서대로 임포트.

    Returns:
        {"files": [...결과...], "total": {...합계...}}
    """
    csv_files = sorted(folder.glob("*.csv"))
    if not csv_files:
        return {"files": [], "total": {"inserted": 0, "skipped": 0, "errors": 0}}

    results = []
    total = {"inserted": 0, "skipped": 0, "errors": 0}

    for csv_path in csv_files:
        result = import_garmin_csv(conn, csv_path)
        result["file"] = csv_path.name
        results.append(result)
        for k in total:
            total[k] += result[k]
        print(
            f"[garmin_csv] {csv_path.name}: "
            f"+{result['inserted']} 신규, {result['skipped']} 중복, {result['errors']} 오류"
        )

    return {"files": results, "total": total}

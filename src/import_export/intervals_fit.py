"""intervals.icu FIT 파일 → DB 임포트.

FIT 파일의 session/activity 메시지를 파싱하여
activity_summaries 테이블에 적재한다.

지원 파일: intervals.icu export *.fit (바이너리 ANT+ FIT 형식)
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import fitparse
except ImportError as e:
    raise ImportError("fitparse 라이브러리 필요: pip install fitparse") from e

from src.utils.dedup import assign_group_id
from src.utils.raw_payload import update_changed_fields

# ── FIT → activity_detail_metrics 매핑 ───────────────────────────────────
_INTERVALS_FIT_DETAIL_METRICS: list[tuple[str, str]] = [
    ("normalized_power",      "normalized_power"),
    ("training_stress_score", "tss"),
    ("max_power",             "max_power"),
    ("lap_count",             "num_laps"),
    ("max_speed",             "max_speed"),
    ("elevation_loss",        "elevation_loss"),
    ("avg_run_cadence",       "avg_cadence"),
]

# ── sport 필드 → 내부 activity_type 매핑 ─────────────────────────────────
_SPORT_MAP: dict[str, str] = {
    "running": "running",
    "cycling": "cycling",
    "swimming": "swimming",
    "hiking": "hiking",
    "walking": "walking",
    "fitness_equipment": "strength",
    "training": "strength",
    "generic": "unknown",
}

_SUB_SPORT_MAP: dict[str, str] = {
    "treadmill": "treadmill",
    "track": "track_running",
    "trail": "trail_running",
    "indoor_cycling": "indoor_cycling",
    "spin": "indoor_cycling",
    "lap_swimming": "swimming",
    "open_water": "open_water_swimming",
}


def _activity_type(sport: str | None, sub_sport: str | None) -> str:
    """sport + sub_sport → 내부 activity_type."""
    if sub_sport and sub_sport in _SUB_SPORT_MAP:
        return _SUB_SPORT_MAP[sub_sport]
    return _SPORT_MAP.get(sport or "", "unknown")


def _parse_fit(fit_path: Path) -> dict[str, Any] | None:
    """단일 FIT 파일 파싱 → 정규화된 dict 또는 None."""
    try:
        fit = fitparse.FitFile(str(fit_path))
    except Exception:
        return None

    # session 메시지에서 핵심 지표 추출
    sessions = list(fit.get_messages("session"))
    if not sessions:
        return None

    sess = sessions[0]
    sess_data: dict[str, Any] = {f.name: f.value for f in sess if f.value is not None}

    # activity 메시지에서 timestamp(UTC 종료) + local_timestamp(로컬 종료) 추출
    # local_timestamp는 활동 종료 시각의 로컬 시간이므로 시작 시각 계산에 오프셋만 사용
    act_ts_utc: datetime | None = None
    act_local_ts: datetime | None = None
    for act_msg in fit.get_messages("activity"):
        for f in act_msg:
            if f.name == "timestamp" and f.value is not None:
                act_ts_utc = f.value
            elif f.name == "local_timestamp" and f.value is not None:
                act_local_ts = f.value
        if act_ts_utc:
            break

    # sport 정보
    sport_str: str | None = None
    sub_sport_str: str | None = None
    for sp_msg in fit.get_messages("sport"):
        for f in sp_msg:
            if f.name == "sport":
                sport_str = str(f.value) if f.value else None
            elif f.name == "sub_sport":
                sub_sport_str = str(f.value) if f.value else None
    # session에도 sport 있음
    if not sport_str:
        sport_str = str(sess_data.get("sport", "")) or None
    if not sub_sport_str:
        sub_sport_str = str(sess_data.get("sub_sport", "")) or None

    # start_time: session.start_time(UTC) + 로컬 오프셋 → 로컬 시작 시각
    # 로컬 오프셋 = activity.local_timestamp - activity.timestamp (둘 다 종료 시각)
    sess_start_utc: datetime | None = sess_data.get("start_time")
    if sess_start_utc is None:
        return None
    if act_ts_utc is not None and act_local_ts is not None:
        local_offset = act_local_ts - act_ts_utc
        start_dt = sess_start_utc + local_offset
    else:
        # fallback: UTC 그대로 (오프셋 정보 없음)
        start_dt = sess_start_utc
    start_time = start_dt.isoformat()

    # 거리 (m → km)
    total_distance_m = sess_data.get("total_distance")
    distance_km = round(total_distance_m / 1000, 4) if total_distance_m else None

    # 시간 (초)
    duration_sec_raw = sess_data.get("total_elapsed_time")
    duration_sec = int(round(duration_sec_raw)) if duration_sec_raw else None

    # 페이스 (avg_speed m/s → sec/km)
    avg_speed = sess_data.get("avg_speed") or sess_data.get("enhanced_avg_speed")
    avg_pace_sec_km: int | None = None
    if avg_speed and avg_speed > 0:
        avg_pace_sec_km = int(round(1000 / avg_speed))

    # 케이던스: FIT avg_running_cadence는 한쪽 발(stride/min) → 양발 spm으로 변환
    # Garmin CSV의 avg_cadence는 양발 spm이므로 단위 일치 필요
    avg_cadence_raw = sess_data.get("avg_running_cadence")
    avg_cadence = int(avg_cadence_raw * 2) if avg_cadence_raw is not None else None

    # 상승고도
    elevation_gain_raw = sess_data.get("total_ascent")
    elevation_gain = float(elevation_gain_raw) if elevation_gain_raw is not None else None

    return {
        "activity_type": _activity_type(sport_str, sub_sport_str),
        "start_time": start_time,
        "distance_km": distance_km,
        "duration_sec": duration_sec,
        "avg_hr": sess_data.get("avg_heart_rate"),
        "max_hr": sess_data.get("max_heart_rate"),
        "avg_cadence": avg_cadence,
        "elevation_gain": elevation_gain,
        "avg_pace_sec_km": avg_pace_sec_km,
        "avg_power": sess_data.get("avg_power"),
        "calories": sess_data.get("total_calories"),
        # 확장 필드 (raw payload용)
        "max_speed": sess_data.get("max_speed") or sess_data.get("enhanced_max_speed"),
        "normalized_power": sess_data.get("normalized_power"),
        "tss": sess_data.get("training_stress_score"),
        "max_power": sess_data.get("max_power"),
        "num_laps": sess_data.get("num_laps"),
        "total_timer_time": sess_data.get("total_timer_time"),
        "elevation_loss": sess_data.get("total_descent"),
        "sport": sport_str,
        "sub_sport": sub_sport_str,
    }


# ── DB 적재 ──────────────────────────────────────────────────────────────

def _upsert_intervals_fit_detail_metrics(
    conn: sqlite3.Connection, activity_id: int, parsed: dict[str, Any]
) -> None:
    """FIT 파싱 데이터 → activity_detail_metrics INSERT/UPDATE."""
    for metric_name, parsed_key in _INTERVALS_FIT_DETAIL_METRICS:
        val = parsed.get(parsed_key)
        if val is None:
            continue
        conn.execute(
            "DELETE FROM activity_detail_metrics "
            "WHERE activity_id=? AND source='intervals' AND metric_name=?",
            (activity_id, metric_name),
        )
        conn.execute(
            "INSERT INTO activity_detail_metrics "
            "(activity_id, source, metric_name, metric_value) VALUES (?,?,?,?)",
            (activity_id, "intervals", metric_name, float(val)),
        )


def import_intervals_fit(
    conn: sqlite3.Connection,
    fit_path: Path,
) -> dict[str, int]:
    """단일 FIT 파일을 DB에 적재.

    Returns:
        {"inserted": n, "skipped": n, "errors": n}
    """
    parsed = _parse_fit(fit_path)
    if parsed is None:
        print(f"[intervals_fit] 파싱 실패: {fit_path.name}")
        return {"inserted": 0, "skipped": 0, "errors": 1}

    if not parsed["start_time"]:
        return {"inserted": 0, "skipped": 0, "errors": 1}

    # source_id: 파일명에서 숫자 ID 추출 (예: i100193210__.fit → 100193210)
    stem = fit_path.stem  # "i100193210__"
    numeric_part = stem.lstrip("i").split("_")[0]
    source_id = f"fit_{numeric_part}" if numeric_part.isdigit() else f"fit_{stem}"

    try:
        cursor = conn.execute(
            """INSERT OR IGNORE INTO activity_summaries
               (source, source_id, activity_type, start_time,
                distance_km, duration_sec, avg_pace_sec_km,
                avg_hr, max_hr, avg_cadence, elevation_gain,
                calories, avg_power, export_filename)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "intervals",
                source_id,
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
                parsed["avg_power"],
                fit_path.name,
            ),
        )
    except sqlite3.Error as e:
        print(f"[intervals_fit] DB 삽입 오류 ({fit_path.name}): {e}")
        return {"inserted": 0, "skipped": 0, "errors": 1}

    if cursor.rowcount == 0:
        # 이미 존재 — 변경/누락 필드 업데이트 + detail metrics 갱신
        existing_id = update_changed_fields(conn, "intervals", source_id, {
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
            _upsert_intervals_fit_detail_metrics(conn, existing_id, parsed)
        conn.commit()
        return {"inserted": 0, "skipped": 1, "errors": 0}

    activity_id = cursor.lastrowid

    # raw payload 저장
    payload = {k: v for k, v in parsed.items() if v is not None}
    payload["_source_file"] = fit_path.name
    try:
        conn.execute(
            """INSERT OR REPLACE INTO raw_source_payloads
               (source, entity_type, entity_id, activity_id, payload_json,
                created_at, updated_at)
               VALUES ('intervals', 'fit_export', ?, ?, ?, datetime('now'), datetime('now'))""",
            (source_id, activity_id, json.dumps(payload, ensure_ascii=False, default=str)),
        )
    except sqlite3.Error:
        pass

    _upsert_intervals_fit_detail_metrics(conn, activity_id, parsed)
    assign_group_id(conn, activity_id)
    conn.commit()

    return {"inserted": 1, "skipped": 0, "errors": 0}


def import_intervals_folder(
    conn: sqlite3.Connection,
    folder: Path,
) -> dict[str, Any]:
    """폴더 내 모든 FIT 파일을 순서대로 임포트.

    Returns:
        {"files": [...결과...], "total": {...합계...}}
    """
    fit_files = sorted(folder.glob("*.fit"))
    if not fit_files:
        return {"files": [], "total": {"inserted": 0, "skipped": 0, "errors": 0}}

    total = {"inserted": 0, "skipped": 0, "errors": 0}
    results = []

    for fit_path in fit_files:
        result = import_intervals_fit(conn, fit_path)
        result["file"] = fit_path.name
        results.append(result)
        for k in total:
            total[k] += result[k]

    print(
        f"[intervals_fit] 완료: +{total['inserted']} 신규, "
        f"{total['skipped']} 중복, {total['errors']} 오류 (총 {len(fit_files)}개 파일)"
    )
    return {"files": results, "total": total}

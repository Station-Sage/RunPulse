"""RunPulse v0.3 DB 헬퍼 유틸리티.

activity_summaries, metric_store, daily_wellness, daily_fitness 등에 대한
CRUD 함수를 제공합니다. Extractor와 Sync Orchestrator가 이 함수들을 호출합니다.

사용법:
    from src.utils.db_helpers import upsert_activity, upsert_metric, get_primary_metrics
"""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
from datetime import datetime
from typing import Any, Optional

log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# source_payloads (Layer 0)
# ─────────────────────────────────────────────────────────────────────────────

def upsert_payload(
    conn: sqlite3.Connection,
    source: str,
    entity_type: str,
    entity_id: str,
    payload: str | dict,
    *,
    entity_date: str | None = None,
    activity_id: int | None = None,
    endpoint: str | None = None,
    parser_version: str = "1.0",
) -> tuple[int, bool]:
    """raw payload 저장. payload_hash로 변경 감지.

    Returns: (row_id, is_new_or_changed)
    """
    if isinstance(payload, dict):
        payload_str = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    else:
        payload_str = payload

    payload_hash = hashlib.sha256(payload_str.encode()).hexdigest()

    # 기존 hash 확인
    existing = conn.execute(
        "SELECT id, payload_hash FROM source_payloads "
        "WHERE source = ? AND entity_type = ? AND entity_id = ?",
        (source, entity_type, entity_id),
    ).fetchone()

    if existing:
        row_id, old_hash = existing[0], existing[1]
        if old_hash == payload_hash:
            return row_id, False  # 변경 없음
        # 변경됨 → UPDATE
        conn.execute(
            "UPDATE source_payloads SET payload = ?, payload_hash = ?, "
            "entity_date = ?, activity_id = ?, endpoint = ?, "
            "parser_version = ?, fetched_at = datetime('now') "
            "WHERE id = ?",
            (payload_str, payload_hash, entity_date, activity_id,
             endpoint, parser_version, row_id),
        )
        return row_id, True

    # 신규 INSERT
    cur = conn.execute(
        "INSERT INTO source_payloads "
        "(source, entity_type, entity_id, entity_date, activity_id, "
        " payload, payload_hash, endpoint, parser_version) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (source, entity_type, entity_id, entity_date, activity_id,
         payload_str, payload_hash, endpoint, parser_version),
    )
    return cur.lastrowid, True


def get_payload(
    conn: sqlite3.Connection,
    source: str,
    entity_type: str,
    entity_id: str,
) -> dict | None:
    """raw payload JSON 반환."""
    row = conn.execute(
        "SELECT payload FROM source_payloads "
        "WHERE source = ? AND entity_type = ? AND entity_id = ?",
        (source, entity_type, entity_id),
    ).fetchone()
    if row:
        return json.loads(row[0])
    return None


# ─────────────────────────────────────────────────────────────────────────────
# activity_summaries (Layer 1)
# ─────────────────────────────────────────────────────────────────────────────

# activity_summaries에 INSERT할 수 있는 컬럼 (id, created_at, updated_at 제외)
_ACTIVITY_COLUMNS = [
    "source", "source_id", "matched_group_id",
    "name", "activity_type", "start_time",
    "distance_m", "duration_sec", "moving_time_sec", "elapsed_time_sec",
    "avg_speed_ms", "max_speed_ms", "avg_pace_sec_km",
    "avg_hr", "max_hr",
    "avg_cadence", "max_cadence",
    "avg_power", "max_power", "normalized_power",
    "elevation_gain", "elevation_loss",
    "calories",
    "training_effect_aerobic", "training_effect_anaerobic",
    "training_load", "suffer_score",
    "avg_ground_contact_time_ms", "avg_stride_length_cm",
    "avg_vertical_oscillation_cm", "avg_vertical_ratio_pct",
    "start_lat", "start_lon", "end_lat", "end_lon",
    "avg_temperature",
    "description", "event_type", "device_name", "gear_id", "source_url",
]


def upsert_activity(conn: sqlite3.Connection, data: dict) -> int:
    """activity_summaries UPSERT. UNIQUE(source, source_id) 기준.

    data: Extractor가 반환한 dict. 키는 컬럼명.
    Returns: row id.
    """
    # data에서 유효한 컬럼만 필터
    cols = [c for c in _ACTIVITY_COLUMNS if c in data]
    vals = [data[c] for c in cols]

    cols_str = ", ".join(cols)
    placeholders = ", ".join("?" * len(cols))

    # ON CONFLICT → UPDATE (source, source_id 제외)
    update_cols = [c for c in cols if c not in ("source", "source_id")]
    update_clause = ", ".join(f"{c} = excluded.{c}" for c in update_cols)
    update_clause += ", updated_at = datetime('now')"

    sql = (
        f"INSERT INTO activity_summaries ({cols_str}) VALUES ({placeholders}) "
        f"ON CONFLICT(source, source_id) DO UPDATE SET {update_clause}"
    )

    cur = conn.execute(sql, vals)

    # 삽입된/업데이트된 행의 id 조회
    row = conn.execute(
        "SELECT id FROM activity_summaries WHERE source = ? AND source_id = ?",
        (data["source"], data["source_id"]),
    ).fetchone()
    return row[0]


def get_activity(conn: sqlite3.Connection, activity_id: int) -> dict | None:
    """activity_summaries 단일 행 반환."""
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM activity_summaries WHERE id = ?",
        (activity_id,),
    ).fetchone()
    if row:
        return dict(row)
    return None


def get_activity_list(
    conn: sqlite3.Connection,
    *,
    limit: int = 50,
    offset: int = 0,
    activity_type: str | None = None,
    canonical_only: bool = True,
) -> list[dict]:
    """활동 목록 조회. canonical_only=True면 대표 활동만."""
    table = "v_canonical_activities" if canonical_only else "activity_summaries"
    clauses = []
    params: list[Any] = []

    if activity_type:
        clauses.append("activity_type = ?")
        params.append(activity_type)

    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""

    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        f"SELECT * FROM {table}{where} ORDER BY start_time DESC LIMIT ? OFFSET ?",
        params + [limit, offset],
    ).fetchall()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
# metric_store (Layer 2)
# ─────────────────────────────────────────────────────────────────────────────

def upsert_metric(
    conn: sqlite3.Connection,
    scope_type: str,
    scope_id: str | int,
    metric_name: str,
    provider: str,
    *,
    numeric_value: float | None = None,
    text_value: str | None = None,
    json_value: Any = None,
    category: str | None = None,
    algorithm_version: str = "1.0",
    confidence: float | None = None,
    raw_name: str | None = None,
    parent_metric_id: int | None = None,
) -> int:
    """metric_store UPSERT. UNIQUE(scope_type, scope_id, metric_name, provider) 기준.

    Returns: row id.
    """
    scope_id_str = str(scope_id)
    json_str = json.dumps(json_value, ensure_ascii=False) if json_value is not None else None

    sql = """
        INSERT INTO metric_store
            (scope_type, scope_id, metric_name, category, provider,
             numeric_value, text_value, json_value,
             algorithm_version, confidence, raw_name, parent_metric_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(scope_type, scope_id, metric_name, provider)
        DO UPDATE SET
            numeric_value = excluded.numeric_value,
            text_value = excluded.text_value,
            json_value = excluded.json_value,
            category = COALESCE(excluded.category, category),
            algorithm_version = excluded.algorithm_version,
            confidence = excluded.confidence,
            raw_name = excluded.raw_name,
            parent_metric_id = excluded.parent_metric_id,
            updated_at = datetime('now')
    """

    cur = conn.execute(sql, (
        scope_type, scope_id_str, metric_name, category, provider,
        numeric_value, text_value, json_str,
        algorithm_version, confidence, raw_name, parent_metric_id,
    ))

    row = conn.execute(
        "SELECT id FROM metric_store "
        "WHERE scope_type = ? AND scope_id = ? AND metric_name = ? AND provider = ?",
        (scope_type, scope_id_str, metric_name, provider),
    ).fetchone()
    return row[0]


def upsert_metrics_batch(
    conn: sqlite3.Connection,
    scope_type: str,
    scope_id: str | int,
    metrics: list[dict],
) -> int:
    """여러 메트릭을 일괄 UPSERT.

    metrics: [{"metric_name": ..., "provider": ..., "numeric_value": ..., ...}, ...]
    Returns: 처리된 메트릭 수.
    """
    count = 0
    for m in metrics:
        if m.get("numeric_value") is None and m.get("text_value") is None and m.get("json_value") is None:
            continue  # 값이 전부 None이면 skip
        upsert_metric(
            conn,
            scope_type,
            scope_id,
            m["metric_name"],
            m["provider"],
            numeric_value=m.get("numeric_value"),
            text_value=m.get("text_value"),
            json_value=m.get("json_value"),
            category=m.get("category"),
            algorithm_version=m.get("algorithm_version", "1.0"),
            confidence=m.get("confidence"),
            raw_name=m.get("raw_name"),
            parent_metric_id=m.get("parent_metric_id"),
        )
        count += 1
    return count


def get_primary_metric(
    conn: sqlite3.Connection,
    scope_type: str,
    scope_id: str | int,
    metric_name: str,
) -> dict | None:
    """대표(is_primary=1) 메트릭값 반환."""
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM metric_store "
        "WHERE scope_type = ? AND scope_id = ? AND metric_name = ? AND is_primary = 1",
        (scope_type, str(scope_id), metric_name),
    ).fetchone()
    if row:
        return dict(row)
    return None


def get_primary_metrics(
    conn: sqlite3.Connection,
    scope_type: str,
    scope_id: str | int,
    names: list[str] | None = None,
) -> list[dict]:
    """scope의 모든 primary 메트릭 또는 지정된 이름들만 반환."""
    conn.row_factory = sqlite3.Row
    scope_id_str = str(scope_id)

    if names:
        placeholders = ",".join("?" * len(names))
        rows = conn.execute(
            f"SELECT * FROM metric_store "
            f"WHERE scope_type = ? AND scope_id = ? AND is_primary = 1 "
            f"AND metric_name IN ({placeholders})",
            [scope_type, scope_id_str] + names,
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM metric_store "
            "WHERE scope_type = ? AND scope_id = ? AND is_primary = 1",
            (scope_type, scope_id_str),
        ).fetchall()
    return [dict(r) for r in rows]


def get_all_providers(
    conn: sqlite3.Connection,
    scope_type: str,
    scope_id: str | int,
    metric_name: str,
) -> list[dict]:
    """한 메트릭의 모든 provider 값 비교."""
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM metric_store "
        "WHERE scope_type = ? AND scope_id = ? AND metric_name = ? "
        "ORDER BY is_primary DESC, provider",
        (scope_type, str(scope_id), metric_name),
    ).fetchall()
    return [dict(r) for r in rows]


def get_metrics_by_category(
    conn: sqlite3.Connection,
    scope_type: str,
    scope_id: str | int,
    category: str,
    *,
    primary_only: bool = True,
) -> list[dict]:
    """카테고리별 메트릭 조회."""
    conn.row_factory = sqlite3.Row
    sql = (
        "SELECT * FROM metric_store "
        "WHERE scope_type = ? AND scope_id = ? AND category = ?"
    )
    params: list[Any] = [scope_type, str(scope_id), category]

    if primary_only:
        sql += " AND is_primary = 1"

    rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def get_metric_history(
    conn: sqlite3.Connection,
    metric_name: str,
    *,
    scope_type: str = "daily",
    provider: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    primary_only: bool = True,
) -> list[dict]:
    """메트릭 시계열 조회 (주로 일별 추세)."""
    conn.row_factory = sqlite3.Row
    clauses = ["scope_type = ?", "metric_name = ?"]
    params: list[Any] = [scope_type, metric_name]

    if provider:
        clauses.append("provider = ?")
        params.append(provider)
    elif primary_only:
        clauses.append("is_primary = 1")

    if date_from:
        clauses.append("scope_id >= ?")
        params.append(date_from)
    if date_to:
        clauses.append("scope_id <= ?")
        params.append(date_to)

    where = " AND ".join(clauses)
    rows = conn.execute(
        f"SELECT * FROM metric_store WHERE {where} ORDER BY scope_id",
        params,
    ).fetchall()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
# daily_wellness (Layer 1)
# ─────────────────────────────────────────────────────────────────────────────

_WELLNESS_COLUMNS = [
    "date", "sleep_score", "sleep_duration_sec", "sleep_start_time",
    "hrv_weekly_avg", "hrv_last_night", "resting_hr",
    "body_battery_high", "body_battery_low", "avg_stress",
    "steps", "active_calories", "weight_kg",
]


def upsert_daily_wellness(conn: sqlite3.Connection, data: dict) -> int:
    """daily_wellness UPSERT. UNIQUE(date) 기준. Merge 전략: NULL만 채움."""
    date_val = data.get("date")
    if not date_val:
        raise ValueError("daily_wellness requires 'date'")

    existing = conn.execute(
        "SELECT * FROM daily_wellness WHERE date = ?",
        (date_val,),
    ).fetchone()

    if existing:
        # Merge: 기존 NULL인 필드만 새 값으로 채움
        col_names = [desc[0] for desc in conn.execute("PRAGMA table_info(daily_wellness)").fetchall()]
        col_names = [d[1] for d in conn.execute("PRAGMA table_info(daily_wellness)").fetchall()]
        existing_dict = dict(zip(col_names, existing))

        updates = {}
        for col in _WELLNESS_COLUMNS:
            if col == "date":
                continue
            new_val = data.get(col)
            if new_val is not None and existing_dict.get(col) is None:
                updates[col] = new_val

        if updates:
            set_clause = ", ".join(f"{k} = ?" for k in updates)
            set_clause += ", updated_at = datetime('now')"
            conn.execute(
                f"UPDATE daily_wellness SET {set_clause} WHERE date = ?",
                list(updates.values()) + [date_val],
            )

        return existing_dict["id"]
    else:
        cols = [c for c in _WELLNESS_COLUMNS if c in data]
        vals = [data[c] for c in cols]
        placeholders = ", ".join("?" * len(cols))
        cur = conn.execute(
            f"INSERT INTO daily_wellness ({', '.join(cols)}) VALUES ({placeholders})",
            vals,
        )
        return cur.lastrowid


# ─────────────────────────────────────────────────────────────────────────────
# daily_fitness (Layer 1)
# ─────────────────────────────────────────────────────────────────────────────

def upsert_daily_fitness(
    conn: sqlite3.Connection,
    date: str,
    source: str,
    *,
    ctl: float | None = None,
    atl: float | None = None,
    tsb: float | None = None,
    ramp_rate: float | None = None,
    vo2max: float | None = None,
) -> int:
    """daily_fitness UPSERT. UNIQUE(date, source) 기준."""
    sql = """
        INSERT INTO daily_fitness (date, source, ctl, atl, tsb, ramp_rate, vo2max)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(date, source) DO UPDATE SET
            ctl = COALESCE(excluded.ctl, ctl),
            atl = COALESCE(excluded.atl, atl),
            tsb = COALESCE(excluded.tsb, tsb),
            ramp_rate = COALESCE(excluded.ramp_rate, ramp_rate),
            vo2max = COALESCE(excluded.vo2max, vo2max),
            updated_at = datetime('now')
    """
    cur = conn.execute(sql, (date, source, ctl, atl, tsb, ramp_rate, vo2max))
    row = conn.execute(
        "SELECT id FROM daily_fitness WHERE date = ? AND source = ?",
        (date, source),
    ).fetchone()
    return row[0]


# ─────────────────────────────────────────────────────────────────────────────
# DB Status (검증/디버깅)
# ─────────────────────────────────────────────────────────────────────────────

def get_db_status(conn: sqlite3.Connection) -> dict:
    """DB 요약 통계 반환."""
    status = {}

    # 테이블별 행 수
    for table in [
        "source_payloads", "activity_summaries", "daily_wellness",
        "daily_fitness", "metric_store", "activity_streams",
        "activity_laps", "activity_best_efforts", "gear",
        "weather_cache", "sync_jobs",
    ]:
        try:
            row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
            status[f"{table}_count"] = row[0]
        except Exception:
            status[f"{table}_count"] = -1

    # metric_store provider 분포
    try:
        rows = conn.execute(
            "SELECT provider, COUNT(*) FROM metric_store GROUP BY provider"
        ).fetchall()
        status["metric_providers"] = {r[0]: r[1] for r in rows}
    except Exception:
        status["metric_providers"] = {}

    # metric_store unmapped 비율
    try:
        total = status.get("metric_store_count", 0)
        unmapped = conn.execute(
            "SELECT COUNT(*) FROM metric_store WHERE category = '_unmapped'"
        ).fetchone()[0]
        status["unmapped_ratio"] = unmapped / total if total > 0 else 0
    except Exception:
        status["unmapped_ratio"] = 0

    # primary 무결성 (같은 scope+name에 is_primary=1이 2개 이상인 경우)
    try:
        violations = conn.execute(
            "SELECT COUNT(*) FROM ("
            "  SELECT scope_type, scope_id, metric_name, SUM(is_primary) AS pc "
            "  FROM metric_store GROUP BY scope_type, scope_id, metric_name "
            "  HAVING pc > 1"
            ")"
        ).fetchone()[0]
        status["primary_violations"] = violations
    except Exception:
        status["primary_violations"] = -1

    return status

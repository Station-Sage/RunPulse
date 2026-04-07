"""Phase 5 서비스 레이어 - 웰니스 데이터 조회.

읽기 전용. DB 쓰기 없음.
첫 번째 인자는 sqlite3.Connection.
반환값은 dict/list (snake_case 키, 단위 변환 없음).

설계 문서: v0.3/data/phase-5-impl/01-service-layer.md
"""
from __future__ import annotations

import sqlite3
from collections import defaultdict
from typing import Any

from src.utils import db_helpers
from src.utils.metric_registry import get_metric

_WELLNESS_CATEGORIES = (
    "sleep", "stress", "hrv", "readiness", "wellness",
    "rp_readiness", "rp_risk", "rp_recovery",
)

_TREND_WELLNESS_COLS = (
    "sleep_score", "hrv_last_night", "resting_hr",
    "body_battery_high", "avg_stress", "weight_kg",
)


def get_wellness_detail(conn: sqlite3.Connection, date: str | None = None) -> dict:
    """웰니스 상세: core + metrics_by_category + readiness_summary.

    date: 'YYYY-MM-DD'. None이면 오늘.
    """
    conn.row_factory = sqlite3.Row

    if date is None:
        date = conn.execute("SELECT date('now')").fetchone()[0]

    # core
    core_row = conn.execute(
        "SELECT * FROM daily_wellness WHERE date = ?", (date,)
    ).fetchone()
    core = dict(core_row) if core_row else {}

    # metrics_by_category (is_primary=1, wellness 관련 카테고리)
    placeholders = ",".join("?" * len(_WELLNESS_CATEGORIES))
    metric_rows = conn.execute(
        f"SELECT metric_name, category, numeric_value, text_value, json_value,"
        f"       provider, confidence"
        f" FROM metric_store"
        f" WHERE scope_type = 'daily' AND scope_id = ? AND is_primary = 1"
        f"   AND category IN ({placeholders})"
        f" ORDER BY category, metric_name",
        (date, *_WELLNESS_CATEGORIES),
    ).fetchall()

    grouped: dict[str, list] = defaultdict(list)
    for row in metric_rows:
        metric_name = row["metric_name"]
        meta = get_metric(metric_name)
        entry = {
            "metric_name": metric_name,
            "numeric_value": row["numeric_value"],
            "text_value": row["text_value"],
            "json_value": row["json_value"],
            "provider": row["provider"],
            "confidence": row["confidence"],
            "unit": meta.unit if meta else "",
            "description": meta.description if meta else "",
        }
        grouped[row["category"]].append(entry)
    metrics_by_category = dict(grouped)

    # readiness_summary (utrs, cirs)
    readiness_summary: dict[str, Any] = {}
    for metric_name in ("utrs", "cirs"):
        row = db_helpers.get_primary_metric(conn, "daily", date, metric_name)
        if row:
            readiness_summary[metric_name] = {
                "value": row.get("numeric_value"),
                "confidence": row.get("confidence"),
            }
        else:
            readiness_summary[metric_name] = None

    return {
        "date": date,
        "core": core,
        "metrics_by_category": metrics_by_category,
        "readiness_summary": readiness_summary,
    }


def get_wellness_trend(conn: sqlite3.Connection, days: int = 30) -> dict:
    """웰니스 시계열.

    반환: {"dates": [...], "sleep_score": [...], "hrv_last_night": [...], ...}
    날짜 기준 정렬. 데이터 없는 날짜는 null.
    """
    conn.row_factory = sqlite3.Row
    date_expr = f"-{days} days"

    # daily_wellness 행 조회
    wellness_rows = conn.execute(
        "SELECT date, sleep_score, hrv_last_night, resting_hr,"
        "       body_battery_high, avg_stress, weight_kg"
        " FROM daily_wellness"
        " WHERE date >= date('now', ?)"
        " ORDER BY date",
        (date_expr,),
    ).fetchall()

    # utrs 시계열 (metric_store)
    utrs_rows = conn.execute(
        "SELECT scope_id AS date, numeric_value"
        " FROM metric_store"
        " WHERE scope_type = 'daily'"
        "   AND metric_name = 'utrs'"
        "   AND is_primary = 1"
        "   AND scope_id >= date('now', ?)"
        " ORDER BY scope_id",
        (date_expr,),
    ).fetchall()
    utrs_map = {r["date"]: r["numeric_value"] for r in utrs_rows}

    # 날짜 유니온
    dates_set: set[str] = set()
    wellness_map: dict[str, dict] = {}
    for row in wellness_rows:
        d = row["date"]
        dates_set.add(d)
        wellness_map[d] = dict(row)
    dates_set.update(utrs_map.keys())

    dates = sorted(dates_set)

    result: dict[str, list] = {"dates": dates}
    for col in _TREND_WELLNESS_COLS:
        result[col] = [wellness_map.get(d, {}).get(col) for d in dates]
    result["utrs"] = [utrs_map.get(d) for d in dates]

    return result

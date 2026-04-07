"""Phase 5 서비스 레이어 - 대시보드 데이터 조회.

읽기 전용. DB 쓰기 없음.
첫 번째 인자는 sqlite3.Connection.
반환값은 dict/list (snake_case 키, 단위 변환 없음).

설계 문서: v0.3/data/phase-5-impl/01-service-layer.md
"""
from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from typing import Any

from src.utils import db_helpers

# ─────────────────────────────────────────────────────────────────────────────
# 내부 헬퍼
# ─────────────────────────────────────────────────────────────────────────────

_LEVEL_THRESHOLDS: dict[str, list[tuple[float, str]]] = {
    # (최소값, 레이블) — 내림차순으로 첫 번째 매칭 사용
    "utrs":  [(80, "매우 좋음"), (65, "양호"), (50, "보통"), (35, "낮음")],
    "crs":   [(80, "매우 좋음"), (65, "양호"), (50, "보통"), (35, "낮음")],
    "cirs":  [(50, "매우 높음"), (35, "높음"), (20, "보통"), (10, "낮음")],
}
_DEFAULT_LEVEL = "매우 낮음"


def _interpret_level(metric_name: str, value: float | None) -> str | None:
    """메트릭 값을 레이블로 변환."""
    if value is None:
        return None
    thresholds = _LEVEL_THRESHOLDS.get(metric_name, [])
    for min_val, label in thresholds:
        if value >= min_val:
            return label
    return _DEFAULT_LEVEL


def _get_training_phase(tsb: float | None, ramp_rate: float | None) -> str:
    """TSB + ramp_rate 기반 훈련 단계 판단."""
    if tsb is None and ramp_rate is None:
        return "unknown"
    tsb = tsb or 0.0
    ramp_rate = ramp_rate or 0.0
    if tsb > 15:
        return "tapering"
    if tsb > 5:
        return "recovering"
    if ramp_rate > 3:
        return "building"
    if ramp_rate < -3:
        return "detraining"
    return "maintaining"


# ─────────────────────────────────────────────────────────────────────────────
# 공개 함수
# ─────────────────────────────────────────────────────────────────────────────

def get_dashboard_data(conn: sqlite3.Connection, date: str | None = None) -> dict:
    """대시보드 전체 데이터.

    date: 기준일 'YYYY-MM-DD'. None이면 오늘.
    """
    conn.row_factory = sqlite3.Row

    if date is None:
        date_row = conn.execute("SELECT date('now')").fetchone()
        date = date_row[0]

    # wellness
    wellness_row = conn.execute(
        "SELECT * FROM daily_wellness WHERE date = ?", (date,)
    ).fetchone()
    wellness = dict(wellness_row) if wellness_row else {}

    # readiness
    readiness: dict[str, Any] = {}
    for metric_name in ("utrs", "cirs", "crs"):
        row = db_helpers.get_primary_metric(conn, "daily", date, metric_name)
        if row:
            value = row.get("numeric_value")
            entry: dict[str, Any] = {
                "value": value,
                "level": _interpret_level(metric_name, value),
            }
            if row.get("json_value"):
                try:
                    entry["components"] = json.loads(row["json_value"])
                except (ValueError, TypeError):
                    pass
            if row.get("confidence") is not None:
                entry["confidence"] = row["confidence"]
            readiness[metric_name] = entry
        else:
            readiness[metric_name] = None

    # training_status
    pmc_metrics = db_helpers.get_primary_metrics(
        conn, "daily", date,
        names=["ctl", "atl", "tsb", "ramp_rate", "acwr"],
    )
    pmc_map = {r["metric_name"]: r.get("numeric_value") for r in pmc_metrics}

    tsb = pmc_map.get("tsb")
    ramp_rate = pmc_map.get("ramp_rate")
    training_status = {
        "ctl": pmc_map.get("ctl"),
        "atl": pmc_map.get("atl"),
        "tsb": tsb,
        "ramp_rate": ramp_rate,
        "acwr": pmc_map.get("acwr"),
        "training_phase": _get_training_phase(tsb, ramp_rate),
    }

    # recent_activities (최근 5개)
    recent_rows = conn.execute(
        "SELECT id, name, start_time, distance_m, duration_sec"
        " FROM v_canonical_activities"
        " ORDER BY start_time DESC LIMIT 5"
    ).fetchall()
    recent_activities = [dict(r) for r in recent_rows]

    # race_predictions (daily scope, 실제 metric_name에 _sec 접미사)
    pred_names = ["darp_5k_sec", "darp_10k_sec", "darp_half_sec", "darp_marathon_sec"]
    pred_rows = db_helpers.get_primary_metrics(conn, "daily", date, names=pred_names)
    pred_map = {r["metric_name"]: r.get("numeric_value") for r in pred_rows}
    race_predictions = {
        "darp_5k":       pred_map.get("darp_5k_sec"),
        "darp_10k":      pred_map.get("darp_10k_sec"),
        "darp_half":     pred_map.get("darp_half_sec"),
        "darp_marathon": pred_map.get("darp_marathon_sec"),
    }

    # weekly_summary
    weekly_row = conn.execute(
        "SELECT COUNT(*) AS run_count,"
        "       SUM(distance_m) AS total_distance_m,"
        "       SUM(duration_sec) AS total_duration_sec"
        " FROM v_canonical_activities"
        " WHERE activity_type = 'running'"
        "   AND start_time >= date(?, '-7 days')",
        (date,),
    ).fetchone()

    if weekly_row and weekly_row["run_count"]:
        total_dist = weekly_row["total_distance_m"] or 0
        total_dur = weekly_row["total_duration_sec"] or 0
        avg_pace = (total_dur / (total_dist / 1000)) if total_dist > 0 else None
        weekly_summary = {
            "run_count": weekly_row["run_count"],
            "total_distance_m": total_dist,
            "total_duration_sec": total_dur,
            "avg_pace_sec_km": avg_pace,
        }
    else:
        weekly_summary = {
            "run_count": 0,
            "total_distance_m": 0.0,
            "total_duration_sec": 0,
            "avg_pace_sec_km": None,
        }

    return {
        "date": date,
        "wellness": wellness,
        "readiness": readiness,
        "training_status": training_status,
        "recent_activities": recent_activities,
        "race_predictions": race_predictions,
        "weekly_summary": weekly_summary,
    }


def get_pmc_chart_data(conn: sqlite3.Connection, days: int = 90) -> list[dict]:
    """ctl/atl/tsb 시계열 (metric_store daily). date별 pivot.

    반환: [{"date": str, "ctl": float|None, "atl": float|None, "tsb": float|None}, ...]
    """
    conn.row_factory = sqlite3.Row
    date_expr = f"-{days} days"
    rows = conn.execute(
        "SELECT scope_id AS date, metric_name, numeric_value"
        " FROM metric_store"
        " WHERE scope_type = 'daily'"
        "   AND metric_name IN ('ctl', 'atl', 'tsb')"
        "   AND is_primary = 1"
        "   AND scope_id >= date('now', ?)"
        " ORDER BY scope_id",
        (date_expr,),
    ).fetchall()

    pivoted: dict[str, dict] = defaultdict(lambda: {"ctl": None, "atl": None, "tsb": None})
    for row in rows:
        pivoted[row["date"]][row["metric_name"]] = row["numeric_value"]

    return [{"date": d, **vals} for d, vals in sorted(pivoted.items())]


def get_daily_metric_chart(
    conn: sqlite3.Connection,
    metric_name: str,
    days: int = 30,
) -> list[dict]:
    """일별 메트릭 시계열 (is_primary=1).

    반환: [{"date": str, "value": float}, ...]
    """
    conn.row_factory = sqlite3.Row
    date_expr = f"-{days} days"
    rows = conn.execute(
        "SELECT scope_id AS date, numeric_value AS value"
        " FROM metric_store"
        " WHERE scope_type = 'daily'"
        "   AND metric_name = ?"
        "   AND is_primary = 1"
        "   AND scope_id >= date('now', ?)"
        " ORDER BY scope_id",
        (metric_name, date_expr),
    ).fetchall()
    return [dict(r) for r in rows]

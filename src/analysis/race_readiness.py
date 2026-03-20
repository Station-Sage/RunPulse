"""레이스 준비도 분석."""

from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime

from .efficiency import efficiency_trend
from .recovery import get_recovery_status
from .trends import calculate_acwr


def _safe_float(value):
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_date(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def _clamp(value, low=0.0, high=100.0):
    return max(low, min(high, value))


def _grade(score: float) -> str:
    if score >= 85:
        return "A"
    if score >= 70:
        return "B"
    if score >= 55:
        return "C"
    if score >= 40:
        return "D"
    return "F"


def _latest_daily(conn: sqlite3.Connection, source: str, column: str):
    try:
        row = conn.execute(
            f"""
            SELECT {column}
            FROM daily_fitness
            WHERE source = ? AND {column} IS NOT NULL
            ORDER BY date DESC
            LIMIT 1
            """,
            (source,),
        ).fetchone()
    except sqlite3.OperationalError:
        return None
    return row[0] if row else None


def _latest_metric(conn: sqlite3.Connection, source: str, metric_name: str):
    try:
        row = conn.execute(
            """
            SELECT metric_value, metric_json
            FROM source_metrics
            WHERE source = ? AND metric_name = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (source, metric_name),
        ).fetchone()
    except sqlite3.OperationalError:
        return None
    if not row:
        return None
    value, metric_json = row
    if value is not None:
        return value
    return metric_json


def _fitness_score(ctl) -> float | None:
    ctl = _safe_float(ctl)
    if ctl is None:
        return None
    return round(_clamp(ctl * 2.0), 1)


def _vo2max_score(vo2max) -> float | None:
    vo2 = _safe_float(vo2max)
    if vo2 is None:
        return None
    return round(_clamp((vo2 - 34.0) * 4.5), 1)


def _freshness_score(tsb) -> float | None:
    tsb = _safe_float(tsb)
    if tsb is None:
        return None
    score = 100.0 - abs(tsb - 5.0) * (40.0 / 13.0)
    return round(_clamp(score), 1)


def _recovery_score(conn: sqlite3.Connection) -> float | None:
    try:
        result = get_recovery_status(conn)
    except Exception:
        return None
    if not result:
        return None
    return _safe_float(result.get("recovery_score"))


def _efficiency_score(conn: sqlite3.Connection) -> float | None:
    try:
        trend = efficiency_trend(conn, weeks=4)
    except Exception:
        return None
    if not trend:
        return None

    values = []
    for item in trend:
        value = _safe_float(item.get("avg_decoupling_pct"))
        if value is not None:
            values.append(value)

    if not values:
        return None

    avg_decoupling = sum(values) / len(values)
    return round(_clamp(100.0 - avg_decoupling * 8.0), 1)


def _acwr_score(conn: sqlite3.Connection) -> float | None:
    try:
        acwr = calculate_acwr(conn)
    except Exception:
        return None

    if not acwr or not isinstance(acwr, dict):
        return None

    avg = acwr.get("average") or {}
    value = _safe_float(avg.get("acwr"))
    if value is None:
        return None

    diff = abs(value - 1.0)
    return round(_clamp(100.0 - diff * 120.0), 1)


def _race_predictions_from_metric(conn: sqlite3.Connection):
    raw = _latest_metric(conn, "runalyze", "race_prediction")
    if not raw or not isinstance(raw, str):
        return None
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(parsed, dict):
        return None

    result = {}
    if "5k" in parsed:
        result["5k"] = int(parsed["5k"])
    if "10k" in parsed:
        result["10k"] = int(parsed["10k"])
    if "half" in parsed:
        result["half"] = int(parsed["half"])
    if "full" in parsed:
        result["full"] = int(parsed["full"])
    if "marathon" in parsed and "full" not in result:
        result["full"] = int(parsed["marathon"])
    return result or None


def vdot_race_predictions(vdot):
    v = _safe_float(vdot)
    if v is None or v <= 0:
        return None

    five_k = max(900, int(round(1800 - (v - 30) * 29)))
    ten_k = int(round(five_k * 2.08))
    half = int(round(ten_k * 2.21))
    full = int(round(half * 2.09))

    return {
        "5k": five_k,
        "10k": ten_k,
        "half": half,
        "full": full,
    }


def _coverage_meta(available_count: int) -> tuple[str, str, str | None]:
    if available_count >= 4:
        return "high", "high", None
    if available_count == 3:
        return "enough", "medium", None
    if available_count == 2:
        return (
            "low",
            "low",
            "충분한 데이터가 쌓이지 않았습니다. 최근 3~4주 이상 데이터를 누적해 주세요.",
        )
    if available_count == 1:
        return (
            "low",
            "low",
            "충분한 데이터가 쌓이지 않았습니다. 최근 3~4주 이상 데이터를 누적해 주세요.",
        )
    return (
        "low",
        "low",
        "충분한 데이터가 쌓이지 않았습니다. 최근 3~4주 이상 데이터를 누적해 주세요.",
    )


def _is_insufficient_data(scores: dict) -> bool:
    available = [v for v in scores.values() if v is not None]
    return len(available) < 3


def assess_race_readiness(
    conn: sqlite3.Connection,
    race_date=None,
    race_distance_km=None,
    config=None,
) -> dict:
    race_day = _parse_date(race_date)
    days_to_race = (race_day - date.today()).days if race_day else None

    ctl = _safe_float(_latest_daily(conn, "intervals", "ctl"))
    atl = _safe_float(_latest_daily(conn, "intervals", "atl"))
    tsb = _safe_float(_latest_daily(conn, "intervals", "tsb"))

    vo2max = _safe_float(_latest_daily(conn, "garmin", "garmin_vo2max"))
    if vo2max is None:
        vo2max = _safe_float(_latest_daily(conn, "runalyze", "runalyze_evo2max"))

    vdot = _safe_float(_latest_daily(conn, "runalyze", "runalyze_vdot"))
    marathon_shape = _safe_float(_latest_daily(conn, "runalyze", "runalyze_marathon_shape"))

    scores = {
        "vo2max_score": _vo2max_score(vo2max),
        "fitness_score": _fitness_score(ctl),
        "acwr_score": _acwr_score(conn),
        "recovery_score": _recovery_score(conn),
        "efficiency_score": _efficiency_score(conn),
        "freshness_score": _freshness_score(tsb),
    }

    available_scores = [v for v in scores.values() if v is not None]
    available_count = len(available_scores)
    data_sufficiency, confidence, warning = _coverage_meta(available_count)
    insufficient = _is_insufficient_data(scores)

    if insufficient:
        readiness_score = None
        grade = None
        status = "insufficient_data"
    else:
        base = sum(available_scores) / len(available_scores)
        readiness_score = round(_clamp(base), 1)
        grade = _grade(readiness_score)
        status = "ok"

    recommendations = []
    if insufficient:
        recommendations.append(
            "레이스 준비도는 최근 훈련 추세와 회복 흐름이 함께 있어야 정확하게 평가할 수 있습니다. 최근 3~4주 이상 데이터를 누적한 뒤 다시 확인해 주세요."
        )
    else:
        if scores["fitness_score"] is not None and scores["fitness_score"] < 55:
            recommendations.append("기초 체력이 아직 부족합니다. 무리한 강도보다 기본 유산소를 우선하세요.")
        if scores["freshness_score"] is not None and scores["freshness_score"] < 55:
            recommendations.append("신선도가 낮습니다. 휴식이나 이지런으로 피로를 조절하세요.")
        if scores["recovery_score"] is not None and scores["recovery_score"] < 55:
            recommendations.append("회복 상태가 낮습니다. 수면과 휴식을 먼저 챙기세요.")
        if scores["acwr_score"] is not None and scores["acwr_score"] < 60:
            recommendations.append("최근 훈련 부하 균형이 좋지 않습니다. 급격한 증가를 피하세요.")
        if days_to_race is not None and 0 <= days_to_race <= 14:
            recommendations.append("레이스가 가까우니 테이퍼링과 컨디션 유지에 집중하세요.")
        if readiness_score is not None and readiness_score >= 80:
            recommendations.append("현재 준비도가 좋습니다. 무리한 추가 훈련보다 컨디션 유지가 중요합니다.")
        if not recommendations:
            recommendations.append("현재 상태를 유지하면서 규칙적으로 훈련을 이어가세요.")

    recommendation = " ".join(recommendations)

    race_predictions = _race_predictions_from_metric(conn)
    if race_predictions is None:
        race_predictions = vdot_race_predictions(vdot)

    return {
        "race_date": race_day.isoformat() if race_day else None,
        "race_distance_km": _safe_float(race_distance_km),
        "days_to_race": days_to_race,
        "status": status,
        "readiness_score": readiness_score,
        "grade": grade,
        "scores": scores,
        "metrics": {
            "vo2max": vo2max,
            "vdot": vdot,
            "ctl": ctl,
            "atl": atl,
            "tsb": tsb,
            "marathon_shape": marathon_shape,
        },
        "race_predictions": race_predictions,
        "recommendation": recommendation,
        "recommendations": recommendations,
        "data_sufficiency": data_sufficiency,
        "confidence": confidence,
        "warning": warning,
    }

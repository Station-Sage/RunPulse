from __future__ import annotations

"""Garmin 일별 확장 API — race_predictions, training_status, fitness_metrics,
user_summary, heart_rates."""

import json
import sqlite3
from typing import TYPE_CHECKING

from src.sync.garmin_helpers import _store_raw_payload, _upsert_daily_detail_metric

if TYPE_CHECKING:
    from garminconnect import Garmin


def sync_daily_race_predictions(
    conn: sqlite3.Connection,
    client: "Garmin",
    date_str: str,
) -> None:
    """Garmin 레이스 예측 시간 → daily_detail_metrics."""
    try:
        data = client.get_race_predictions()
    except Exception as e:
        print(f"[garmin] race_predictions 실패 {date_str}: {e}")
        return

    if not data:
        return

    _store_raw_payload(conn, "race_predictions", date_str, data)

    predictions = data if isinstance(data, dict) else {}
    metrics = {
        "race_pred_5k_sec": predictions.get("time5K"),
        "race_pred_10k_sec": predictions.get("time10K"),
        "race_pred_half_sec": predictions.get("timeHalfMarathon"),
        "race_pred_marathon_sec": predictions.get("timeMarathon"),
    }
    for k, v in metrics.items():
        if v is not None:
            try:
                _upsert_daily_detail_metric(conn, date_str, k, metric_value=float(v))
            except (TypeError, ValueError):
                pass


def sync_daily_training_status(
    conn: sqlite3.Connection,
    client: "Garmin",
    date_str: str,
) -> None:
    """Garmin 훈련 상태/ATL/CTL → daily_fitness + daily_detail_metrics."""
    try:
        data = client.get_training_status(date_str)
    except Exception as e:
        print(f"[garmin] training_status 실패 {date_str}: {e}")
        return

    if not data:
        return

    _store_raw_payload(conn, "training_status_day", date_str, data)

    atl_dto = data.get("acuteTrainingLoadDTO") or {}
    atl = atl_dto.get("acuteTrainingLoad")
    ctl = (
        atl_dto.get("chronicTrainingLoad")
        or atl_dto.get("longTermTrainingLoad")
    )
    acwr = atl_dto.get("acuteChronicTrainingLoadRatio")
    training_status_val = (
        data.get("trainingStatus") or data.get("mostRecentTrainingStatus")
    )
    fitness_trend = (
        data.get("fitnessTrend") or data.get("mostRecentFitnessTrend")
    )

    if atl is not None or ctl is not None:
        try:
            conn.execute(
                """INSERT INTO daily_fitness (date, source, atl, ctl)
                   VALUES (?, 'garmin', ?, ?)
                   ON CONFLICT(date, source) DO UPDATE SET
                       atl = COALESCE(excluded.atl, atl),
                       ctl = COALESCE(excluded.ctl, ctl),
                       updated_at = datetime('now')""",
                (date_str, atl, ctl),
            )
        except sqlite3.OperationalError:
            pass

    if acwr is not None:
        try:
            _upsert_daily_detail_metric(
                conn, date_str, "garmin_acwr", metric_value=float(acwr)
            )
        except (TypeError, ValueError):
            pass

    if training_status_val is not None:
        _upsert_daily_detail_metric(
            conn, date_str, "garmin_training_status_label",
            metric_json=json.dumps({"value": training_status_val}),
        )
    if fitness_trend is not None:
        _upsert_daily_detail_metric(
            conn, date_str, "garmin_fitness_trend",
            metric_json=json.dumps({"value": fitness_trend}),
        )


def sync_daily_fitness_metrics(
    conn: sqlite3.Connection,
    client: "Garmin",
    date_str: str,
) -> None:
    """Garmin endurance_score, hill_score, fitnessage, lactate_threshold 저장."""
    # Endurance Score
    try:
        es = client.get_endurance_score(date_str)
        if es:
            _store_raw_payload(conn, "endurance_score_day", date_str, es)
            score = es.get("overallScore") or es.get("enduranceScore")
            if score is not None:
                _upsert_daily_detail_metric(
                    conn, date_str, "garmin_endurance_score",
                    metric_value=float(score),
                )
    except Exception:
        pass

    # Hill Score
    try:
        hs = client.get_hill_score(date_str, date_str)
        if hs:
            _store_raw_payload(conn, "hill_score_day", date_str, hs)
            if isinstance(hs, dict):
                score = hs.get("overallScore") or hs.get("hillScore")
            elif isinstance(hs, list) and hs:
                score = hs[0].get("overallScore")
            else:
                score = None
            if score is not None:
                _upsert_daily_detail_metric(
                    conn, date_str, "garmin_hill_score", metric_value=float(score)
                )
    except Exception:
        pass

    # Fitness Age
    try:
        fa = client.get_fitnessage(date_str, date_str)
        if fa:
            _store_raw_payload(conn, "fitnessage_day", date_str, fa)
            if isinstance(fa, dict):
                age = fa.get("achievableFitnessAge") or fa.get("fitnessAge")
            elif isinstance(fa, list) and fa:
                age = fa[0].get("achievableFitnessAge")
            else:
                age = None
            if age is not None:
                _upsert_daily_detail_metric(
                    conn, date_str, "garmin_fitness_age", metric_value=float(age)
                )
    except Exception:
        pass

    # Lactate Threshold (글로벌 값 — 날짜별 API 없음, 당일 date_str로 저장)
    try:
        lt = client.get_lactate_threshold()
        if lt:
            _store_raw_payload(conn, "lactate_threshold_day", date_str, lt)
            ftp = lt.get("functionalThresholdPower")
            lthr_dto = lt.get("lactateThresholdHeartRate") or {}
            lthr = lthr_dto.get("heartRate") or lt.get("heartRate")
            if ftp is not None:
                _upsert_daily_detail_metric(
                    conn, date_str, "garmin_ftp", metric_value=float(ftp)
                )
            if lthr is not None:
                _upsert_daily_detail_metric(
                    conn, date_str, "garmin_lthr", metric_value=float(lthr)
                )
    except Exception:
        pass


def sync_daily_user_summary(
    conn: sqlite3.Connection,
    client: "Garmin",
    date_str: str,
) -> None:
    """Garmin user_summary (94키) → daily_wellness 보완 + daily_detail_metrics."""
    try:
        data = client.get_user_summary(date_str)
    except Exception as e:
        print(f"[garmin] user_summary 실패 {date_str}: {e}")
        return

    if not data:
        return

    _store_raw_payload(conn, "user_summary_day", date_str, data)

    # daily_wellness에 누락 컬럼 COALESCE 보완
    wellness_updates = {
        "steps": data.get("totalSteps") or data.get("steps"),
        "spo2_avg": data.get("averageSpo2") or data.get("avgSpo2"),
        "respiration_avg": (
            data.get("avgWakingRespirationValue")
            or data.get("averageRespirationValue")
        ),
        "intensity_min_moderate": data.get("moderateIntensityMinutes"),
        "intensity_min_vigorous": data.get("vigorousIntensityMinutes"),
    }
    non_null = {k: v for k, v in wellness_updates.items() if v is not None}
    if non_null:
        set_clause = ", ".join(
            f"{col} = COALESCE({col}, ?)" for col in non_null
        )
        try:
            conn.execute(
                f"UPDATE daily_wellness SET {set_clause} "
                "WHERE date = ? AND source = 'garmin'",
                (*non_null.values(), date_str),
            )
        except sqlite3.OperationalError:
            pass

    # daily_detail_metrics 추가 필드
    extra: dict[str, object] = {
        "body_battery_highest": data.get("bodyBatteryHighestValue"),
        "body_battery_lowest": data.get("bodyBatteryLowestValue"),
        "body_battery_charged_summary": data.get("bodyBatteryChargedValue"),
        "total_kilocalories": data.get("totalKilocalories"),
        "active_kilocalories": data.get("activeKilocalories"),
        "bmr_kilocalories": data.get("bmrKilocalories"),
        "total_distance_meters": data.get("totalDistanceMeters"),
        "highly_active_seconds": data.get("highlyActiveSeconds"),
        "active_seconds": data.get("activeSeconds"),
        "sedentary_seconds": data.get("sedentarySeconds"),
        "sleeping_seconds": data.get("sleepingSeconds"),
        "avg_stress_level": data.get("averageStressLevel"),
        "max_stress_level": data.get("maxStressLevel"),
        "stress_duration": data.get("stressDuration"),
        "rest_stress_duration": data.get("restStressDuration"),
        "floors_ascended": (
            data.get("floorsAscended") or data.get("floorsAscendedInMeters")
        ),
        "floors_descended": (
            data.get("floorsDescended") or data.get("floorsDescendedInMeters")
        ),
    }
    for k, v in extra.items():
        if v is not None:
            try:
                _upsert_daily_detail_metric(
                    conn, date_str, k, metric_value=float(v)
                )
            except (TypeError, ValueError):
                pass


def sync_daily_all_day_stress(
    conn: sqlite3.Connection,
    client: "Garmin",
    date_str: str,
) -> None:
    """Garmin 24시간 스트레스 타임라인 → daily_detail_metrics (전체 배열 보완 저장)."""
    try:
        data = client.get_all_day_stress(date_str)
    except Exception:
        return

    if not data:
        return

    _store_raw_payload(conn, "all_day_stress_day", date_str, data)

    avg = data.get("avgStressLevel") or data.get("averageStressLevel")
    stress_vals = data.get("stressValuesArray") or []

    if avg is not None:
        try:
            _upsert_daily_detail_metric(
                conn, date_str, "all_day_stress_avg", metric_value=float(avg)
            )
        except (TypeError, ValueError):
            pass

    if stress_vals:
        _upsert_daily_detail_metric(
            conn, date_str, "all_day_stress_timeline",
            metric_json=json.dumps(stress_vals),
        )


def sync_daily_body_battery_events(
    conn: sqlite3.Connection,
    client: "Garmin",
    date_str: str,
) -> None:
    """Garmin body battery 이벤트 (충전/방전) → daily_detail_metrics."""
    try:
        data = client.get_body_battery_events(date_str, date_str)
    except Exception:
        return

    if not data:
        return

    _store_raw_payload(conn, "body_battery_events_day", date_str, data)

    events = data if isinstance(data, list) else data.get("events", [])
    if events:
        _upsert_daily_detail_metric(
            conn, date_str, "body_battery_events",
            metric_json=json.dumps(events),
        )


def sync_daily_heart_rates(
    conn: sqlite3.Connection,
    client: "Garmin",
    date_str: str,
) -> None:
    """Garmin 일중 HR 타임라인 → daily_detail_metrics."""
    try:
        data = client.get_heart_rates(date_str)
    except Exception:
        return

    if not data:
        return

    _store_raw_payload(conn, "heart_rates_day", date_str, data)

    hr_values = data.get("heartRateValues") or []
    if not hr_values:
        return

    valid = [
        pair[1] for pair in hr_values
        if len(pair) > 1 and pair[1] is not None and pair[1] > 0
    ]
    if valid:
        _upsert_daily_detail_metric(
            conn, date_str, "hr_max_daily", metric_value=float(max(valid))
        )
        _upsert_daily_detail_metric(
            conn, date_str, "hr_min_daily", metric_value=float(min(valid))
        )
        _upsert_daily_detail_metric(
            conn, date_str, "hr_avg_daily",
            metric_value=round(sum(valid) / len(valid), 1),
        )
    _upsert_daily_detail_metric(
        conn, date_str, "heart_rates_timeline",
        metric_json=json.dumps(hr_values),
    )

"""Garmin 랩(lapDTOs)·스트림 확장 필드 — 예측 리뉴얼(P7-PRED-12)에서 보존하는 값."""
from __future__ import annotations

# Garmin details(metricDescriptors) key → activity_streams 컬럼. 기존 direct* 매핑보다 우선.
STREAM_KEY_ALIASES = {
    "elapsed_sec": ("sumElapsedDuration", "directElapsedDuration"),
    "distance_m": ("sumDistance", "directDistance"),
    "gap_speed_ms": ("directGradeAdjustedSpeed",),
}

# 러닝 다이내믹스 등 보조 스트림 — Garmin details key → activity_streams 컬럼(원본 단위)
STREAM_EXTRA_KEYS = {
    "ground_contact_ms": ("directGroundContactTime",),
    "vertical_osc_cm": ("directVerticalOscillation",),
    "stride_length_cm": ("directStrideLength",),
    "vertical_ratio_pct": ("directVerticalRatio",),
    "body_battery": ("directBodyBattery",),
    "respiration_rate": ("directRespirationRate",),
}


def lap_extras(lap: dict) -> dict:
    """lapDTO → activity_laps 확장 컬럼(None 은 제외)."""
    out = {
        "gap_speed_ms": lap.get("avgGradeAdjustedSpeed"),
        "elevation_loss": lap.get("elevationLoss"),
        "avg_temperature_c": lap.get("averageTemperature"),
        "elapsed_duration_sec": lap.get("elapsedDuration"),
        "moving_duration_sec": lap.get("movingDuration"),
        "compliance_score": lap.get("directWorkoutComplianceScore"),
        "wkt_step_index": lap.get("wktStepIndex"),
        "avg_ground_contact_ms": lap.get("groundContactTime"),
        "avg_vertical_osc_cm": lap.get("verticalOscillation"),
        "avg_stride_length_cm": lap.get("strideLength"),
        "avg_vertical_ratio_pct": lap.get("verticalRatio"),
        "normalized_power": lap.get("normalizedPower"),
        "avg_respiration_rate": lap.get("avgRespirationRate"),
    }
    return {k: v for k, v in out.items() if v is not None}


def pick(metrics, idx_map: dict[str, int], keys: tuple[str, ...]):
    """스트림 한 점(metrics: list 또는 dict)에서 keys 순서대로 첫 값."""
    for k in keys:
        if isinstance(metrics, dict):
            if metrics.get(k) is not None:
                return metrics[k]
            continue
        pos = idx_map.get(k)
        if pos is not None and pos < len(metrics) and metrics[pos] is not None:
            return metrics[pos]
    return None

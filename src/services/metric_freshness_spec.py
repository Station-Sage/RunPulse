"""메트릭별 신선도 입력 명세 (ADR-050) — 어떤 wellness 컬럼·선행 메트릭에 의존하는지 선언.

metric_freshness.assess 가 이 표만 읽는다. 메트릭을 추가하면 여기에 항목을 더한다.
wellness_role: component(구성요소, 오래되면 stale) | modifier(보정, 나이로 stale 안 됨) | gate(문턱, 불명이면 gate_unknown).
component_map: row.json_value 의 구성요소/신호 키 → daily_wellness 컬럼 (누락 입력 이름을 구하는 데 쓴다).
"""
from __future__ import annotations

STALE_DAYS = 2
PARTIAL_CONFIDENCE = 0.5

FRESHNESS_SPEC: dict[str, dict] = {
    "utrs": {
        "wellness": ["body_battery_high", "sleep_score", "hrv_weekly_avg", "avg_stress"],
        "metrics": ["tsb"], "wellness_role": "component",
        "component_map": {"body_battery": "body_battery_high", "sleep": "sleep_score",
                          "hrv": "hrv_weekly_avg", "stress": "avg_stress"},
    },
    "rmr": {
        "wellness": ["resting_hr", "body_battery_high", "sleep_score"],
        "metrics": ["tsb"], "wellness_role": "component", "min_version": "1.1",
        "component_map": {"resting_hr": "resting_hr", "body_battery": "body_battery_high",
                          "sleep": "sleep_score"},
    },
    "rtti": {
        "wellness": ["body_battery_high", "sleep_score"],
        "metrics": ["atl", "ctl"], "wellness_role": "modifier", "min_version": "1.1",
    },
    "crs": {
        "wellness": ["body_battery_high", "hrv_weekly_avg"],
        "metrics": ["acwr", "tsb", "cirs"], "upstream": ["utrs"],
        "wellness_role": "gate", "min_version": "1.1",
        "signal_map": {"body_battery": "body_battery_high", "hrv_today": "hrv_weekly_avg"},
    },
}

WELLNESS_LABELS = {
    "body_battery_high": "바디배터리", "sleep_score": "수면 점수",
    "hrv_weekly_avg": "HRV", "avg_stress": "스트레스", "resting_hr": "안정시 심박",
}

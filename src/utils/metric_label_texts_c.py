"""지표 한 줄 설명 2차분(M-07) — 상세 화면에 설명이 비던 지표. 문구는 TXT-1 확정.

40자 이내 한 문장, 계산식이 아닌 '무엇을 재는지'만 쓴다. 행동 힌트는 두지 않는다.
metric_labels.py가 import 시 METRIC_LABELS의 description_short에 합친다(이미 있으면 덮지 않음).
"""
from __future__ import annotations

TEXTS_C: dict[str, str] = {
    "training_response": "역치 이상으로 달린 주간 시간(분)과 그 추세",
    "rec": "같은 심박에서 얼마나 빠르게 달리는지 본 러닝 효율",
    "sapi": "기온 등 계절 조건을 감안한 최근 성과 수준",
    "critical_power": "오래 유지할 수 있는 러닝 파워의 상한 추정",
    "eftp": "약 1시간 버틸 수 있는 역치 페이스 추정",
    "lt_speed_ref": "기기가 측정·추정한 젖산역치 속도",
    "garmin_ftp": "Garmin이 추정한 러닝 기능적 역치 파워",
    "sleep_deep_sec": "지난밤 깊은 수면 시간",
    "sleep_light_sec": "지난밤 얕은 수면 시간",
    "sleep_rem_sec": "지난밤 렘(REM) 수면 시간",
    "sleep_awake_sec": "잠든 뒤 깨어 있던 시간",
    "sleep_avg_hr": "수면 중 평균 심박 — 평소보다 높으면 회복 부족 신호",
    "sleep_body_battery_change": "수면 동안 충전된 바디 배터리 양",
    "avg_spo2": "수면 중 평균 혈중 산소포화도",
    "min_spo2": "수면 중 가장 낮았던 혈중 산소포화도",
    "skin_temp_deviation": "수면 중 피부 온도의 평소 대비 차이(°C)",
    "steps": "하루 걸음 수",
    "active_calories": "운동·활동으로 쓴 하루 칼로리",
    "avg_respiration_sleep": "수면 중 1분당 평균 호흡수",
    "min_respiration_sleep": "수면 중 1분당 가장 낮은 호흡수",
    "lthr_self": "내 기록으로 추정한 젖산역치 심박",
    "hrmax_self": "내 기록으로 추정한 최대 심박",
    "hrv_5min_high": "지난밤 5분 구간 중 가장 높았던 심박변이도",
    "lthr_ref": "기기가 측정·추정한 젖산역치 심박",
    "hrmax_ref": "기기에 설정·추정된 최대 심박",
    "heat_model": "기온 1℃ 변화에 따른 페이스 변화 비율 추정",
    "hrv_status": "Garmin 심박변이도 상태(균형·낮음 등)",
    "weight_kg": "기록된 체중",
}

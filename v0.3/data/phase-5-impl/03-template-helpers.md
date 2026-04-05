# Phase 5 Template Helpers 설계

> UI와 AI context에서 공통으로 사용하는 포맷/해석 함수.
> Jinja2 전역 함수로도 등록 가능하고, Python에서 직접 호출도 가능.

## 파일: src/web/template_helpers.py

## 단위 변환 함수

### format_distance(meters, unit="km", decimals=2) -> str

    10020.0 → "10.02km"
    None → ""

### format_pace(sec_per_km) -> str

    312.5 → "5:13"
    None → ""
    0 → ""

### format_duration(seconds) -> str

    3735 → "1:02:15"  (1시간 이상: HH:MM:SS)
    735 → "12:15"     (1시간 미만: MM:SS)
    None → ""

### format_speed(ms, unit="km/h") -> str

    3.2 → "11.5km/h"

### format_time_prediction(seconds) -> str

    6135 → "1:42:15"
    레이스 예측 시간 전용. format_duration과 동일 포맷.

### format_metric(metric_name, value, unit=None) -> str

    metric_registry에서 단위 조회 후 적절히 포맷.
    - unit이 "sec/km" → format_pace(value)
    - unit이 "sec" 이고 prediction 카테고리 → format_time_prediction(value)
    - unit이 "sec" → format_duration(value)
    - 기타 → "{value}{unit}"

## 메트릭 해석 함수

### interpret_metric_level(metric_name, value) -> str

    metric_dictionary의 범위 해석 테이블 사용.
    "utrs", 72.3 → "양호"
    "cirs", 28.1 → "낮음"
    "acwr", 1.05 → "최적"

내부 데이터 구조 (metric_dictionary에서 추출):

    METRIC_LEVELS = {
        "utrs": [(30, "미흡"), (50, "낮음"), (70, "보통"), (85, "양호"), (100, "우수")],
        "cirs": [(30, "낮음"), (50, "보통"), (70, "높음"), (100, "위험")],
        "acwr": [(0.8, "낮음"), (1.3, "최적"), (1.5, "주의"), (5.0, "위험")],
        "lsi": [(1.3, "정상"), (1.5, "상승"), (10.0, "급증")],
        "monotony": [(1.5, "다양함"), (2.0, "보통"), (10.0, "단조로움")],
        "di": [(30, "미흡"), (50, "보통"), (70, "양호"), (100, "우수")],
        "rmr": [(30, "미흡"), (50, "낮음"), (70, "보통"), (85, "양호"), (100, "우수")],
        "rec": [(30, "미흡"), (50, "보통"), (70, "양호"), (100, "우수")],
        "rri": [(40, "부족"), (60, "상승 중"), (80, "준비됨"), (100, "피크")],
        "marathon_shape": [(30, "부족"), (50, "기초"), (70, "상승 중"), (85, "준비됨"), (100, "피크")],
        "crs": [(20, "휴식"), (40, "가벼운 운동만"), (60, "보통"), (80, "전면 훈련"), (100, "고강도 가능")],
        "rtti": [(70, "여유"), (100, "최적"), (130, "과부하"), (300, "위험")],
        "sapi": [(85, "미흡"), (100, "정상"), (150, "양호")],
        "teroi": [(0, "음수"), (5, "낮음"), (15, "양호"), (100, "우수")],
        "tpdi": [(5, "일관됨"), (10, "보통"), (100, "큰 격차")],
        "adti": [(-10, "하락"), (10, "안정"), (100, "상승 중")],
        "runpulse_vdot": [(35, "초보"), (50, "중급"), (60, "상급"), (85, "엘리트")],
        "vdot_adj": [(35, "초보"), (45, "중급"), (55, "상급"), (85, "엘리트")],
        "aerobic_decoupling_rp": [(5, "우수"), (10, "양호"), (15, "보통"), (100, "미흡")],
        "trimp": [(50, "회복"), (100, "쉬운 강도"), (200, "보통"), (350, "높은 강도"), (999, "매우 높은 강도")],
        "relative_effort": [(50, "낮음"), (100, "보통"), (200, "높음"), (999, "매우 높음")],
        "wlei": [(50, "낮음"), (100, "보통"), (200, "높음"), (999, "매우 높음")],
        "eftp": [(210, "엘리트"), (260, "상급"), (320, "중급"), (600, "초보")],
        "critical_power": [(200, "낮음"), (280, "보통"), (500, "높음")],
    }

내부 함수:

    def _find_level(levels, value):
        for threshold, label in levels:
            if value <= threshold:
                return label
        return levels[-1][1]

## Higher/Lower 판단

    HIGHER_IS_BETTER = {
        True:  utrs, crs, rmr, di, rec, rri, marathon_shape, vdot_adj,
               sapi, runpulse_vdot, teroi, adti, critical_power,
               efficiency_factor_rp, trimp, relative_effort, wlei, hrss
        False: cirs, eftp, gap_rp, fearp, lsi, monotony, tpdi,
               aerobic_decoupling_rp
        None:  acwr, rtti (범위형 — 최적 구간이 중간에 있음)
    }

## Badge/Color 함수

### metric_level_color(metric_name, value) -> str

    해석 등급에 따른 CSS 색상 클래스.
    "우수"/"양호"/"최적" → "green"
    "보통"/"정상" → "yellow"
    "미흡"/"높음"/"위험"/"과부하" → "red"
    "낮음" → HIGHER_IS_BETTER에 따라 다름
        HIGHER_IS_BETTER=True이면 "낮음" → "red"
        HIGHER_IS_BETTER=False이면 "낮음" → "green"

### confidence_badge(confidence) -> str

    0.8 이상 → "높음"
    0.5~0.8 → "보통"
    0.5 미만 → "낮음"
    None → ""

### provider_badge(provider) -> str

    "runpulse:formula_v1" → "RunPulse"
    "runpulse:rule_v1" → "RunPulse"
    "garmin" → "Garmin"
    "strava" → "Strava"
    "intervals" → "Intervals.icu"
    "runalyze" → "Runalyze"
    "user" → "사용자"
    그 외 → provider 그대로

### metric_display_name(metric_name) -> str

    metric_registry에서 description 조회.
    "utrs" → "Unified Training Readiness Score"
    없으면 metric_name 그대로 반환.

### metric_unit(metric_name) -> str

    metric_registry에서 unit 조회.
    "utrs" → "점"
    없으면 "" 반환.

## template_helpers.py DoD

- [ ] format_distance: m→km 변환 정확, 소수점 제어
- [ ] format_pace: 0, None, 극단값 안전 처리
- [ ] format_duration: 1시간 미만 MM:SS, 1시간 이상 HH:MM:SS
- [ ] interpret_metric_level: metric_dictionary의 범위 해석 커버 (METRIC_LEVELS에 등록된 모든 메트릭)
- [ ] HIGHER_IS_BETTER: metric_dictionary의 "해석" 필드와 일치
- [ ] metric_level_color: HIGHER_IS_BETTER에 따라 색상 방향 반전
- [ ] confidence_badge, provider_badge: 유효한 문자열 반환
- [ ] metric_display_name, metric_unit: registry 조회, 미등록 시 fallback

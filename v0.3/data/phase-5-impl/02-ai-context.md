# Phase 5 AI Context Builder 설계

> AI 코칭이 새 스키마에서 컨텍스트를 빌드하는 모듈.
> 서비스 레이어 함수를 호출하여 markdown 형태의 컨텍스트를 생성한다.

## 원칙

1. AI context는 서비스 레이어만 호출 (직접 SQL 없음)
2. 출력은 markdown 문자열 (LLM 프롬프트에 삽입)
3. 메트릭 값 옆에 반드시 해석을 포함 ("UTRS 72 — 양호")
4. 해석은 metric_dictionary의 범위 테이블 사용
5. 숫자의 근거(어떤 소스, 어떤 공식)를 투명하게 표시

## 파일: src/ai/ai_context.py

### build_daily_briefing

시그니처:

    def build_daily_briefing(conn, date: str = None) -> str:

서비스 레이어에서 데이터를 가져와 LLM에 전달할 daily briefing 생성.
반환: markdown string.

호출하는 서비스:

    dashboard_service.get_dashboard_data(conn, date)

사용하는 헬퍼:

    template_helpers.format_distance
    template_helpers.format_pace
    template_helpers.format_duration
    template_helpers.format_time_prediction
    template_helpers.interpret_metric_level

출력 예시:

    ## 오늘의 상태 (2026-04-04)

    ### 훈련 준비도
    - UTRS: 72.3점 (양호) — 수면 85, HRV 비율 1.08, TSB +5.2, 바디배터리 78, 스트레스 32
    - CIRS: 28.1점 (낮은 위험) — ACWR 1.05 (최적), LSI 0.9 (정상)
    - CRS: Level 3 (전면 훈련 가능)

    ### 체력 상태
    - CTL: 45.2 (만성 부하)
    - ATL: 52.1 (급성 부하)
    - TSB: -6.9 (약간 피로)
    - 추세: 체력 상승 중 (ramp_rate +2.3)

    ### 수면
    - 수면 점수: 82 | 수면 시간: 7시간 12분
    - HRV: 지난밤 42ms (주간평균 39ms, +7.7%)

    ### 레이스 예측 (DARP)
    - 5K: 22:15 | 10K: 46:30 | 하프: 1:42:10 | 풀: 3:35:00

    ### 최근 활동
    - 어제: 오후 달리기 10.2km, 52분, 페이스 5:05/km, TRIMP 91

구현 패턴:

    data = get_dashboard_data(conn, date)
    lines = []

    readiness = data.get("readiness", {})
    utrs = readiness.get("utrs", {})
    if utrs.get("value") is not None:
        level = interpret_metric_level("utrs", utrs["value"])
        lines.append(f"- UTRS: {utrs['value']}점 ({level})")

    ... 나머지 섹션도 동일한 패턴

    return "\n".join(lines)

None 처리: 메트릭 값이 None이면 해당 줄을 출력하지 않는다.

### build_activity_analysis

시그니처:

    def build_activity_analysis(conn, activity_id: int) -> str:

반환: markdown string.

호출하는 서비스:

    activity_service.get_activity_detail(conn, activity_id)

출력 예시:

    ## 활동 분석: 오후 달리기 (2026-04-03)

    ### 기본 정보
    - 거리: 10.02km | 시간: 52분 15초 | 페이스: 5:13/km
    - 평균 심박: 155bpm | 최대: 178bpm
    - 고도: +120m / -115m | 기온: 18°C

    ### RunPulse 분석
    - TRIMP: 91.2 (보통~높은 강도)
    - 유산소 분리: 3.2% (우수 — 후반부 효율 유지)
    - GAP: 5:08/km (경사 보정 시 더 빠름)
    - FEARP: 5:05/km (환경 보정 페이스)
    - 운동 유형: tempo (confidence 0.78)
    - VDOT: 48.2 (중급)

    ### 소스 비교
    | 지표 | Garmin | Strava | RunPulse |
    |------|--------|--------|----------|
    | 거리 | 10.02km | 10.05km | — |
    | Training Load | 52 | — | HRSS 95.1 |
    | TRIMP | — | — | 91.2 |

구현 패턴:

    detail = get_activity_detail(conn, activity_id)
    core = detail["core"]
    metrics = detail["metrics_by_category"]
    comparison = detail["source_comparison"]
    groups = detail["semantic_groups"]

    기본 정보: core에서 format_distance, format_pace, format_duration 사용
    RunPulse 분석: metrics에서 rp_* 카테고리 순회, interpret_metric_level 사용
    소스 비교: comparison + groups에서 테이블 생성

## ai_context.py DoD

- [ ] build_daily_briefing: 서비스 레이어만 호출, 직접 SQL 없음
- [ ] 모든 메트릭 값에 해석 포함 (metric_dictionary 범위 테이블 기준)
- [ ] build_activity_analysis: core + RP 분석 + 소스 비교 포함
- [ ] 숫자 포맷: 거리 km, 페이스 MM:SS/km, 시간 HH:MM:SS (template_helpers 사용)
- [ ] None 메트릭은 표시하지 않음 (빈 줄 없이)

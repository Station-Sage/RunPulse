"""도구 사용 가이드 — MCP initialize의 instructions로 전달되는 호출 레시피.

목적은 호출당 토큰이 아니라 호출 '횟수'를 줄이는 것: 질문 유형별로 어떤 도구 1~2회로
끝나는지를 고정해 광범위 스캔을 막는다. 세션 시작 시 1회 전달되므로 짧게 유지한다
(tests/test_ai_tool_guide.py가 길이 상한과 도구 누락을 검사).
"""

MAX_GUIDE_CHARS = 1400

USAGE_GUIDE = """RunPulse 러닝 데이터 도구 규칙 (호출 횟수·토큰 절약)
- 목록 응답은 {"fields":[...],"rows":[[...]]}. rows의 각 행은 fields 순서. 없는 컬럼은 생략됨.
- 62일 초과 구간은 주별(week=일요일 시작)로 자동 집계. 일별이 필요하면 짧게 지정하고 granularity=day.
- 날짜·id를 모르면 먼저 get_training_summary로 좁힌 뒤 id로 상세를 본다. 같은 데이터를 반복 조회 금지.
질문 → 도구
- 최근 N주/훈련 블록/대회 이후 → get_training_summary (1회로 볼륨·CTL/TSB·주요 세션 id)
- 몸 상태(수면·HRV·BB) → get_wellness (14일 이내 권장)
- 피트니스 추이 → get_fitness
- 특정 날 러닝 → get_activity(date), 기간 목록 → get_activities_range
- 인터벌·크루즈 세트별 → get_activity_laps(id), 세션 간 세트 비교 → compare_workout_sets
- km 스플릿·HR존 → get_activity_detail(id)
- 대회 이력 → get_race_history, 두 기간 비교 → compare_periods
- 메트릭 → get_metrics(날짜)/get_metrics_trend, 계획·프로필·날씨 → get_training_plan/get_runner_profile/get_weather
"""

# RunPulse - 파일별 역할

## 진입점 (src 루트)
- db_setup.py: SQLite 테이블 생성, 마이그레이션
- sync.py: 데이터 동기화 CLI 진입점 (--source --days)
- analyze.py: 분석 리포트 CLI 진입점 (today|week|month|compare|trends|deep|race|full)
- plan.py: 훈련 계획 및 목표 CLI 진입점
- serve.py: Flask 웹서버 실행
- import_history.py: GPX/FIT 파일 일괄 파싱 및 DB 삽입

## DB 스키마 주요 테이블
- activity_summaries: 4소스 활동 통합 (matched_group_id, avg_power, export_filename, workout_label 포함)
- source_metrics: activity 단위 소스별 고유 지표 (training_load, icu_hrss, trimp 등)
- daily_wellness: 날짜별 수면/HRV/Body Battery/스트레스
- daily_fitness: 날짜별 피트니스 추적 지표 (CTL/ATL/TSB, VO2Max, VDOT, marathon_shape)
- daily_detail_metrics: Garmin 일별 상세 지표 (training_readiness, overnight_hrv_avg, spo2 등)
- planned_workouts: 계획된 운동 (source, ai_model, garmin_workout_id 포함)
- goals: 레이스 목표
- shoes: 신발 목록 (name, brand, model, distance_km, retired, added_at)
- sync_jobs: 백그라운드 동기화 작업 이력 (job_id, source, status, started_at, finished_at, rows_added, error)
- source_payloads: 4소스 raw API 응답 보존 (source, entity_type, payload JSON)

## sync 모듈 (src/sync/)
- garmin.py: GarminConnect 세션 관리, 활동/웰니스 가져오기, DB 저장
- strava.py: OAuth 토큰 갱신, 활동/스트림 가져오기, 스트림은 JSON 파일로 저장
- intervals.py: Basic Auth로 활동/웰니스(CTL/ATL/TSB/Zone분포) 가져오기
- runalyze.py: API 토큰으로 활동/VO2Max/VDOT/Marathon Shape/Race Prediction 가져오기

## analysis 모듈 (src/analysis/)
- compare.py: 두 기간 비교. 거리/시간/페이스/HR + 4소스 고유 지표 변화량/변화율
- trends.py: N주 롤링 추세, ACWR 부상 위험도 (Garmin TL, Strava RE, Intervals HRSS, Runalyze TRIMP 교차)
- recovery.py: Garmin Body Battery/HRV/Sleep/Stress 기반 회복 점수 및 추세
- weekly_score.py: 볼륨/강도분포/ACWR/회복/EF/일관성 종합 Training Quality Score 0-100
- efficiency.py: Strava stream 1초 데이터로 Aerobic EF/Cardiac Decoupling 계산, 주별 추세
- zones_analysis.py: HR zone 분포 분석, 80/20 법칙 준수 판정 (stream > intervals > avg_hr 폴백)
- activity_deep.py: 4소스 통합 단일 활동 심층 — 1km pace splits, fitness/recovery context
- race_readiness.py: 레이스 준비도 종합 (Garmin VO2Max + Runalyze EffVO2Max/VDOT/Marathon Shape + Intervals TSB)
- report.py: 마크다운 리포트 포맷팅 (인간 읽기용 + AI 컨텍스트용 이중 출력)

## training 모듈 (src/training/)
- goals.py: 목표 SQLite CRUD, 목표 페이스 자동 계산
- planner.py: 주간/월간 훈련 스케줄 생성
- adjuster.py: 당일 컨디션 점수 계산, 계획 상향/하향 조정

## ai 모듈 (src/ai/)
- ai_context.py: 분석 데이터를 AI 프롬프트 컨텍스트로 변환 (상세 분석 요청용)
- ai_schema.py: AI 훈련 계획 JSON 스키마 정의 및 jsonschema 검증
- ai_parser.py: AI 응답 텍스트에서 JSON 블록 추출, 스키마 검증, 파싱
- briefing.py: AI 코치 탭 진입 시 자동 브리핑 (오늘/이번주 데이터 수집 → 프롬프트 조립)
- suggestions.py: 추천 칩 생성 (RunnerState 기반 규칙 + AI 응답 suggestions 파싱 하이브리드)
- prompt_templates/: 프롬프트 템플릿 텍스트 파일 디렉터리

### prompt_templates/ 파일
- briefing.txt: AI 코치 탭 진입 시 자동 브리핑 프롬프트
- deep_analysis.txt: 단일 활동 심층 분석 요청
- pace_strategy.txt: 페이스 전략 평가 요청
- rest_advice.txt: 휴식 적절성 판단 요청
- tomorrow_rec.txt: 내일 훈련 추천 요청
- race_predict.txt: 레이스 예측 및 준비도 분석 요청
- plan_request.txt: 주간 훈련 스케줄 생성 요청 (JSON 출력 지시 포함)
- deload_plan.txt: 디로딩 계획 요청
- zone_review.txt: 강도 분포 분석 요청
- taper_check.txt: 테이퍼링 점검 요청

## workout 모듈 (src/workout/)
- workout_builder.py: AI JSON → Garmin RunningWorkout Typed Model 변환
- garmin_calendar.py: 워크아웃 업로드 → 캘린더 스케줄 → 삭제 (슬롯 우회)
- workout_export.py: 워크아웃 JSON/YAML 내보내기

## utils 모듈 (src/utils/)
- api.py: httpx 기반 GET/POST 래퍼, 재시도, 에러 처리
- config.py: config.json 로드/저장/부분업데이트/마스킹 유틸리티
- pace.py: 초를 "분:초/km"로, km/h를 sec/km로 변환
- zones.py: 5존 HR 계산 (max_hr 기반), 페이스 존 계산 (threshold_pace 기반)
- dedup.py: 중복 활동 매칭 (허용오차 7분·15%), auto_group_all() 전이적 그룹 병합
- clipboard.py: termux-clipboard-set 호출 래퍼
- sync_policy.py: SyncPolicy/SyncGuardResult — rate limit·cooldown·중복 방지, sync_state.json 관리

## services 모듈 (src/services/)
- unified_activities.py: 멀티소스 활동 병합·비교·그룹관리 서비스
  - `fetch_unified_activities()`: sort_by/sort_dir/q/min_max_dist/pace/dur 필터 지원
  - `build_unified_activity()`: 그룹 또는 단독 활동 → UnifiedActivity 변환
  - `build_source_comparison()`: 소스별 수치 비교 테이블 생성
  - `assign_group_to_activities()` / `remove_from_group()`: 수동 그룹 관리

## import_export 모듈 (src/import_export/)
- garmin_csv.py: Garmin 내보내기 CSV 파싱 → activity_summaries 삽입 (수영 거리 m→km 변환)
- strava_csv.py: Strava 내보내기 CSV 파싱 → activity_summaries 삽입

## web 모듈 (src/web/)
- app.py: Flask Blueprint 등록, 홈 대시보드, DB/sync-status/payloads 라우트
- helpers.py: html_page, make_table, fmt_min, fmt_duration, readiness_badge, connected_services()
- sync_ui.py: _source_checkboxes() pill-style 멀티셀렉트 (미연결 서비스 disabled)
- views_wellness.py: /wellness Blueprint — Garmin 회복·웰니스 카드 + 14일 추세
- views_activity.py: /activity/deep Blueprint — 단일 활동 심층 분석 (생체역학·HR존·소스별 메트릭)
- views_activities.py: /activities Blueprint — 활동 목록 (정렬·검색·범위필터·페이지네이션)
- views_activity_merge.py: /activities/merge-group·/activities/remove-from-group — 수동 그룹 관리
- views_export_import.py: /export-import Blueprint — CSV 임포트/내보내기 탭
- views_shoes.py: /shoes Blueprint — 신발 목록·누적거리·은퇴 처리
- views_settings.py: /settings·/connect/* Blueprint — 4개 서비스 연동 설정 UI
- views_sync.py: 백그라운드 기간 동기화 UI (진행 프로그레스바, SSE polling)

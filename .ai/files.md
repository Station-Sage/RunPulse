# RunPulse - 파일별 역할

## 진입점 (src 루트)
- db_setup.py: SQLite 테이블 생성, 마이그레이션
- sync.py: 데이터 동기화 CLI 진입점 (--source --days)
- analyze.py: 분석 리포트 CLI 진입점 (today|week|month|compare|trends|deep|race|full)
- plan.py: 훈련 계획 및 목표 CLI 진입점
- serve.py: Flask 웹서버 실행
- import_history.py: GPX/FIT 파일 일괄 파싱 및 DB 삽입

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
- efficiency.py: Strava Stream 1초 데이터로 Aerobic EF(Pace/HR) 및 Cardiac Decoupling 계산
- zones_analysis.py: Intervals.icu HR/Pace Zone 분포 분석, 80/20 법칙 준수 판정
- activity_deep.py: 단일 활동 심층 (km별 스플릿, 디커플링, 존분포, 4소스 평가 병합)
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
- config.py: config.json 로드 유틸리티
- pace.py: 초를 "분:초/km"로, km/h를 sec/km로 변환
- zones.py: 5존 HR 계산 (max_hr 기반), 페이스 존 계산 (threshold_pace 기반)
- dedup.py: 중복 활동 매칭 함수
- clipboard.py: termux-clipboard-set 호출 래퍼

## web 모듈 (src/web/)
- app.py: Flask 라우트 정의 (대시보드, AI 코치, 훈련 계획 탭)
- templates/: HTML 파일들 (대시보드, AI 코치 채팅, 훈련 계획, 활동 상세)
- static/: CSS, JS (추천 칩 플로팅, 채팅 UI, 차트)

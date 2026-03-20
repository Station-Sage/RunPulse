# RunPulse - 작업 목록
최종 업데이트: 2026-03-21

## Phase 1: 기반 구축 (완료)
- [x] P1-1: 디렉터리 구조 및 문서 생성
- [x] P1-2: db_setup.py - SQLite 스키마 생성
- [x] P1-3: src/utils/pace.py - 페이스 변환 함수
- [x] P1-4: src/utils/zones.py - HR존 및 Pace존 계산
- [x] P1-5: src/utils/dedup.py - 중복 활동 매칭
- [x] P1-6: src/utils/clipboard.py - termux-clipboard-set 래퍼
- [x] P1-7: config.json.example 생성
- [x] P1-8: tests/ 기본 테스트 작성

## Phase 2: 데이터 수집 (완료)
- [x] P2-1: src/sync/garmin.py - Garmin Connect 활동/웰니스
- [x] P2-2: src/sync/strava.py - Strava OAuth2 활동/스트림
- [x] P2-3: src/sync/intervals.py - Intervals.icu 활동/CTL/ATL/TSB
- [x] P2-4: src/sync/runalyze.py - Runalyze 활동/VO2Max/Race Prediction
- [x] P2-5: src/sync.py - CLI 진입점
- [x] P2-6: src/import_history.py - GPX/FIT 일괄 임포트
- [x] P2-7: 중복 매칭 통합 테스트

## Phase 1-2 수정 (완료)
- [x] FIX-1: db_setup.py - daily_fitness 테이블 신설, planned_workouts 컬럼 추가, migrate_db()
- [x] FIX-2: garmin.py - aerobic/anaerobic TE 분리, VO2Max→daily_fitness, sync_garmin() 래퍼
- [x] FIX-3: strava.py - best_efforts 수집, cadence*2 확인
- [x] FIX-4: intervals.py - CTL/ATL/TSB→daily_fitness 이관, HR Zone TODO 주석
- [x] FIX-5: runalyze.py - marathon_shape, race_prediction 수집, daily_fitness 연동
- [x] FIX-6: compare.py - daily_fitness 기반 CTL/ATL/TSB/VO2Max 비교 (source_metrics 폴백)
- [x] FIX-7: trends.py - fitness_trend() daily_fitness 우선 참조 (source_metrics 폴백)
- [x] FIX-8: 테스트 144개 전체 통과 (신규 21개 포함)

## Phase 3: 분석 리포트 (완료)

### Sprint 3-1: 핵심 분석 기반
- [x] P3-1: src/analysis/compare.py - 기간 비교 (오늘vs어제, 이번주vs지난주, 월간, 연간)
- [x] P3-2: src/analysis/trends.py - 주간 추세, ACWR 부상 위험도 (4개 소스 부하 교차 검증)
- [x] P3-3: src/analysis/recovery.py - Garmin Body Battery/HRV/Sleep/Stress 기반 회복 상태 평가
- [x] P3-4: src/analysis/weekly_score.py - 주간 Training Quality Score (0-100 종합 점수)

### Sprint 3-2: 심층 분석
- [x] P3-5: src/analysis/efficiency.py - Aerobic EF (Pace/HR) + Cardiac Decoupling (Strava Stream 활용)
- [x] P3-6: src/analysis/zones_analysis.py - HR/Pace Zone 분포, 80/20 법칙 준수 여부 판정
- [x] P3-7: src/analysis/activity_deep.py - 단일 활동 심층 분석 (스플릿, 디커플링, 존분포, 4소스 평가 병합)

### Sprint 3-3: 레이스 & 리포트
- [x] P3-8: src/analysis/race_readiness.py - 레이스 준비도 (VO2Max추세, VDOT, Marathon Shape, TSB 종합)
- [x] P3-9: src/analysis/report.py - 마크다운 리포트 포맷팅 (인간용 + AI 컨텍스트용 이중 출력)
- [x] P3-10: src/analyze.py - CLI 진입점 (today|week|month|compare|trends|deep|race|full --clipboard --save)

## Phase 4: 훈련 계획 및 목표
- [x] P4-1: src/training/goals.py - 목표 CRUD (레이스명, 날짜, 거리, 목표 시간)
- [x] P4-2: src/training/planner.py - 주간/월간 훈련 계획 생성
- [x] P4-3: src/training/adjuster.py - 컨디션 기반 당일 계획 조정
- [x] P4-4: src/plan.py - CLI 진입점

## Phase 4-1: AI 코치 연동
- [ ] P4-1-1: src/ai/ai_context.py - 분석 데이터를 AI 프롬프트 컨텍스트로 변환
- [ ] P4-1-2: src/ai/ai_schema.py - AI 훈련 계획 JSON 스키마 정의 및 검증
- [ ] P4-1-3: src/ai/ai_parser.py - AI 응답에서 훈련 계획 JSON 추출 및 파싱
- [ ] P4-1-4: src/ai/briefing.py - AI 코치 탭 진입 시 자동 브리핑 (오늘/이번주 데이터 수집 + 프롬프트 조립)
- [ ] P4-1-5: src/ai/suggestions.py - 추천 칩 생성 (규칙 기반 + AI 응답 파싱 하이브리드)
- [ ] P4-1-6: src/ai/prompt_templates/ - 프롬프트 템플릿 파일들 (briefing, deep_analysis, race_predict 등 10종)

## Phase 4-2: 가민 워크아웃 캘린더
- [ ] P4-2-1: src/workout/workout_builder.py - AI JSON을 Garmin Typed Workout 모델로 변환
- [ ] P4-2-2: src/workout/garmin_calendar.py - 워크아웃 업로드 → 캘린더 스케줄 → 삭제 (25개 슬롯 우회)
- [ ] P4-2-3: src/workout/workout_export.py - 워크아웃 JSON/YAML 내보내기

## Phase 5: 웹 대시보드
- [x] P5-1: src/serve.py + src/web/app.py - Flask 경량 서버/workbench 기본 구현 완료
- [x] P5-2: 대시보드 홈 (오늘 회복 요약 카드, 주간 점수 카드, 최근 활동 + 심층 링크) — `app.py` 홈 라우트 개선
- [x] P5-garmin-wellness: /wellness 라우트 — Garmin daily detail 카드 뷰 (training readiness, HRV, 수면, SpO2, body battery 등) + 14일 추세 테이블
- [x] P5-activity-deep: /activity/deep 라우트 — 단일 활동 심층 카드 뷰 (garmin_daily_detail + 4소스 메트릭 + 페이스 스플릿)
- [x] P5-activities: /activities 라우트 — 활동 목록 탭 (소스/유형/날짜 필터, 페이지네이션, 심층 링크)
- [x] P5-wellness-steps: /wellness 체중/걸음수 카드 추가 (intervals daily_wellness 소스)
- [ ] P5-3: AI 코치 탭 (브리핑 자동 표시, 채팅 인터페이스, 추천 칩 플로팅, 붙여넣기 입력창)
- [ ] P5-4: 훈련 계획 탭 (AI 생성 계획 승인/수정 UI, 캘린더 뷰, 가민 푸시 버튼)
- [ ] P5-5: 설정 탭 - 서비스 연동 (Garmin SSO 팝업, Strava OAuth2 자동화, Intervals API Key, Runalyze Token)
- [ ] P5-6: 설정 탭 - 사용자 프로필 (max_hr, threshold_pace, 주간 목표, 레이스 목표)
- [ ] P5-7: 모바일 반응형 HTML + 다크 모드

## Phase 6: 고도화
- [ ] P6-1: AI 코치 다중 프로바이더 (Genspark, ChatGPT, Claude, DeepSeek 교체 가능)
- [ ] P6-2: iframe DOM 자동 감지로 AI 응답 자동 수집 (방법 1 확장)
- [ ] P6-3: AI 코치 대화 이력 저장 및 검색
- [ ] P6-4: cron 자동 동기화 (termux-job-scheduler)
- [ ] P6-5: termux-notification 알림 연동

## 완료 기록
- 2026-03-18: Phase 1 전체 완료 (P1-1 ~ P1-8), 45개 테스트
- 2026-03-18: Phase 2 전체 완료 (P2-1 ~ P2-7), 68개 테스트
- 2026-03-19: Phase 3 확장 설계, Phase 4-1/4-2 분리, AI 코치 브리핑/추천칩 설계
- 2026-03-19: Sprint 3-1 완료 (P3-1 ~ P3-4), 58개 테스트 신규 추가 (누적 103개)
- 2026-03-20: Phase 1-2 스키마 확장 및 sync 개선 완료 (FIX-1~FIX-8), 테스트 144개 통과
- 2026-03-20: Sprint 3-2 완료 (P3-5 ~ P3-7), 신규 테스트 39개 추가 (누적 183개)
- 2026-03-20: Phase 4 완료 (P4-1 ~ P4-4) — 목표 CRUD, 규칙 기반 주간 계획, 컨디션 조정, plan.py CLI
- 2026-03-21: Phase 5 UI 1차 완료 — /wellness, /activity/deep 라우트 신설, 홈 대시보드 개선, 신규 테스트 38개 (누적 304개)
- 2026-03-21: Phase 5 UI 2차 완료 — /activities 탭 신설, /wellness 체중/걸음수 카드, 전체 테스트 316개 통과

- [ ] P3-followup: 레이스 준비도 데이터 부족 시 grade/readiness_score를 None으로 전환하고 "충분한 데이터가 쌓이지 않았습니다" 안내 중심 UX로 개선

- [x] P3-8: 레이스 준비도 분석 추가 (race_readiness.py)
- [x] P3-9: 마크다운 리포트 및 AI 컨텍스트 생성 추가 (report.py)
- [x] P3-10: analyze.py CLI 엔트리포인트 추가
- [ ] P3-followup: race readiness insufficient_data UX 문구/리포트 섹션/AI context 표현 정교화

## Integration validation
- [ ] IV-1: 실제 Garmin/Strava export 샘플 기반 import_history 통합 검증
- [ ] IV-2: 실제 API 응답 fixture 기반 sync parser 검증 (Intervals 1차 완료, cross-source 전체 검증은 미완료)
- [ ] IV-3: dedup false positive / false negative 사례 수집
- [ ] IV-4: analyze.py / report.py / race_readiness.py 실제 데이터 sanity check (Intervals 1차 완료, 전체 검증은 미완료)
- [ ] IV-5: 익명화 fixture dataset 설계 및 tests/fixtures 구조 정리

- [x] IV-2: Intervals.icu 실제 API 응답 기반 sync parser 1차 검증 완료
- [x] IV-4: Intervals 실제 데이터 기반 analyze.py / report.py sanity check 1차 완료
- [x] IV-followup: Intervals payload 기반 interval_summary 리포트 노출 및 /payloads drill-down 개선
- [x] IV-followup: Intervals wellness 확장 필드 저장 및 report visibility 보강
- [x] IV-followup: `/payloads` 필터(`source`, `entity_type`, `activity_id`, `limit`) 추가

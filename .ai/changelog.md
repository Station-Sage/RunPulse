# RunPulse - 변경 이력

## 2026-03-18
- 프로젝트 초기 설정
- CLAUDE.md, AGENTS.md 생성
- .ai 문서 세트 생성 (index, todo, architecture, decisions, data-sources, files, roadmap)
- 디렉터리 구조 생성
- Phase 1 기반 구축 완료
  - requirements.txt 생성
  - db_setup.py: SQLite 스키마 5개 테이블 (activities, source_metrics, daily_wellness, planned_workouts, goals)
  - src/utils/config.py: 설정 파일 로드 유틸리티
  - src/utils/pace.py: 페이스 변환 (초↔분:초, km/h↔sec/km)
  - src/utils/zones.py: HR존/페이스존 계산 (5존)
  - src/utils/dedup.py: 중복 활동 매칭 (±5분, ±3%)
  - src/utils/clipboard.py: termux-clipboard-set 래퍼
  - tests/ 45개 테스트 (db_setup, pace, zones, dedup)
- Phase 2 데이터 수집 완료
  - src/utils/api.py: httpx 기반 GET/POST 래퍼 (1회 재시도)
  - src/sync/garmin.py: Garmin Connect 활동/웰니스 동기화
  - src/sync/strava.py: Strava OAuth2 토큰 갱신, 활동/스트림 동기화
  - src/sync/intervals.py: Intervals.icu Basic Auth 활동/웰니스(CTL/ATL) 동기화
  - src/sync/runalyze.py: Runalyze API Token 활동/VO2Max 동기화
  - src/sync.py: CLI 진입점 (--source all --days 7)
  - src/import_history.py: GPX/FIT 파일 일괄 임포트
  - tests/ 68개 테스트 전체 통과 (api, sync 4개, import, 통합 dedup)

## 2026-03-19
- Phase 3 분석 모듈 확장 설계
  - 기존 3개(compare, trends, report) → 10개 모듈로 확장
  - 신규: efficiency.py (EF/Decoupling), zones_analysis.py (80/20),
    activity_deep.py (단일활동 심층), race_readiness.py (레이스 준비도),
    recovery.py (Garmin 웰니스 기반), weekly_score.py (종합 점수)
- AI 코치 브리핑 시스템 설계
  - briefing.py: 탭 진입 시 자동 데이터 수집 + 프롬프트 조립
  - 오늘 활동 유무에 따른 분기 프롬프트
- 추천 칩(Suggestion Chips) 시스템 설계
  - suggestions.py: 규칙 기반(즉시) + AI 동적(응답 후) 하이브리드
  - RunnerState 기반 우선순위 정렬 로직
  - 칩 클릭 시 해당 프롬프트 템플릿 + 데이터 자동 조립
- Phase 4-1/4-2 분리 확정, Phase 5 AI 코치 탭 상세화
- 설계 결정 D11~D18 추가
- .ai 문서 전체 업데이트 (todo, architecture, files, roadmap, decisions, data-sources, changelog)
- 서비스 연동 가이드 전면 개편 (docs/setup-apis.md)
  - 4개 서비스별 구글 SSO 지원 현황 정리
  - CLI 모드(키 직접 입력) + 웹 UI 모드(소셜 로그인 팝업) 이중 방식 설계
  - Phase 5 웹 UI 연동 플로우 (Garmin SSO, Strava OAuth2, Intervals/Runalyze 안내)
  - 트러블슈팅 섹션 추가
- 설계 결정 D19 추가 (서비스 연동 이중 방식)
- Phase 5에 설정 탭 태스크 추가 (P5-5, P5-6)
## 2026-03-20 (Sprint 3-2)
- Sprint 3-2 심층 분석 모듈 구현 (branch: claude/sprint-3-2-deep-analysis)
  - src/analysis/efficiency.py: Strava stream 기반 Aerobic EF/Cardiac Decoupling
    - calculate_efficiency(): 전반/후반 EF 비교, 디커플링 %, status(good/fair/poor)
    - efficiency_trend(): N주간 주별 평균 EF/디커플링 추세
  - src/analysis/zones_analysis.py: HR Zone 분포, 80/20 법칙 판정
    - analyze_zones(): 3단계 폴백 (strava_stream > intervals_zones > avg_hr_estimate)
    - weekly_zone_trend(): N주 주별 강도 분포 추세, polarization_status 판정
  - src/analysis/activity_deep.py: 4소스 통합 단일 활동 심층 분석
    - deep_analyze(): 4소스 metrics + pace splits + fitness/recovery context
    - pace splits: Strava stream 1초 데이터 기반 1km 단위 구간 시간/심박
  - src/analysis/__init__.py: 신규 6개 함수 export
  - tests/ 39개 신규 (누적 183개)

## 2026-03-20
- Phase 1-2 스키마 확장 및 sync 개선 (branch: claude/fix-phase1-2-schema-sync)
  - db_setup.py: daily_fitness 테이블 신설 (CTL/ATL/TSB/VO2Max 날짜별 저장), planned_workouts에 source/ai_model/garmin_workout_id 컬럼 추가, migrate_db() 기존 DB 안전 업그레이드
  - garmin.py: aerobic/anaerobic Training Effect 분리 저장 + 하위호환 alias, vo2max→daily_fitness, sync_garmin() 클라이언트 1회 로그인 래퍼
  - strava.py: best_efforts 추출 및 JSON 저장, cadence*2 보정 확인
  - intervals.py: CTL/ATL/TSB를 source_metrics에서 daily_fitness로 이관, icu_hrss는 source_metrics 유지, HR Zone TODO 주석
  - runalyze.py: marathon_shape, race_prediction JSON 수집, daily_fitness 연동 (evo2max/vdot/marathon_shape)
  - compare.py: CTL/ATL/TSB, VO2Max를 daily_fitness에서 조회 (source_metrics 폴백)
  - trends.py: fitness_trend() daily_fitness 우선 참조, source_metrics 폴백, 결과 키 명확화
  - tests/ 41개 신규 테스트 (test_daily_fitness.py 20개 포함), 전체 144개 통과 (이전 103개 기준 +41개)
  - 설계 결정 D20 추가 (daily_fitness 테이블 분리)
  - .ai 문서 업데이트 (todo, decisions, files)
- Sprint 3-1 핵심 분석 모듈 구현 (branch: claude/sprint-3-1-core-analysis)
  - src/analysis/compare.py: 기간 비교 (matched_group_id 중복 제거, delta/pct 계산)
    - compare_periods(), compare_today_vs_yesterday(), compare_this_week_vs_last(), compare_this_month_vs_last()
    - 4개 소스 고유 지표: garmin training_effect/load, strava suffer_score, intervals CTL/ATL/TSB, runalyze VO2Max/VDOT
  - src/analysis/trends.py: 주간 추세 및 ACWR 부상 위험도
    - weekly_trends(): N주 롤링 집계, 주간 거리 변화율
    - calculate_acwr(): 4개 소스 교차 검증 (garmin_tl, strava_re, intervals_hrss, runalyze_trimp)
    - fitness_trend(): CTL/ATL/TSB/VO2Max 주간 추세
  - src/analysis/recovery.py: Garmin 웰니스 기반 회복 상태 평가
    - get_recovery_status(): 5개 지표 가중 평균 (body_battery 30%, sleep 25%, hrv 25%, stress 15%, rhr 5%)
    - recovery_trend(): N일 추세, 상승/하락/안정 판정
  - src/analysis/weekly_score.py: Training Quality Score (0-100)
    - 6개 컴포넌트: volume(25), intensity(20), acwr(20), recovery(15), consistency(10), efficiency(10)
    - 등급 판정: A(85+), B(70+), C(55+), D(40+), F
  - tests/ 58개 신규 테스트 추가 (누적 103개)

## 2026-03-19
- Sprint 3-3 완료
- race_readiness.py 추가: 레이스 준비도 6개 지표 가중 평가, VDOT 기반 레이스 예측
- report.py 추가: today/week/month/race/full 마크다운 리포트 및 AI 컨텍스트 생성
- analyze.py 추가: argparse 기반 CLI 진입점
- analysis/__init__.py export 업데이트
- utils/config.py 수정: config.json 없어도 기본값으로 동작
- 테스트 추가: race_readiness/report/analyze_cli
- Phase 3 전체 완료

## 2026-03-20 (feature/intervals-analysis-polish)
- Intervals 후속 polish 작업 반영
  - report.py: `interval_summary` 리포트 노출 및 포맷 개선
  - report.py: 거리/시간/zone 분포 표시 가독성 개선
  - report.py: Intervals wellness 참고 섹션 추가 (`steps`, `sleep`, `hrv`, `resting_hr`)
  - report.py: `daily_wellness` 값이 비어 있을 때 raw payload fallback 사용
  - db_setup.py: `daily_wellness` 확장 컬럼 추가
    - `hrv_sdnn`, `avg_sleeping_hr`, `fatigue`, `mood`, `motivation`, `steps`, `weight_kg`
  - sync/intervals.py: Intervals wellness 확장 필드 저장 로직 추가
  - web/app.py: `/payloads/view` drill-down 추가
  - web/app.py: `/payloads` recent payload `open` 링크 및 필터(`source`, `entity_type`, `activity_id`, `limit`) 추가
- 실데이터 sanity 확인
  - latest Intervals run 리포트에서 interval summary, efficiency, zone 분포, wellness 참고 출력 확인

## 2026-03-20

- Sprint 3-3 / Phase 3 완료
- race_readiness.py 추가: 레이스 준비도 평가, VDOT 기반 레이스 예측, insufficient_data 처리
- report.py 추가: today/week/month/race/full 마크다운 리포트 및 AI context 생성
- analyze.py 추가: argparse 기반 CLI 엔트리포인트와 공통 옵션 지원
- tests 추가/수정: race_readiness, report, analyze_cli 테스트 보강
- sync.garmin 개선: garminconnect optional dependency 처리로 Termux 환경 테스트 호환성 확보
- 전체 테스트 통과: 212 passed

- 2026-03-20: Intervals.icu 실데이터 검증 진행. activities/wellness raw payload 보존용 source_payloads 테이블 추가.
- 2026-03-20: Intervals activity metrics(trimp, strain_score, icu_efficiency_factor, decoupling, zone times 등) 정규화 저장 추가.
- 2026-03-20: analyze/report가 Intervals efficiency 및 zone 데이터를 반영하도록 개선.
- 2026-03-20: integration workbench에 /payloads 페이지 추가하여 raw payload/source_metrics 상태 확인 가능.

## 2026-03-20 (Phase 4)
- Phase 4 훈련 계획 및 목표 구현 (branch: feature/phase4-ai-coach)
  - src/training/__init__.py: 모듈 export
  - src/training/goals.py: 목표 CRUD 7개 함수
    - add_goal(), list_goals(), get_goal(), get_active_goal()
    - update_goal(), complete_goal(), cancel_goal()
    - 기존 goals 테이블 활용 (DB 스키마 변경 없음)
  - src/training/planner.py: 규칙 기반 주간 훈련 계획 생성
    - generate_weekly_plan(): CTL/TSB/목표거리/레이스까지 주수 기반 Daniels 원칙 적용
    - 훈련 단계 4단계: base/build/peak/taper
    - 80/20 강도 분배, TSB 기반 볼륨 보정
    - save_weekly_plan(), get_planned_workouts()
  - src/training/adjuster.py: 컨디션 기반 당일 계획 조정
    - _fatigue_level(): body_battery/sleep_score/stress/TSB 복합 피로도 판정
    - 피로 높음: interval/tempo→rest, long→easy
    - 피로 중간: interval/tempo/long→easy
    - 컨디션 양호(TSB>10 + battery>70): volume_boost 플래그
  - src/plan.py: CLI 진입점
    - plan.py week / today / generate [--goal-id N]
    - plan.py goal list/add/done/cancel
  - tests/test_goals.py: 14개 테스트
  - tests/test_planner.py: 17개 테스트
  - tests/test_adjuster.py: 11개 테스트

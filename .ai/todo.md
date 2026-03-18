# RunPulse - 작업 목록
최종 업데이트: 2026-03-18

## Phase 1: 기반 구축 (현재)
- [ ] P1-1: 디렉터리 구조 및 문서 생성
- [ ] P1-2: db_setup.py - SQLite 스키마 생성 (activities, source_metrics, daily_wellness, planned_workouts, goals)
- [ ] P1-3: src/utils/pace.py - 페이스 변환 함수 (초를 분:초로, km/h를 min/km로)
- [ ] P1-4: src/utils/zones.py - HR존 및 Pace존 계산 (사용자 max_hr, threshold_pace 기반)
- [ ] P1-5: src/utils/dedup.py - 중복 활동 매칭 (timestamp 플러스마이너스 5분, distance 플러스마이너스 3퍼센트)
- [ ] P1-6: src/utils/clipboard.py - termux-clipboard-set 래퍼
- [ ] P1-7: config.json.example 생성
- [ ] P1-8: tests/ 기본 테스트 작성 (pace, zones, dedup)

## Phase 2: 데이터 수집
- [ ] P2-1: src/sync/garmin.py - garminconnect 라이브러리로 활동 및 웰니스 데이터 가져오기
- [ ] P2-2: src/sync/strava.py - Strava OAuth2 토큰 갱신 및 활동/스트림 가져오기
- [ ] P2-3: src/sync/intervals.py - Intervals.icu Basic Auth로 활동 및 CTL/ATL/TSB 가져오기
- [ ] P2-4: src/sync/runalyze.py - Runalyze API 토큰으로 활동 및 VO2Max/Race Prediction 가져오기
- [ ] P2-5: src/sync.py - CLI 진입점. --source (garmin|strava|intervals|runalyze|all) --days N
- [ ] P2-6: src/import_history.py - GPX/FIT 파일 일괄 파싱 및 DB 삽입
- [ ] P2-7: 중복 매칭 통합 테스트

## Phase 3: 분석 리포트
- [ ] P3-1: src/analysis/compare.py - 오늘vs어제, 이번주vs지난주, 이번달vs지난달/작년 비교
- [ ] P3-2: src/analysis/trends.py - 주간 추세, ACWR 부상 위험도, 최적 주행거리 분석
- [ ] P3-3: src/analysis/report.py - 마크다운 포매팅, 4개 소스 고유 지표 섹션 분리
- [ ] P3-4: src/analyze.py - CLI 진입점. today|week|month|compare|trends|full --clipboard --save

## Phase 4: 훈련 계획 및 목표
- [ ] P4-1: src/training/goals.py - 목표 CRUD (레이스명, 날짜, 거리, 목표 시간, 자동 페이스 계산)
- [ ] P4-2: src/training/planner.py - 주간/월간 훈련 계획 생성 (현재 CTL, VO2Max 기반)
- [ ] P4-3: src/training/adjuster.py - 컨디션(HRV, Sleep, Body Battery) 기반 당일 계획 조정
- [ ] P4-4: src/plan.py - CLI 진입점. goal add|list, plan week|month, context --clipboard

## Phase 5: 웹 대시보드
- [ ] P5-1: src/serve.py + src/web/app.py - Flask 경량 서버
- [ ] P5-2: 대시보드 (오늘 요약, 주간 통계, 피트니스 차트, 최근 활동 목록)
- [ ] P5-3: 모바일 반응형 HTML

## Phase 6: 고도화
- [ ] P6-1: Genspark 프롬프트 템플릿 최적화
- [ ] P6-2: cron 자동 동기화 (termux-job-scheduler)
- [ ] P6-3: termux-notification 알림 연동

## 완료 기록
(완료된 작업은 여기로 이동하고 날짜 기록)

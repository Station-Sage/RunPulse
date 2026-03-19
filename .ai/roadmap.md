# RunPulse - 개발 로드맵

## Phase 1: 기반 구축 (완료)
목표: 프로젝트 구조, DB 스키마, 유틸리티 함수, 기본 테스트
산출물: db_setup.py, utils 모듈 5개, 테스트 45개

## Phase 2: 데이터 수집 (완료)
목표: 4개 소스 동기화, GPX/FIT 임포트, 중복 매칭
산출물: sync 모듈 4개, sync.py, import_history.py, 테스트 68개

## Phase 3: 분석 리포트 (현재, 3개 스프린트)
목표: 4개 소스 고유 데이터를 최대 활용한 통합 분석

Sprint 3-1 (핵심 기반, ~1시간):
- compare.py: 기간 비교
- trends.py: 추세 + ACWR (4소스 교차 검증)
- recovery.py: Garmin 웰니스 기반 회복
- weekly_score.py: 종합 점수 0-100
산출물: 브리핑 프롬프트의 핵심 데이터 공급 가능

Sprint 3-2 (심층 분석, ~1시간):
- efficiency.py: EF + Cardiac Decoupling (Strava Stream)
- zones_analysis.py: 80/20 강도 분포
- activity_deep.py: 단일 활동 심층
산출물: 칩 "오늘 훈련 상세 분석"의 데이터 공급 가능

Sprint 3-3 (레이스 & 출력, ~1시간):
- race_readiness.py: 레이스 준비도 종합
- report.py: 마크다운 포맷팅 (인간용 + AI용)
- analyze.py: CLI 진입점
산출물: CLI로 전체 분석 실행 가능

## Phase 4: 훈련 계획 및 목표 (~1시간)
목표: 목표 관리, 계획 생성/조정
산출물: training 모듈 3개, plan.py CLI

## Phase 4-1: AI 코치 연동 (~1.5시간)
목표: 브리핑 자동 생성, 추천 칩, 프롬프트 템플릿, 응답 파싱
산출물: ai 모듈 5개, 프롬프트 템플릿 10종
의존: Phase 3 (분석 데이터), Phase 4 (목표 데이터)

## Phase 4-2: 가민 워크아웃 캘린더 (~1시간)
목표: AI 훈련 계획 → 가민 워크아웃 변환 → 캘린더 등록 → 슬롯 우회
산출물: workout 모듈 3개
의존: Phase 4-1 (AI 파싱된 계획)

## Phase 5: 웹 대시보드 (~2시간)
목표: 대시보드, AI 코치 탭(브리핑+채팅+칩), 훈련 계획 탭, 모바일 반응형
산출물: Flask 서버, HTML/CSS/JS
의존: Phase 3 (차트 데이터), Phase 4-1 (AI 코치 기능)

## Phase 6: 고도화 (지속)
목표: 다중 AI 프로바이더, DOM 자동 감지, 대화 이력, cron, 알림
산출물: 점진적 개선

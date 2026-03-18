# RunPulse - 개발 로드맵

## Phase 1: 기반 구축 (1주)
목표: 프로젝트 구조, DB 스키마, 유틸리티 함수, 기본 테스트
산출물: db_setup.py, utils 모듈 4개, 테스트 5개 이상

## Phase 2: 데이터 수집 (2주)
목표: 4개 소스 동기화 모듈, GPX/FIT 일괄 임포트, 중복 매칭
산출물: sync 모듈 4개, sync.py CLI, import_history.py

## Phase 3: 분석 리포트 (1주)
목표: 기간 비교, 추세 분석, 마크다운 리포트, 클립보드 복사
산출물: analysis 모듈 3개, analyze.py CLI

## Phase 4: 훈련 계획 및 목표 (1주)
목표: 목표 관리, 주간/월간 계획 생성, 컨디션 기반 조정, Genspark 컨텍스트
산출물: training 모듈 3개, plan.py CLI

## Phase 5: 웹 대시보드 (1주)
목표: 로컬 웹 서버, 대시보드 페이지, 모바일 반응형
산출물: serve.py, web 모듈

## Phase 6: 고도화 (지속)
목표: Genspark 프롬프트 최적화, 자동화(cron), 알림, 추가 차트
산출물: scripts/ 자동화 스크립트, 프롬프트 템플릿

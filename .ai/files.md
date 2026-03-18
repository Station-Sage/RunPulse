# RunPulse - 파일별 역할

## 진입점 (src 루트)
- db_setup.py: SQLite 테이블 생성, 마이그레이션
- sync.py: 데이터 동기화 CLI 진입점, argparse로 --source --days 처리
- analyze.py: 분석 리포트 CLI 진입점, argparse로 today|week|month|compare|trends|full 처리
- plan.py: 훈련 계획 및 목표 CLI 진입점
- serve.py: Flask/bottle 웹서버 실행
- import_history.py: GPX/FIT 파일 일괄 파싱 및 DB 삽입

## sync 모듈
- garmin.py: GarminConnect 세션 관리, 활동/웰니스 가져오기, DB 저장
- strava.py: OAuth 토큰 갱신, 활동/스트림 가져오기, 스트림은 JSON 파일로 저장
- intervals.py: Basic Auth로 활동/웰니스(CTL/ATL/TSB) 가져오기
- runalyze.py: API 토큰으로 활동/VO2Max 가져오기

## analysis 모듈
- compare.py: 두 기간 비교 로직. 거리/시간/페이스/HR 변화량 및 변화율 계산
- trends.py: N주 추세 회귀, ACWR(Acute:Chronic Workload Ratio) 계산
- report.py: 마크다운 테이블 및 서술 텍스트 포매팅, 소스별 섹션 생성

## training 모듈
- goals.py: 목표 SQLite CRUD, 목표 페이스 자동 계산
- planner.py: 주간/월간 훈련 스케줄 생성 (현재 피트니스 수준 기반)
- adjuster.py: 당일 컨디션 점수 계산, 계획 상향/하향 조정

## utils 모듈
- api.py: httpx 기반 GET/POST 래퍼, 재시도, 에러 처리
- pace.py: 초를 "분:초/km"로, km/h를 min/km로 변환 등
- zones.py: 5존 HR 계산 (max_hr 기반), 페이스 존 계산 (threshold_pace 기반)
- dedup.py: 중복 활동 매칭 함수
- clipboard.py: termux-clipboard-set 호출 래퍼

## web 모듈
- app.py: 라우트 정의, DB 쿼리, 템플릿 렌더링
- templates/: HTML 파일들 (대시보드, 활동 상세 등)

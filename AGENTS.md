# AGENTS.md - RunPulse

## 프로젝트
RunPulse - Termux 기반 개인 러닝 데이터 분석 및 훈련 코치 에이전트

## 기술 스택
- Python 3.11+, SQLite3, garminconnect, httpx, gpxpy, fitparse
- 실행 환경: Android Termux
- AI 분석: Genspark AI Chat (클립보드 복사 후 붙여넣기 워크플로)

## 소스 코드 구조

    src/
    ├── db_setup.py          # SQLite 스키마 초기화
    ├── sync.py              # 4개 소스 데이터 동기화 CLI
    ├── analyze.py           # 분석 리포트 생성 CLI
    ├── plan.py              # 훈련 계획 및 목표 관리 CLI
    ├── serve.py             # 경량 웹 대시보드
    ├── sync/
    │   ├── garmin.py        # Garmin Connect 동기화
    │   ├── strava.py        # Strava API 동기화
    │   ├── intervals.py     # Intervals.icu API 동기화
    │   └── runalyze.py      # Runalyze API 동기화
    ├── analysis/
    │   ├── compare.py       # 기간 비교 분석
    │   ├── trends.py        # 추세 분석, 부상 위험 감지
    │   └── report.py        # 마크다운 리포트 포매팅
    ├── training/
    │   ├── goals.py         # 목표 CRUD
    │   ├── planner.py       # 훈련 계획 생성
    │   └── adjuster.py      # 컨디션 기반 계획 조정
    ├── utils/
    │   ├── api.py           # HTTP 요청 래퍼
    │   ├── pace.py          # 페이스 변환 유틸
    │   ├── zones.py         # HR/Pace 존 계산
    │   ├── dedup.py         # 중복 활동 매칭
    │   └── clipboard.py     # termux-clipboard-set 래퍼
    └── web/
        ├── app.py           # Flask/bottle 앱
        └── templates/       # HTML 템플릿

## 4개 소스별 고유 데이터

Garmin 고유 지표:
  Training Status, Training Effect, Training Load, VO2Max(기기),
  Body Battery, Sleep Score, HRV Status, Stress

Strava 고유 지표:
  Relative Effort(Suffer Score), Segment PR,
  1초 단위 Stream(HR/Speed/Cadence/Altitude/Power)

Intervals.icu 고유 지표:
  CTL(Fitness), ATL(Fatigue), TSB(Form), Ramp Rate,
  HR/Pace Zone 분포, HRSS, Pace 기반 Training Load

Runalyze 고유 지표:
  Effective VO2Max, VDOT, Race Prediction(5K~마라톤),
  TRIMP, Marathon Shape, Performance Condition

## 실행 명령어

    python src/db_setup.py
    python src/sync.py --source all --days 7
    python src/analyze.py today
    python src/plan.py week
    python -m pytest tests/

## 작업 규칙
- CLAUDE.md 참조
- 파일 300줄 이하
- config.json 커밋 금지
- conventional commits 사용

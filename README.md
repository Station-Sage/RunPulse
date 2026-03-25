# RunPulse

Termux 기반 개인 러닝 데이터 분석 및 훈련 코치 에이전트

## 특징
- Garmin, Strava, Intervals.icu, Runalyze 4개 소스 통합
- 각 플랫폼의 고유 2차 데이터를 병합하여 다각도 분석
- 오늘/주간/월간 비교 리포트, 추세 분석
- 훈련 계획 생성 및 레이스 목표 관리
- Genspark AI Chat 연동 (클립보드 복사)
- 전액 무료, Termux에서 완전 동작

## 4개 소스의 고유 가치

    Garmin    : Training Effect, Body Battery, HRV Status, Sleep Score
    Strava    : Suffer Score, Segment PR, 1초 단위 Stream
    Intervals : CTL(Fitness), ATL(Fatigue), TSB(Form), Ramp Rate
    Runalyze  : Effective VO2Max, VDOT, Race Prediction, TRIMP

## 빠른 시작

    # Termux에서
    pkg install -y python git sqlite termux-api
    pip install garminconnect httpx gpxpy python-dateutil fitparse

    cd ~/projects
    git clone -b dev https://github.com/Station-Sage/RunPulse.git
    cd RunPulse

    cp config.json.example config.json
    # config.json 편집하여 인증 정보 입력

    python src/db_setup.py
    python src/sync.py --source all --days 7
    python src/analyze.py today
    python src/analyze.py full --clipboard
    # Genspark AI Chat에 붙여넣고 분석 요청

## 문서
- docs/setup-termux.md: Termux 설치 가이드
- docs/setup-apis.md: API 설정 가이드
- docs/usage.md: 사용 가이드
- docs/install-guide.md: 솔루션 및 리소스 설치 가이드

## 아키텍처

    Garmin/Strava/Intervals/Runalyze
                |
          [sync.py - 4개 소스 동기화]
                |
          [running.db (SQLite)]
                |
       +--------+--------+
       |        |        |
    analyze  plan.py  serve.py
       |        |        |
    리포트   훈련계획  대시보드
       |        |
    클립보드 -> Genspark AI Chat

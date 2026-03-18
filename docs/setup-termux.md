# Termux 설치 가이드

## 1. Termux 설치
F-Droid에서 설치: https://f-droid.org/packages/com.termux/
Google Play 버전은 오래되었으므로 F-Droid 권장

## 2. 기본 패키지

    pkg update && pkg upgrade -y
    pkg install -y python git sqlite termux-api

## 3. Python 패키지

    pip install --upgrade pip
    pip install garminconnect httpx gpxpy python-dateutil fitparse
    pip install pytest  # 테스트용
    pip install flask   # 웹 대시보드용 (선택)

## 4. 저장소 클론

    mkdir -p ~/projects
    cd ~/projects
    git clone -b dev https://github.com/Station-Sage/RunPulse.git
    cd RunPulse

## 5. 설정 파일

    cp config.json.example config.json
    # config.json을 편집하여 실제 인증 정보 입력
    # nano config.json 또는 vi config.json

## 6. DB 초기화

    python src/db_setup.py

## 7. 테스트 동기화

    python src/sync.py --source garmin --days 1

## 8. 리포트 확인

    python src/analyze.py today

## termux-api 권한
Termux:API 앱도 F-Droid에서 설치 필요.
클립보드 기능 사용 시 termux-clipboard-set 명령어가 동작하는지 확인:

    echo "test" | termux-clipboard-set
    termux-clipboard-get

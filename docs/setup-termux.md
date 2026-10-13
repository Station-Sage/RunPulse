# Termux 설치 가이드

## 1. Termux 설치
F-Droid에서 설치: https://f-droid.org/packages/com.termux/
Google Play 버전은 오래되었으므로 F-Droid 권장

## 2. 기본 패키지

    pkg update && pkg upgrade -y
    pkg install -y python git sqlite termux-api

## 3. Python 패키지

    pip install --upgrade pip
    pip install -r requirements.txt   # flask·gunicorn 포함 (필수)
    pip install pytest                # 테스트용

flask 는 웹 앱·테스트에 필수이고, gunicorn 은 Docker 실행과 테스트 수집에 필요하다
(Termux 실행 자체는 `python src/serve.py` 라 gunicorn 을 쓰지 않는다). 가상환경(`.venv` 또는 `start.sh` 의
`/root/venvs/runpulse`)에 설치하고 시스템 python 에는 설치하지 않는다 (ENV-1).
저장소 클론(4단계) 후 저장소 루트에서 실행한다.

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

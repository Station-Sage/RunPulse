# RunPulse 솔루션 및 리소스 설치 가이드

## 1. Termux 기본 환경

    # Termux 설치: F-Droid에서 다운로드
    # https://f-droid.org/packages/com.termux/

    # Termux:API 앱도 설치 (클립보드 기능용)
    # https://f-droid.org/packages/com.termux.api/

    # 기본 패키지
    pkg update && pkg upgrade -y
    pkg install -y python git sqlite termux-api curl

## 2. Python 패키지

    pip install --upgrade pip

    # 필수
    pip install garminconnect    # Garmin Connect 비공식 API
    pip install httpx            # 비동기 HTTP 클라이언트
    pip install gpxpy            # GPX 파일 파싱
    pip install fitparse         # FIT 파일 파싱
    pip install python-dateutil  # 날짜 파싱 유틸

    # 테스트
    pip install pytest

    # 웹 대시보드 (선택)
    pip install flask
    # 또는 더 경량: pip install bottle

## 3. SQLite (이미 포함)
Termux의 Python에 sqlite3 모듈이 내장되어 있음.
별도 설치 불필요.
확인:

    python -c "import sqlite3; print(sqlite3.sqlite_version)"

## 4. Git 설정

    git config --global user.name "Your Name"
    git config --global user.email "your@email.com"

## 5. 스토리지 권한
Termux에서 공유 스토리지 접근이 필요한 경우:

    termux-setup-storage

## 6. 선택적 도구

    # 텍스트 에디터
    pkg install -y nano
    # 또는
    pkg install -y vim

    # JSON 처리
    pkg install -y jq

    # 프로세스 관리 (웹서버 백그라운드 실행 시)
    pkg install -y tmux

## 7. 디스크 사용량 참고
- running.db: 활동 1000개 기준 약 5-10MB
- Strava 스트림 JSON: 활동당 약 100-500KB
- GPX/FIT 히스토리: 활동 수에 따라 수백MB 가능
- 총 예상: 500MB-2GB (과거 데이터 보관량에 따라)

## 8. 트러블슈팅

### garminconnect 설치 실패 시

    pkg install -y build-essential
    pip install garminconnect

### fitparse 설치 실패 시

    pkg install -y clang
    pip install fitparse

### termux-clipboard-set 동작 안 할 때
Termux:API 앱이 설치되어 있는지 확인.
두 앱(Termux, Termux:API) 모두 F-Droid에서 설치해야 호환됨.
Google Play와 F-Droid 버전을 섞으면 동작하지 않음.

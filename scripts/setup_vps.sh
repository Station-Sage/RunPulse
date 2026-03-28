#!/bin/bash
# RunPulse VPS 초기 설정 스크립트
# 대상: Ubuntu 24.04 (AWS Lightsail)
# 실행: bash setup_vps.sh
set -e

REPO_URL="https://github.com/Station-Sage/RunPulse.git"
APP_DIR="$HOME/RunPulse"

echo "=== [1/5] 시스템 패키지 업데이트 ==="
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y git curl

echo "=== [2/5] Docker 설치 ==="
if ! command -v docker &>/dev/null; then
  curl -fsSL https://get.docker.com | sh
  sudo usermod -aG docker "$USER"
  echo "Docker 설치 완료. 그룹 변경 적용을 위해 재로그인이 필요할 수 있습니다."
else
  echo "Docker 이미 설치됨: $(docker --version)"
fi

echo "=== [3/5] 소스코드 클론 ==="
if [ -d "$APP_DIR" ]; then
  echo "이미 존재: $APP_DIR — git pull 실행"
  git -C "$APP_DIR" pull
else
  git clone "$REPO_URL" "$APP_DIR"
fi

echo "=== [4/5] DB 초기화 및 앱 빌드/시작 ==="
cd "$APP_DIR"

# config.json이 없으면 예제 복사
if [ ! -f config.json ] && [ -f config.json.example ]; then
  cp config.json.example config.json
  echo "config.json 생성됨 — API 키를 입력하세요: nano config.json"
fi

# Docker 이미지 빌드 + 컨테이너 시작
docker compose build
docker compose up -d

# DB 초기화 (최초 1회)
docker compose exec runpulse python src/db_setup.py

echo "=== [5/5] code-server 설치 ==="
if ! command -v code-server &>/dev/null; then
  curl -fsSL https://code-server.dev/install.sh | sh
  # 서비스 등록 (부팅 시 자동 시작)
  sudo systemctl enable --now code-server@"$USER"
  echo "code-server 설치 완료."
else
  echo "code-server 이미 설치됨."
fi

echo ""
echo "========================================"
echo "설치 완료!"
echo ""
echo "RunPulse 앱:  http://$(curl -s ifconfig.me)"
echo ""
echo "code-server 터널 시작 방법:"
echo "  code-server --auth none &"
echo "  code tunnel"
echo "  # GitHub 계정으로 인증 후 vscode.dev 링크 출력됨"
echo ""
echo "config.json 편집:  nano $APP_DIR/config.json"
echo "컨테이너 재시작:   cd $APP_DIR && docker compose restart"
echo "로그 확인:         cd $APP_DIR && docker compose logs -f"
echo "========================================"

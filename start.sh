#!/data/data/com.termux/files/usr/bin/bash
# RunPulse 서버 시작 스크립트 (Termux → proot debian)
#
# 사용법:
#   ./start.sh          # 기본 실행 (포트 18080)
#   ./start.sh 8080     # 포트 지정
#
# 중지: Ctrl+C

PORT="${1:-18080}"

echo "🏃 RunPulse 서버 시작 (포트: $PORT)"
echo "   http://localhost:$PORT/dashboard"
echo ""

PROJ_DIR="$(cd "$(dirname "$0")" && pwd)"

proot-distro login debian --bind "$PROJ_DIR:/root/RunPulse" -- bash -c "
  source /root/venvs/runpulse/bin/activate
  cd /root/RunPulse
  python src/serve.py --port $PORT
"

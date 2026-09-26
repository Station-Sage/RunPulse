#!/usr/bin/env bash
# 클라우드(Claude Code on the web) 세션 환경 준비 — 멱등. 실 DB·config.json 없이 테스트가 도는 상태를 만든다.
set -euo pipefail
cd "$(dirname "$0")/.."

python3 -m pip install -q -r requirements.txt pytest
(cd frontend && npm ci --no-audit --no-fund)

# 실 DB 통합 테스트는 DB가 없으면 skip 된다. default 유저 DB 는 만들지 않는다.
python3 -m pytest tests/test_activity_types.py -q
echo "cloud setup OK"

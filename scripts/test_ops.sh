#!/usr/bin/env bash
# 관제 콘솔·감사 서비스·오토파일럿 테스트만 실행 (전체 스위트는 커밋·병합 직전에만). 인자는 pytest 로 전달.
cd "$(dirname "$0")/.." || exit 1
files=$(grep -rlE "scripts[./](audit|autopilot|console)" tests --include='test_*.py' | sort)
exec .venv/bin/python -m pytest $files -q "$@"

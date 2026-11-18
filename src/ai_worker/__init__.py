"""호스트 Claude CLI 워커 (V2-AI-CLAUDE-QUEUE) — ai_jobs 큐를 폴링해 `claude -p` 로 처리한다.

표준 라이브러리와 순수 src 모듈만 쓴다(flask import 금지). 컨테이너 앱과는 DB 폴링으로만 통신한다.
설계: v0.3/data/phase-7-ui-renewal/DESIGN-V2-AI-CLAUDE-QUEUE.md
"""

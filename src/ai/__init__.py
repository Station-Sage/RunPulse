# src/ai/__init__.py
"""AI 코칭 컨텍스트 빌더.

서비스 레이어 데이터를 LLM 프롬프트용 마크다운으로 변환.
직접 SQL 금지 — 서비스 레이어만 호출. None 메트릭은 출력에서 제외.

설계 문서: v0.3/data/phase-5-impl/02-ai-context.md
의존: src/services/, src/web/template_helpers.py
"""

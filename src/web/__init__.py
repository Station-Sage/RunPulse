# src/web/__init__.py
"""Flask 웹 뷰 + 템플릿 헬퍼.

Phase 7까지 기존 69개 뷰 파일은 수정하지 않음.
Phase 5에서 template_helpers.py만 신규 추가.

설계 문서: v0.3/data/phase-5-impl/03-template-helpers.md
의존: src/services/, src/utils/metric_registry.py
주의: 기존 뷰는 v0.2 스키마 기준 — 새 스키마와 혼용 금지
"""

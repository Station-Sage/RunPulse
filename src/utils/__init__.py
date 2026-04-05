# src/utils/__init__.py
"""공유 유틸리티.

DB 헬퍼, 메트릭 레지스트리, 시맨틱 그룹, rate limiter 등.
다른 모듈이 공통으로 사용하는 기능만 배치.
metric_registry는 category의 single source of truth.

설계 문서: v0.3/data/architecture.md
주의: db_helpers의 upsert 함수는 Phase 3 sync에서만 호출.
      서비스 레이어는 read 함수만 사용.
"""

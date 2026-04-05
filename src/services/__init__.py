# src/services/__init__.py
"""Phase 5 서비스 레이어.

DB에서 데이터를 읽어 가공된 dict를 반환한다.
읽기 전용 — DB 쓰기 금지. 첫 번째 인자는 항상 sqlite3.Connection.
반환값은 dict (snake_case 키). 단위 변환 하지 않음 — SI 그대로 반환.

설계 문서: v0.3/data/phase-5-impl/01-service-layer.md
의존: src/utils/db_helpers.py, src/utils/metric_registry.py
주의: metric_store 조회 시 is_primary=1 필터 필수
"""

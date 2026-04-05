# src/metrics/__init__.py
"""Phase 4 메트릭 엔진.

CalcContext API로 데이터를 읽고 metric_store에 결과를 쓴다.
모든 calculator는 MetricCalculator를 상속. 의존성은 produces/depends로 선언.
데이터 부족 시 None 반환. confidence로 신뢰도 표시.

설계 문서: v0.3/data/phase-4.md
의존: src/utils/db_helpers.py, src/utils/metric_registry.py, src/utils/metric_groups.py
주의: category는 calculator의 self.category가 DB 저장값 (registry 아님)
"""

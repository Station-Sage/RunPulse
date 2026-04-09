"""RunPulse 데이터 검증 패키지.

초기 데이터 적재 후 파이프라인 정합성을 자동 검증합니다.
12개 체크: row_counts, source_distribution, unmapped_metric_ratio,
metric_density, primary_uniqueness, provider_distribution,
dedup_consistency, data_quality, wellness_coverage,
fitness_continuity, referential_integrity, engine_coverage.

사용법:
    from src.validation.validator import DataValidator
    results = DataValidator(conn).run_all()
"""

from src.validation.validator import DataValidator, CheckResult

__all__ = ["DataValidator", "CheckResult"]

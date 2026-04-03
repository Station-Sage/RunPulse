"""메트릭 이름 충돌 방지 검증 테스트 (보강 #9)."""
from src.metrics.engine import ALL_CALCULATORS


# activity_summaries 컬럼명 (calculator가 이 이름을 produces로 쓰면 이중 저장)
ACTIVITY_SUMMARY_COLUMNS = {
    "distance_m", "duration_sec", "moving_time_sec", "avg_hr", "max_hr",
    "avg_cadence", "avg_speed_ms", "max_speed_ms", "avg_pace_sec_km",
    "calories", "elevation_gain", "elevation_loss", "avg_power", "max_power",
    "normalized_power", "training_effect_aerobic", "training_effect_anaerobic",
    "training_load", "suffer_score", "avg_ground_contact_time_ms",
    "avg_stride_length_cm", "avg_vertical_oscillation_cm",
    "avg_vertical_ratio_pct", "avg_temperature",
}


class TestMetricNaming:
    def test_no_calculator_uses_activity_summary_column_name(self):
        """calculator produces가 activity_summaries 컬럼명과 겹치면 안 됨."""
        for calc in ALL_CALCULATORS:
            for produced in calc.produces:
                assert produced not in ACTIVITY_SUMMARY_COLUMNS, (
                    f"Calculator '{calc.name}' produces '{produced}' "
                    f"which conflicts with activity_summaries column"
                )

    def test_no_duplicate_produces_across_calculators(self):
        """서로 다른 calculator가 같은 metric_name을 produces하면 안 됨
        (같은 이름은 provider로 구분하므로 허용하되, produces 선언 중복은 의도 확인 필요)."""
        seen = {}
        for calc in ALL_CALCULATORS:
            for produced in calc.produces:
                if produced in seen:
                    # 같은 scope_type이면 충돌
                    other = seen[produced]
                    assert calc.scope_type != other.scope_type or calc.name == other.name, (
                        f"'{produced}' is produced by both "
                        f"'{other.name}' and '{calc.name}' in same scope"
                    )
                seen[produced] = calc

    def test_all_produces_are_non_empty(self):
        """모든 calculator가 최소 1개의 produces를 가져야 함."""
        for calc in ALL_CALCULATORS:
            assert len(calc.produces) >= 1, f"Calculator '{calc.name}' has empty produces"

    def test_all_names_are_unique(self):
        """모든 calculator name이 고유해야 함."""
        names = [c.name for c in ALL_CALCULATORS]
        assert len(names) == len(set(names)), f"Duplicate names: {names}"

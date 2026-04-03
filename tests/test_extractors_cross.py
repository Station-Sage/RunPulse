"""Cross-extractor 일관성 테스트.

Phase 2 완료 조건 2, 4, 5, 6, 8, 10 검증.
모든 extractor가 동일한 규칙을 따르는지 확인합니다.
"""

import json
import pytest
from pathlib import Path

from src.sync.extractors import get_extractor, EXTRACTORS, BaseExtractor
from src.sync.extractors.base import MetricRecord
from src.sync.extractors.garmin_extractor import _seconds as garmin_seconds


FIXTURES_ROOT = Path(__file__).parent / "fixtures" / "api"

# activity_summaries 허용 컬럼 목록 (db_helpers.py의 _ACTIVITY_COLUMNS + 자동 컬럼)
_VALID_CORE_KEYS = {
    "source", "source_id", "matched_group_id",
    "name", "activity_type", "start_time",
    "distance_m", "duration_sec", "moving_time_sec", "elapsed_time_sec",
    "avg_speed_ms", "max_speed_ms", "avg_pace_sec_km",
    "avg_hr", "max_hr",
    "avg_cadence", "max_cadence",
    "avg_power", "max_power", "normalized_power",
    "elevation_gain", "elevation_loss",
    "calories",
    "training_effect_aerobic", "training_effect_anaerobic",
    "training_load", "suffer_score",
    "avg_ground_contact_time_ms", "avg_stride_length_cm",
    "avg_vertical_oscillation_cm", "avg_vertical_ratio_pct",
    "start_lat", "start_lon", "end_lat", "end_lon",
    "avg_temperature",
    "description", "event_type", "device_name", "gear_id", "source_url",
}

_REQUIRED_CORE_KEYS = {"source", "source_id", "activity_type", "start_time"}

# 소스별 minimal fixture 경로
_FIXTURES = {
    "garmin": FIXTURES_ROOT / "garmin" / "activity_summary_minimal.json",
    "strava": FIXTURES_ROOT / "strava" / "activity_minimal.json",
    "intervals": FIXTURES_ROOT / "intervals" / "activity_minimal.json",
    "runalyze": FIXTURES_ROOT / "runalyze" / "activity_minimal.json",
}


def _load_fixture(source: str) -> dict:
    with open(_FIXTURES[source]) as f:
        return json.load(f)


# ─────────────────────────────────────────────────────────────────────
# 조건 2: get_extractor() 팩토리 함수
# ─────────────────────────────────────────────────────────────────────


class TestGetExtractorFactory:
    """조건 2: get_extractor("garmin") 등 팩토리 함수 정상 동작."""

    @pytest.mark.parametrize("source", ["garmin", "strava", "intervals", "runalyze"])
    def test_returns_correct_instance(self, source):
        ext = get_extractor(source)
        assert isinstance(ext, BaseExtractor)
        assert ext.SOURCE == source

    def test_case_insensitive(self):
        ext = get_extractor("Garmin")
        assert ext.SOURCE == "garmin"

    def test_unknown_source_raises(self):
        with pytest.raises(KeyError, match="Unknown source"):
            get_extractor("unknown_platform")

    def test_returns_new_instance_each_call(self):
        a = get_extractor("garmin")
        b = get_extractor("garmin")
        assert a is not b


# ─────────────────────────────────────────────────────────────────────
# 조건 3 & 4: extract_activity_core 반환 dict 검증
# ─────────────────────────────────────────────────────────────────────


class TestCoreKeysConsistency:
    """조건 3: 필수 키 포함, 조건 4: 허용된 컬럼명만 사용."""

    @pytest.mark.parametrize("source", ["garmin", "strava", "intervals", "runalyze"])
    def test_required_keys_present(self, source):
        """조건 3: source, source_id, activity_type, start_time 필수."""
        ext = get_extractor(source)
        raw = _load_fixture(source)
        core = ext.extract_activity_core(raw)

        for key in _REQUIRED_CORE_KEYS:
            assert key in core, (
                f"[{source}] extract_activity_core() 반환에 필수 키 '{key}' 누락"
            )

    @pytest.mark.parametrize("source", ["garmin", "strava", "intervals", "runalyze"])
    def test_all_keys_are_valid_columns(self, source):
        """조건 4: 반환 dict의 모든 key가 activity_summaries 컬럼명과 일치."""
        ext = get_extractor(source)
        raw = _load_fixture(source)
        core = ext.extract_activity_core(raw)

        invalid_keys = set(core.keys()) - _VALID_CORE_KEYS
        assert not invalid_keys, (
            f"[{source}] activity_summaries에 없는 키: {invalid_keys}"
        )

    @pytest.mark.parametrize("source", ["garmin", "strava", "intervals", "runalyze"])
    def test_no_none_values_in_output(self, source):
        """반환 dict에 None 값이 포함되면 안 됨 (None은 키 자체를 제거)."""
        ext = get_extractor(source)
        raw = _load_fixture(source)
        core = ext.extract_activity_core(raw)

        none_keys = [k for k, v in core.items() if v is None]
        assert not none_keys, (
            f"[{source}] None 값을 가진 키가 있음: {none_keys}"
        )


# ─────────────────────────────────────────────────────────────────────
# 조건 5: metric_name이 core 컬럼과 중복 금지
# ─────────────────────────────────────────────────────────────────────


class TestMetricNoDuplicateWithCore:
    """조건 5: extract_activity_metrics() metric_name ∩ activity_summaries 컬럼 = ∅."""

    @pytest.mark.parametrize("source", ["garmin", "strava", "intervals", "runalyze"])
    def test_no_overlap(self, source):
        ext = get_extractor(source)
        raw = _load_fixture(source)
        metrics = ext.extract_activity_metrics(raw)

        metric_names = {m.metric_name for m in metrics}
        overlap = metric_names & _VALID_CORE_KEYS
        assert not overlap, (
            f"[{source}] metric_name이 activity_summaries 컬럼과 중복: {overlap}"
        )


# ─────────────────────────────────────────────────────────────────────
# 조건 6: 모든 MetricRecord에 category 설정
# ─────────────────────────────────────────────────────────────────────


class TestAllMetricsHaveCategory:
    """조건 6: 모든 MetricRecord.category가 non-None, non-empty."""

    @pytest.mark.parametrize("source", ["garmin", "strava", "intervals", "runalyze"])
    def test_category_set(self, source):
        ext = get_extractor(source)
        raw = _load_fixture(source)
        metrics = ext.extract_activity_metrics(raw)

        for m in metrics:
            assert m.category, (
                f"[{source}] metric '{m.metric_name}'에 category가 없음"
            )
            assert isinstance(m.category, str) and len(m.category) > 0

    @pytest.mark.parametrize("source", ["garmin", "strava", "intervals", "runalyze"])
    def test_no_empty_metrics(self, source):
        """모든 반환된 MetricRecord가 is_empty()==False."""
        ext = get_extractor(source)
        raw = _load_fixture(source)
        metrics = ext.extract_activity_metrics(raw)

        for m in metrics:
            assert not m.is_empty(), (
                f"[{source}] metric '{m.metric_name}'이 비어있음"
            )


# ─────────────────────────────────────────────────────────────────────
# 조건 7: distance_m 미터 단위 통일
# ─────────────────────────────────────────────────────────────────────


class TestDistanceUnit:
    """조건 7: 모든 extractor가 distance_m (미터)을 사용."""

    @pytest.mark.parametrize("source", ["garmin", "strava", "intervals", "runalyze"])
    def test_distance_key_is_meters(self, source):
        ext = get_extractor(source)
        raw = _load_fixture(source)
        core = ext.extract_activity_core(raw)

        assert "distance_m" in core, f"[{source}] distance_m 키 없음"
        assert "distance_km" not in core, f"[{source}] distance_km이 있으면 안 됨"
        # minimal fixture의 거리는 모두 ~10km = ~10000m
        assert core["distance_m"] > 5000, (
            f"[{source}] distance_m={core['distance_m']} — 미터 단위가 아닌 것 같음"
        )


# ─────────────────────────────────────────────────────────────────────
# 조건 8: _seconds() 밀리초/초 자동 판별
# ─────────────────────────────────────────────────────────────────────


class TestSecondsHelper:
    """조건 8: Garmin _seconds() 헬퍼 밀리초/초 자동 판별."""

    def test_already_seconds(self):
        assert garmin_seconds(3120) == 3120

    def test_milliseconds_conversion(self):
        # 3,120,000ms = 3120s
        assert garmin_seconds(3120000) == 3120

    def test_none_returns_none(self):
        assert garmin_seconds(None) is None

    def test_boundary_86400(self):
        # 86400초 = 24시간, 이보다 크면 밀리초로 판별
        assert garmin_seconds(86401) == 86  # 86401ms → 86s

    def test_exactly_86400(self):
        # 86400초 = 정확히 24시간 → 초 단위로 유지
        assert garmin_seconds(86400) == 86400

    def test_float_input(self):
        assert garmin_seconds(3120.5) == 3120


# ─────────────────────────────────────────────────────────────────────
# 조건 10: Cross-extractor 일관성
# ─────────────────────────────────────────────────────────────────────


class TestCrossExtractorConsistency:
    """조건 10: 모든 extractor 간 공통 규칙 준수."""

    def test_all_extractors_registered(self):
        """EXTRACTORS에 4개 소스 등록."""
        assert set(EXTRACTORS.keys()) == {"garmin", "strava", "intervals", "runalyze"}

    def test_all_have_unique_source(self):
        """각 extractor의 SOURCE가 고유."""
        sources = [cls.SOURCE for cls in EXTRACTORS.values()]
        assert len(sources) == len(set(sources))

    @pytest.mark.parametrize("source", ["garmin", "strava", "intervals", "runalyze"])
    def test_source_field_matches_class_source(self, source):
        """반환 dict의 source 값이 클래스의 SOURCE와 일치."""
        ext = get_extractor(source)
        raw = _load_fixture(source)
        core = ext.extract_activity_core(raw)
        assert core["source"] == ext.SOURCE

    @pytest.mark.parametrize("source", ["garmin", "strava", "intervals", "runalyze"])
    def test_activity_type_is_normalized(self, source):
        """activity_type이 정규화된 값."""
        ext = get_extractor(source)
        raw = _load_fixture(source)
        core = ext.extract_activity_core(raw)
        # minimal fixture는 모두 running
        assert core["activity_type"] == "running"

    @pytest.mark.parametrize("source", ["garmin", "strava", "intervals", "runalyze"])
    def test_source_url_contains_source_id(self, source):
        """source_url이 source_id를 포함."""
        ext = get_extractor(source)
        raw = _load_fixture(source)
        core = ext.extract_activity_core(raw)
        if "source_url" in core:
            assert core["source_id"] in core["source_url"]

    def test_all_extractors_inherit_base(self):
        """조건 1 재확인: 모든 extractor가 BaseExtractor의 서브클래스."""
        for source, cls in EXTRACTORS.items():
            assert issubclass(cls, BaseExtractor), (
                f"{source}: {cls.__name__}이 BaseExtractor를 상속하지 않음"
            )

    @pytest.mark.parametrize("source", ["garmin", "strava", "intervals", "runalyze"])
    def test_pace_sec_km_reasonable(self, source):
        """avg_pace_sec_km이 있으면 합리적 범위 (2:30~10:00/km = 150~600초)."""
        ext = get_extractor(source)
        raw = _load_fixture(source)
        core = ext.extract_activity_core(raw)
        if "avg_pace_sec_km" in core:
            pace = core["avg_pace_sec_km"]
            assert 150 < pace < 600, (
                f"[{source}] avg_pace_sec_km={pace} — 비합리적 범위"
            )

    @pytest.mark.parametrize("source", ["garmin", "strava", "intervals", "runalyze"])
    def test_duration_sec_reasonable(self, source):
        """duration_sec이 양수이고 합리적 범위 (1분~24시간)."""
        ext = get_extractor(source)
        raw = _load_fixture(source)
        core = ext.extract_activity_core(raw)
        if "duration_sec" in core:
            dur = core["duration_sec"]
            assert 60 <= dur <= 86400, (
                f"[{source}] duration_sec={dur} — 비합리적 범위"
            )

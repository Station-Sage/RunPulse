"""U18a — 스트림 시간축 결정(stream_time) + 추출기 연결 테스트."""
from src.sync.extractors.garmin_extractor import GarminExtractor
from src.sync.extractors.stream_time import resolve_time_axis, stream_meta
from src.sync.extractors.strava_extractor import StravaExtractor


def _raw(keys, rows):
    return {
        "metricDescriptors": [{"key": k, "metricsIndex": i} for i, k in enumerate(keys)],
        "activityDetailMetrics": [{"metrics": r} for r in rows],
    }


def test_sum_elapsed_preferred():
    idx = {"sumElapsedDuration": 0, "directElapsedDuration": 1}
    t, basis, key = resolve_time_axis([[0, 99], [2, 99], [5, 99]], idx)
    assert (t, basis, key) == ([0.0, 2.0, 5.0], "measured", "sumElapsedDuration")


def test_direct_elapsed_fallback():
    t, basis, key = resolve_time_axis([[0], [3]], {"directElapsedDuration": 0})
    assert basis == "measured" and key == "directElapsedDuration" and t == [0.0, 3.0]


def test_timestamp_only_is_derived():
    t, basis, key = resolve_time_axis([[1000000], [1002000], [1005000]], {"directTimestamp": 0})
    assert (t, basis, key) == ([0.0, 2.0, 5.0], "derived", "directTimestamp")


def test_no_key_scaled_times_none():
    t, basis, key = resolve_time_axis([[1], [2]], {"directHeartRate": 0})
    assert t == [None, None] and basis == "scaled" and key is None


def test_partial_none_interpolated_small_ratio_keeps_basis():
    idx = {"sumElapsedDuration": 0}
    rows = [[float(i)] for i in range(40)]
    rows[10] = [None]
    t, basis, _ = resolve_time_axis(rows, idx)
    assert basis == "measured" and t[10] == 10.0


def test_many_none_lowers_basis():
    idx = {"sumElapsedDuration": 0, "directTimestamp": 1}
    rows = [[0.0, 0], [None, 1000], [None, 2000], [3.0, 3000]]
    t, basis, key = resolve_time_axis(rows, idx)
    assert basis == "derived" and key == "sumElapsedDuration" and t[1] == 1.0


def test_non_monotonic_lowers_without_sorting():
    t, basis, _ = resolve_time_axis([[0], [5], [3], [8]], {"sumElapsedDuration": 0})
    assert basis == "derived" and t == [0.0, 5.0, 3.0, 8.0]


def test_garmin_extractor_meta_and_no_index_fallback():
    ex = GarminExtractor()
    rows = ex.extract_activity_streams(_raw(["sumElapsedDuration", "directHeartRate"], [[0, 100], [2, 101], [5, 102]]))
    assert [r["elapsed_sec"] for r in rows] == [0, 2, 5]
    assert rows.meta["time_basis"] == "measured" and rows.meta["median_dt_sec"] == 2.5
    rows = ex.extract_activity_streams(_raw(["directHeartRate"], [[100], [101]]))
    assert [r["elapsed_sec"] for r in rows] == [None, None] and rows.meta["time_basis"] == "scaled"


def test_strava_time_is_measured():
    rows = StravaExtractor().extract_activity_streams({"time": {"data": [0, 1, 2, 4]}, "heartrate": {"data": [1, 2, 3, 4]}})
    assert rows.meta["time_basis"] == "measured" and rows.meta["time_key"] == "time" and rows.meta["span_sec"] == 4.0


def test_stream_meta_empty():
    m = stream_meta([], "unknown", None, 0)
    assert m["span_sec"] is None and m["median_dt_sec"] is None

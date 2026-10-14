"""timefmt — instant 직렬화·활동 현지 벽시계 변환."""
from src.utils.timefmt import to_iso_instant, to_local_wallclock


def test_instant_naive_is_utc():
    assert to_iso_instant("2026-10-01 15:30:00") == "2026-10-01T15:30:00+00:00"


def test_instant_respects_suffix():
    assert to_iso_instant("2026-10-01T15:30:00+09:00") == "2026-10-01T15:30:00+09:00"
    assert to_iso_instant("2026-10-01T15:30:00Z") == "2026-10-01T15:30:00+00:00"


def test_instant_none_and_garbage():
    assert to_iso_instant(None) is None
    assert to_iso_instant("") is None
    assert to_iso_instant("not-a-date") is None


def test_local_wins_and_fake_z_removed():
    assert to_local_wallclock("2026-10-01T08:00:00Z", "2026-10-01T01:00:00Z", 25200) == "2026-10-01T08:00:00"
    assert to_local_wallclock("2026-10-01 08:00:00") == "2026-10-01 08:00:00"
    assert to_local_wallclock("2026-10-01T08:00:00+00:00") == "2026-10-01T08:00:00"


def test_utc_plus_offset():
    assert to_local_wallclock(None, "2026-10-01T17:30:00Z", 25200) == "2026-10-02T00:30:00"
    assert to_local_wallclock(None, "2026-03-08T10:00:00+00:00", -28800) == "2026-03-08T02:00:00"


def test_unknown_offset_falls_back_to_kst():
    assert to_local_wallclock(None, "2026-10-01T15:30:00Z") == "2026-10-02T00:30:00"


def test_nothing_usable():
    assert to_local_wallclock(None, None) is None
    assert to_local_wallclock("garbage", "garbage") is None

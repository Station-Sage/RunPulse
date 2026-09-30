"""format_ko — Coach 규칙 답변 표기 단일 소스."""
from src.utils import format_ko as f


def test_distance_pace_duration():
    assert f.fmt_distance(10.0312) == "10.03km"
    assert f.fmt_distance(None) == "-"
    assert f.fmt_pace(345) == "5:45/km"
    assert f.fmt_pace(344.6) == "5:45/km"
    assert f.fmt_pace(0) == "-"
    assert f.fmt_duration(13223) == "3:40:23"
    assert f.fmt_duration(1500) == "25:00"
    assert f.fmt_gap(90) == "1분 30초"
    assert f.fmt_gap(-45) == "45초"
    assert f.fmt_gap(120) == "2분"


def test_signed_uses_unicode_minus():
    assert f.fmt_signed(-10.7) == "−11"
    assert f.fmt_signed(-3.3) == "−3.3"
    assert f.fmt_signed(2.6) == "+2.6"
    assert f.fmt_signed(0.02) == "0"
    assert f.fmt_signed(None) == "-"


def test_labels():
    assert f.workout_ko("recovery") == "회복 달리기"
    assert f.workout_ko("easy") == "이지런"
    assert f.workout_ko("weird") == "weird"
    assert f.grade_ko("excellent") == "매우 좋음"
    assert f.grade_ko(None) == "정보 없음"


def test_sanitize_raw_floats_and_sec_per_km():
    assert f.sanitize("TSB 12.3456 입니다") == "TSB 12.3 입니다"
    assert f.sanitize("페이스 345초/km 로") == "페이스 5:45/km 로"
    assert f.sanitize("10.03km 5:45/km") == "10.03km 5:45/km"

"""shoe_status — 임계값·상태 경계·문구·대회 보조 문구·정렬."""
import pytest

from src.services import shoe_status as st


@pytest.mark.parametrize("km,expected", [(559.3, "ok"), (560, "soon"), (699.3, "soon"), (700, "replace")])
def test_boundaries_79_9_80_99_9_100(km, expected):
    assert st.status_of(km, 700) == expected


def test_retire_km_overrides_category_default():
    assert st.effective_retire_km("race", None) == 400
    assert st.effective_retire_km("race", 500) == 500
    assert st.effective_retire_km(None, None) == 700


def test_messages():
    assert st.status_message("ok", 10, 700) == "아직 충분해요"
    assert st.status_message("soon", 612, 700) == "교체를 준비할 때예요 (남은 약 88 km)"
    assert st.status_message("replace", 740, 700) == "교체를 권해요 (임계값 +40 km)"


def test_retired_excluded():
    s = st.shoe_state("daily", None, "2026-01-01", 900)
    assert s["status"] == "retired" and s["message"] is None and s["remaining_km"] is None


def test_race_prep_note():
    assert st.race_prep_note("race", "soon", 10)
    assert st.race_prep_note("race", "ok", 10) is None
    assert st.race_prep_note("daily", "replace", 10) is None
    assert st.race_prep_note("race", "replace", 30) is None
    assert st.shoe_state("race", None, None, 350, 5)["note"]


def test_sort_and_headline():
    shoes = [
        {"name": "A", "status": "ok", "last_used": "2026-05-09"},
        {"name": "B", "status": "soon", "last_used": "2026-05-01"},
        {"name": "C", "status": "soon", "last_used": "2026-05-05"},
        {"name": "D", "status": "replace", "last_used": None},
    ]
    assert [s["name"] for s in sorted(shoes, key=st.sort_key)] == ["D", "C", "B", "A"]
    assert st.headline(shoes) == "D, 교체를 권해요"
    assert st.headline([shoes[0]]) == "모든 신발이 충분히 남았어요"

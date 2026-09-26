"""P7-PRED-53: 대회 확인 서비스."""
import pytest

from src.services import race_result_service as rr
from tests.helpers_pred import mem_conn, seed_run


def test_confirm_update_remove():
    c = mem_conn()
    aid = seed_run(c, sid="1", name="양천 마라톤 10k")
    assert rr.confirm(c, aid, "allout", official_time_sec=2653)["effort"] == "allout"
    assert rr.confirm(c, aid, "paced")["official_time_sec"] is None
    assert rr.remove(c, aid) and rr.get(c, aid) is None


def test_validation():
    c = mem_conn()
    aid = seed_run(c, sid="1")
    with pytest.raises(ValueError):
        rr.confirm(c, aid, "hard")
    with pytest.raises(ValueError):
        rr.confirm(c, aid, "allout", official_time_sec=30)
    with pytest.raises(LookupError):
        rr.confirm(c, 999, "allout")


def test_candidates():
    c = mem_conn()
    seed_run(c, sid="1", date="2026-09-12", name="Forest run", event_type="race")
    seed_run(c, sid="2", date="2026-09-10", name="템포 10k")
    b = seed_run(c, sid="3", date="2026-09-05", name="하프 대회")
    seed_run(c, sid="4", date="2026-09-01", name="Easy")
    rr.confirm(c, b, "fun")
    got = rr.candidates(c, "2026-08-01")
    assert [(x["name"], x["confirmed_effort"]) for x in got] == [("Forest run", None), ("하프 대회", "fun")]

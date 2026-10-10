"""지표 해금 진행도 — 빈 DB 0일, 첫 러닝 기점 일수, 임계 도달 시 unlocked."""
from src.services.metric_unlock_service import get_unlock_progress
from tests.helpers_pred import mem_conn, seed_run


def test_empty_db_all_locked():
    out = get_unlock_progress(mem_conn(), "2026-10-10")
    assert all(v["have_days"] == 0 and not v["unlocked"] for v in out.values())
    assert out["ctl"]["required_days"] == 42 and out["utrs"]["basis"] == "wellness_days"


def test_span_counts_from_first_run():
    c = mem_conn()
    seed_run(c, sid="a", date="2026-09-01", dist=5000)
    out = get_unlock_progress(c, "2026-10-10")
    assert out["ctl"]["have_days"] == 40 and not out["ctl"]["unlocked"]
    assert out["cirs"]["unlocked"]
    seed_run(c, sid="b", date="2026-08-30", dist=5000)
    assert get_unlock_progress(c, "2026-10-10")["tsb"]["unlocked"]

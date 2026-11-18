"""match_hooks — 신규 활동 0건이면 skip, 예외는 error 로 반환, 신규 있으면 최근 N주 매칭 실행."""
import sqlite3
from unittest.mock import patch

from src.db_setup import create_tables
from src.training.match_hooks import count_canonical, run_post_sync_match


def _db(tmp_path):
    p = str(tmp_path / "r.db")
    conn = sqlite3.connect(p)
    create_tables(conn)
    conn.commit()
    conn.close()
    return p


def test_skip_when_no_new_activities(tmp_path):
    assert run_post_sync_match(_db(tmp_path), 0) == {"skipped": "no_new_activities"}


def test_runs_weeks_when_new(tmp_path):
    with patch("src.training.matcher.match_week_activities", return_value=2) as m:
        res = run_post_sync_match(_db(tmp_path), 1, weeks=3)
    assert res == {"weeks": 3, "matched": 6} and m.call_count == 3


def test_error_is_reported_not_raised(tmp_path):
    with patch("src.training.matcher.match_week_activities", side_effect=RuntimeError("boom")):
        assert run_post_sync_match(_db(tmp_path), 1)["error"] == "boom"


def test_count_canonical_empty(tmp_path):
    assert count_canonical(_db(tmp_path)) == 0

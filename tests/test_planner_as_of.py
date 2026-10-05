from unittest.mock import patch

from src.training import planner
from tests.helpers_pred import mem_conn


def test_as_of_passthrough_and_default():
    c = mem_conn()
    seen = {}
    real = planner.get_latest_fitness

    def spy(conn, as_of=None):
        seen["a"] = as_of
        return real(conn, as_of)

    with patch.object(planner, "get_latest_fitness", spy):
        planner.generate_weekly_plan(c, week_start=__import__("datetime").date(2030, 1, 7), as_of=__import__("datetime").date(2030, 1, 1))
        assert seen["a"].isoformat() == "2030-01-01"
        planner.generate_weekly_plan(c, week_start=__import__("datetime").date(2030, 1, 7))
        assert seen["a"] is None

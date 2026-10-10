import json

import pytest

from src.services import garmin_cleanup as gc


class FakeClient:
    def __init__(self, missing=(), fail=(), flaky=()):
        self.missing, self.fail, self.flaky = set(missing), set(fail), set(flaky)
        self.deleted, self.calls = [], {}

    def get_workout_by_id(self, wid):
        if wid in self.missing:
            raise RuntimeError("404 Not Found")

    def delete_workout(self, wid):
        self.calls[wid] = self.calls.get(wid, 0) + 1
        if wid in self.fail or (wid in self.flaky and self.calls[wid] == 1):
            raise RuntimeError("500 boom")
        self.deleted.append(wid)


def _seed(db_conn, status="applied"):
    blob = {"deleted": [{"id": 1, "date": "2026-10-14", "garmin_workout_id": "111"},
                        {"id": 2, "date": "2026-10-12", "garmin_workout_id": "222"},
                        {"id": 3, "date": "2026-10-16", "garmin_workout_id": None},
                        {"id": 4, "date": "2026-10-17", "garmin_workout_id": "444"}], "inserted": []}
    db_conn.execute("INSERT INTO plan_replans(id, goal_id, anchor_monday, start_km, start_source, status, replaced_json) VALUES (1, 1, '2026-10-12', 30, 'user', ?, ?)",
                    (status, json.dumps(blob)))
    db_conn.commit()


def test_targets_sorted_and_filtered(db_conn):
    _seed(db_conn)
    assert [t["date"] for t in gc.targets(db_conn, 1)] == ["2026-10-12", "2026-10-14", "2026-10-17"]


def test_cleanup_partial_failure_and_retry(db_conn):
    _seed(db_conn)
    c = FakeClient(missing={"222"}, fail={"444"}, flaky={"111"})
    r = gc.cleanup(db_conn, 1, c)
    assert (r["deleted"], r["missing"]) == (1, 1) and r["failed"][0]["date"] == "2026-10-17"
    assert c.calls["444"] == 2 and c.calls["111"] == 2
    assert [t["garmin_workout_id"] for t in gc.targets(db_conn, 1)] == ["444"]


def test_rejects_undone_and_missing(db_conn):
    _seed(db_conn, status="undone")
    with pytest.raises(gc.CleanupError) as e:
        gc.targets(db_conn, 1)
    assert e.value.code == "NOT_APPLIED"
    with pytest.raises(gc.CleanupError) as e:
        gc.cleanup(db_conn, 99, FakeClient())
    assert e.value.code == "NO_REPLAN"

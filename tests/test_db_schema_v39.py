"""스키마 v39 — goals.race_id + race_calendar 백필."""
import glob
import json
import sqlite3

import pytest

from src.db_schema_v38 import ensure_v38
from src.db_schema_v39 import NOTE_CREATED_DATE, dry_run, ensure_v39, resync_cache

GOALS = """CREATE TABLE goals (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, race_date TEXT,
distance_km REAL NOT NULL, target_time_sec INTEGER, target_pace_sec_km INTEGER,
status TEXT NOT NULL DEFAULT 'active', created_at TEXT NOT NULL DEFAULT (datetime('now')),
distance_label TEXT, weekly_km_target REAL, plan_weeks INTEGER)"""


def _mk(c):
    c.execute("CREATE TABLE planned_workouts (id INTEGER PRIMARY KEY, date TEXT, source TEXT)")
    c.execute("CREATE TABLE race_results (id INTEGER PRIMARY KEY)")
    c.execute("CREATE TABLE activity_summaries (id INTEGER PRIMARY KEY, source TEXT, source_id TEXT, start_time TEXT)")
    c.execute("CREATE TABLE source_payloads (id INTEGER PRIMARY KEY, source TEXT, entity_type TEXT, entity_id TEXT,"
              " activity_id INTEGER, payload TEXT)")
    c.execute(GOALS)
    ensure_v38(c)
    c.commit()


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    _mk(c)
    return c


def _goal(c, name="G", race_date="2026-05-01", status="completed", dist=42.195, tt=None, created="2026-01-01 00:00:00"):
    c.execute("INSERT INTO goals (name,race_date,distance_km,target_time_sec,status,created_at) VALUES (?,?,?,?,?,?)",
              (name, race_date, dist, tt, status, created))


def _race(c, **kw):
    v = dict(name="R", race_date="2026-05-01", distance_km=42.195, priority="B", status="done")
    v.update(kw)
    c.execute(f"INSERT INTO race_calendar ({','.join(v)}) VALUES ({','.join('?' * len(v))})", tuple(v.values()))


def _races(c):
    c.row_factory = sqlite3.Row
    return [dict(r) for r in c.execute("SELECT * FROM race_calendar ORDER BY id")]


def test_empty_and_idempotent(conn):
    assert dry_run(conn)["needs_column"]
    r = ensure_v39(conn)
    assert r["goals"] == 0
    ensure_v39(conn)
    assert not dry_run(conn)["needs_column"]


def test_completed_creates_done_a_race_and_idempotent(conn):
    _goal(conn, tt=12000)
    _goal(conn, name="H", race_date="2026-06-01", dist=21.0975)
    r = ensure_v39(conn)
    assert r["created"] == 2
    rs = _races(conn)
    assert [(x["priority"], x["status"], x["adapt_choice"], x["plan_state"], x["origin"]) for x in rs] == \
        [("A", "done", "adapt", "applied", "goal")] * 2
    assert (rs[0]["goal_type"], rs[0]["goal_value"], rs[1]["goal_type"]) == ("time", 12000, "finish")
    assert conn.execute("SELECT COUNT(*) FROM goals WHERE race_id IS NOT NULL").fetchone()[0] == 2
    ensure_v39(conn)
    assert len(_races(conn)) == 2


def test_done_bc_reuse_promoted_and_reported(conn):
    _race(conn, priority="B", name="Old")
    _goal(conn)
    r = ensure_v39(conn)
    assert r["reused"] == 1 and r["created"] == 0
    assert r["promotions"] == [{"race_id": 1, "name": "Old", "date": "2026-05-01", "prev_priority": "B", "goal_id": 1}]
    assert _races(conn)[0]["priority"] == "A"
    assert ensure_v39(conn)["promotions"] == []


def test_active_reuses_planned_and_promotes(conn):
    _race(conn, status="planned", priority="C")
    _goal(conn, status="active")
    ensure_v39(conn)
    rs = _races(conn)
    assert len(rs) == 1 and rs[0]["priority"] == "A"


def test_active_plan_state_by_date_range(conn):
    conn.execute("INSERT INTO planned_workouts (date, source) VALUES ('2026-04-10','planner')")
    _goal(conn, status="active")
    _goal(conn, name="X", race_date="2026-09-01", status="active", created="2026-08-01 00:00:00")
    with pytest.raises(sqlite3.IntegrityError):
        ensure_v39(conn)  # A 플래너드 2개 -> ux_race_one_a 위반 시 전체 롤백
    assert dry_run(conn)["needs_column"]
    conn.execute("UPDATE goals SET status='cancelled' WHERE id=2")
    ensure_v39(conn)
    rs = _races(conn)
    assert rs[0]["plan_state"] == "applied" and rs[0]["status"] == "planned" and rs[0]["adapt_choice"] == "adapt"


def test_active_without_date_stays_null(conn):
    _goal(conn, race_date=None, status="active")
    r = ensure_v39(conn)
    assert r["no_date_active"] == 1 and _races(conn) == []
    assert conn.execute("SELECT race_id FROM goals").fetchone()[0] is None


def test_inactive_without_date_uses_created_date_with_offset(conn):
    cur = conn.execute("INSERT INTO activity_summaries (source,source_id,start_time) VALUES ('garmin','a','2026-01-02T09:00:00')")
    conn.execute("INSERT INTO source_payloads (source,entity_type,entity_id,activity_id,payload) VALUES (?,?,?,?,?)",
                 ("garmin", "activity_summary", "a", cur.lastrowid,
                  json.dumps({"startTimeGMT": "2026-01-02 00:00:00", "startTimeLocal": "2026-01-02 09:00:00"})))
    _goal(conn, race_date=None, created="2026-01-01 15:30:00")
    ensure_v39(conn)
    r = _races(conn)[0]
    assert r["race_date"] == "2026-01-02" and r["note"] == NOTE_CREATED_DATE
    assert conn.execute("SELECT race_date FROM goals").fetchone()[0] is None


def test_inactive_without_date_server_local_fallback(conn):
    _goal(conn, race_date=None, created="2026-01-01 12:00:00")
    ensure_v39(conn)
    exp = conn.execute("SELECT date('2026-01-01 12:00:00','localtime')").fetchone()[0]
    assert _races(conn)[0]["race_date"] == exp


def test_cancelled_goal_makes_cancelled_race_and_future_counted(conn):
    _goal(conn, status="cancelled")
    _goal(conn, name="F", race_date="2099-01-01")
    r = ensure_v39(conn)
    rs = _races(conn)
    assert (rs[0]["status"], rs[0]["plan_state"], rs[1]["status"]) == ("cancelled", "none", "done")
    assert r["future_completed"] == 1


def test_resync_cache(conn):
    _goal(conn)
    ensure_v39(conn)
    conn.execute("UPDATE goals SET race_date='2026-05-08' WHERE id=1")
    d = resync_cache(conn)
    assert len(d) == 1 and _races(conn)[0]["race_date"] == "2026-05-08"


def test_backup_file_created_and_failure_blocks(tmp_path):
    p = tmp_path / "running.db"
    c = sqlite3.connect(p)
    _mk(c)
    _goal(c)
    c.commit()
    ensure_v39(c)
    assert len(glob.glob(str(p) + ".pre-v39-*")) == 1
    assert sqlite3.connect(glob.glob(str(p) + ".pre-v39-*")[0]).execute("SELECT COUNT(*) FROM goals").fetchone()[0] == 1


def test_invariant3_blocks_index(conn):
    _goal(conn, status="active")
    ensure_v39(conn)
    conn.execute("UPDATE race_calendar SET status='cancelled'")
    from src.db_schema_v39 import _check_invariant3
    with pytest.raises(RuntimeError):
        _check_invariant3(conn)

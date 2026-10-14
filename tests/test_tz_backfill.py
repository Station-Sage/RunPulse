"""tz_backfill 단위 테스트 — dry-run 무변경, 적용, 되돌리기, 그룹 재평가 (TZ T4)."""
import json

from src.import_export.tz_backfill import list_run, revert_run, run_backfill


class _Lookup:
    available = False


def _payload(conn, source, entity, eid, data, activity_id=None):
    conn.execute("INSERT INTO source_payloads (source, entity_type, entity_id, activity_id, payload)"
                 " VALUES (?,?,?,?,?)", (source, entity, eid, activity_id, json.dumps(data)))


def _setup(conn):
    _payload(conn, "garmin", "activity_summary", "g1",
             {"startTimeGMT": "2026-05-01 00:30:20", "startTimeLocal": "2026-05-01 08:30:20", "distance": 10000})
    cur = conn.execute("INSERT INTO activity_summaries (source, source_id, activity_type, start_time, distance_m)"
                       " VALUES ('strava','s1','running','2026-05-01T09:30:00',10000)")
    _payload(conn, "strava", "csv_export", "s1",
             {"tz_source": "fallback", "start_date_utc": "2026-05-01T00:30:00",
              "start_time": "2026-05-01T09:30:00", "distance_km": 10}, cur.lastrowid)
    conn.commit()


def _start(conn):
    return conn.execute("SELECT start_time FROM activity_summaries WHERE source_id='s1'").fetchone()[0]


def test_dry_run_changes_nothing(db_conn):
    _setup(db_conn)
    r = run_backfill(db_conn, None, lookup=_Lookup(), run_id="r1")
    assert r["checked"] == 1 and r["changed"] == 1 and not r["applied"]
    assert _start(db_conn) == "2026-05-01T09:30:00"
    assert not list_run(db_conn, "r1")


def test_apply_then_revert(db_conn):
    _setup(db_conn)
    r = run_backfill(db_conn, None, apply=True, lookup=_Lookup(), run_id="r2")
    assert r["changed"] == 1 and _start(db_conn) == "2026-05-01T08:30:00"
    assert list_run(db_conn, "r2")[0]["to_source"].startswith("peer_")
    dry = revert_run(db_conn, "r2")
    assert dry["reverted"] == 1 and _start(db_conn) == "2026-05-01T08:30:00"
    rev = revert_run(db_conn, "r2", apply=True)
    assert rev["reverted"] == 1 and _start(db_conn) == "2026-05-01T09:30:00"
    p = json.loads(db_conn.execute("SELECT payload FROM source_payloads WHERE entity_id='s1'").fetchone()[0])
    assert p["tz_pinned"] and p["tz_source"] == "fallback"
    again = run_backfill(db_conn, None, apply=True, lookup=_Lookup())
    assert again["checked"] == 0  # 고정된 행은 재교정 제외


def test_limit_and_confirmed_skipped(db_conn):
    _setup(db_conn)
    assert run_backfill(db_conn, None, limit=0, lookup=_Lookup())["checked"] == 0
    run_backfill(db_conn, None, apply=True, lookup=_Lookup())
    assert run_backfill(db_conn, None, lookup=_Lookup())["checked"] == 0  # peer_direct 는 확정 등급

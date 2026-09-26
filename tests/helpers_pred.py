"""예측 v2 테스트 공용 시드 헬퍼(P7-PRED-11)."""
import sqlite3

from src.db_setup import create_tables


def mem_conn():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    return c


def seed_run(c, *, source="garmin", sid="1", date="2026-05-09", t="07:30:00", name="Run", dist=10000.0,
             moving=2700, elapsed=None, avg_hr=150, max_hr=175, event_type=None, group=None, atype="running",
             lat=37.52, lon=126.92, temp=None):
    c.execute(
        "INSERT INTO activity_summaries (source, source_id, name, activity_type, start_time, distance_m, moving_time_sec,"
        " elapsed_time_sec, duration_sec, avg_hr, max_hr, event_type, matched_group_id, start_lat, start_lon, avg_temperature)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (source, sid, name, atype, f"{date} {t}", dist, moving, elapsed or moving, elapsed or moving, avg_hr, max_hr,
         event_type, group, lat, lon, temp))
    return c.execute("SELECT last_insert_rowid()").fetchone()[0]


def seed_laps(c, aid, laps, source="garmin"):
    """laps: [(dist_m, dur_s, hr, itype, gap_speed_ms|None, max_hr|None)]"""
    for i, (d, s, hr, it, gap, mx) in enumerate(laps):
        c.execute("INSERT INTO activity_laps (activity_id, source, lap_index, distance_m, duration_sec, avg_hr, max_hr,"
                  " lap_trigger, gap_speed_ms) VALUES (?,?,?,?,?,?,?,?,?)", (aid, source, i, d, s, hr, mx, it, gap))

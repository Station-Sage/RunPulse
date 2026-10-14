"""tz_peers / strava_tz / strava_tz_apply 단위 테스트 (TZ T2/T3)."""
import json
from datetime import datetime

from src.import_export.strava_tz import (
    may_overwrite, rank_of, resolve_strava_start, StravaTzLookup,
)
from src.import_export.strava_tz_apply import TzContext, apply_to_existing, tz_payload_fields
from src.utils.dedup import distance_matches
from src.utils.tz_peers import PeerTime, PeerTzIndex

UTC = datetime(2026, 5, 1, 0, 30, 0)  # 현지(+9) 09:30


def _payload(conn, source, entity, eid, data, activity_id=None):
    conn.execute("INSERT INTO source_payloads (source, entity_type, entity_id, activity_id, payload)"
                 " VALUES (?,?,?,?,?)", (source, entity, eid, activity_id, json.dumps(data)))


def _garmin(conn, sid="g1", gmt="2026-05-01 00:30:20", local="2026-05-01 09:30:20", dist=10000):
    _payload(conn, "garmin", "activity_summary", sid,
             {"startTimeGMT": gmt, "startTimeLocal": local, "distance": dist})


def test_distance_matches():
    assert distance_matches(0, 0)
    assert distance_matches(10000, 10900)
    assert not distance_matches(10000, 13000)
    assert not distance_matches(0, 100)


def test_rank_and_overwrite():
    assert rank_of("peer_direct:garmin") == 4
    assert rank_of(None) == 99
    assert may_overwrite("api_payload", "fallback")
    assert not may_overwrite("fallback", "peer_direct:garmin")
    assert not may_overwrite("api_payload", None)


def test_peer_direct_offset(db_conn):
    _garmin(db_conn)
    idx = PeerTzIndex.build(db_conn)
    m = idx.lookup(UTC, 10000)
    assert m and m.offset_sec == 9 * 3600 and m.grade == "direct" and m.source == "garmin"


def test_peer_outside_tolerance_or_distance(db_conn):
    _garmin(db_conn, gmt="2026-05-01 00:35:00", local="2026-05-01 09:35:00")
    idx = PeerTzIndex.build(db_conn)
    assert idx.lookup(UTC, 10000) is None
    _garmin(db_conn, sid="g2")
    assert PeerTzIndex.build(db_conn).lookup(UTC, 30000) is None


def test_peer_irregular_offset_discarded(db_conn):
    _garmin(db_conn, local="2026-05-01 09:50:20")  # 오프셋 9h20m — 15분 배수 아님
    assert PeerTzIndex.build(db_conn).lookup(UTC, 10000) is None


def test_derived_only_when_unique(db_conn):
    _payload(db_conn, "runalyze", "activity_summary", "r1", {"datetime": "2026-05-01 09:30:00", "distance": 10})
    m = PeerTzIndex.build(db_conn).lookup(UTC, 10000)
    assert m and m.grade == "derived" and m.offset_sec == 9 * 3600
    _payload(db_conn, "runalyze", "activity_summary", "r2", {"datetime": "2026-05-01 09:30:30", "distance": 10})
    assert PeerTzIndex.build(db_conn).lookup(UTC, 10000) is None


def test_direct_conflict_uses_source_priority(db_conn):
    _garmin(db_conn)
    _payload(db_conn, "intervals", "activity_summary", "i1",
             {"start_date": "2026-05-01T00:30:10", "start_date_local": "2026-05-01T08:30:10", "distance": 10000})
    m = PeerTzIndex.build(db_conn).lookup(UTC, 10000)
    assert m.source == "garmin" and m.offset_sec == 9 * 3600 and len(m.conflicts) == 2


def test_chain_order(db_conn):
    _garmin(db_conn)
    idx = PeerTzIndex.build(db_conn)
    api = {"start_date_local": "2026-05-01T17:30:00Z"}
    assert resolve_strava_start(db_conn, "s", UTC, 10000, api=api, peers=idx)[1] == "api_payload"
    fit = datetime(2026, 5, 1, 8, 30, 0)
    assert resolve_strava_start(db_conn, "s", UTC, 10000, api={}, fit_local=fit, peers=idx) == (
        "2026-05-01T08:30:00", "fit_local", None)
    local, src, peer = resolve_strava_start(db_conn, "s", UTC, 10000, api={}, peers=idx)
    assert (local, src) == ("2026-05-01T09:30:00", "peer_direct:garmin") and peer["mode"] == "direct"


def test_neighbor_then_fallback(db_conn):
    _garmin(db_conn, gmt="2026-05-01 03:00:00", local="2026-05-01 12:00:00")
    idx = PeerTzIndex.build(db_conn)
    local, src, _ = resolve_strava_start(db_conn, "s", UTC, 5000, api={}, peers=idx)
    assert (local, src) == ("2026-05-01T09:30:00", "neighbor:garmin")
    far = datetime(2026, 5, 20, 0, 0, 0)
    assert resolve_strava_start(db_conn, "s", far, 5000, api={}, peers=idx)[1] == "fallback"
    assert resolve_strava_start(db_conn, "s", far, 5000, api={}, peers=None)[0] == "2026-05-20T09:00:00"


def test_lookup_no_network_on_init():
    lk = StravaTzLookup(None)
    assert not lk.available and lk.status == "config 없음" and lk.fetch("1") is None


def test_tz_context_summary_and_borrow(db_conn):
    _garmin(db_conn)
    tz = TzContext(db_conn, None)
    local, src, _ = tz.resolve("s1", UTC, 10000)
    assert src == "peer_direct:garmin"
    s = tz.summary()
    assert s["tz_resolved"] == {"peer_direct": 1} and s["tz_lookup_status"] == "config 없음"
    assert "시간대 교차소스 1건" in tz.log_line()
    # 확정된 배치 행은 이웃 차용에 쓰인다
    later = datetime(2026, 5, 1, 4, 0, 0)
    assert tz.resolve("s2", later, 3000)[1].startswith("neighbor:")
    assert any(p.source == "strava" for p in tz.peers._extra)


def test_tz_payload_fields():
    f = tz_payload_fields(UTC, "peer_direct:garmin", {"mode": "direct"})
    assert f == {"tz_source": "peer_direct:garmin", "start_date_utc": "2026-05-01T00:30:00",
                 "tz_peer": {"mode": "direct"}}


def _strava_row(conn, sid, start, payload):
    cur = conn.execute("INSERT INTO activity_summaries (source, source_id, activity_type, start_time)"
                       " VALUES ('strava', ?, 'running', ?)", (sid, start))
    _payload(conn, "strava", "csv_export", sid, payload, cur.lastrowid)


def test_apply_to_existing_rank_rules(db_conn):
    _strava_row(db_conn, "a", "2026-05-01T09:30:00", {"tz_source": "fallback"})
    assert apply_to_existing(db_conn, "a", "2026-05-01T08:30:00", "peer_direct:garmin", {"mode": "direct"})
    st = db_conn.execute("SELECT start_time FROM activity_summaries WHERE source_id='a'").fetchone()[0]
    assert st == "2026-05-01T08:30:00"
    p = json.loads(db_conn.execute("SELECT payload FROM source_payloads WHERE entity_id='a'").fetchone()[0])
    assert p["tz_source"] == "peer_direct:garmin" and p["tz_history"][0]["from_source"] == "fallback"
    assert not apply_to_existing(db_conn, "a", "2026-05-01T09:30:00", "fallback", None)  # 하향 금지


def test_apply_to_existing_protects_manual_and_pinned(db_conn):
    _strava_row(db_conn, "m", "2026-05-01T09:30:00", {})  # tz_source 없음 (수동 보정 행 등)
    _strava_row(db_conn, "p", "2026-05-01T09:30:00", {"tz_source": "fallback", "tz_pinned": True})
    assert not apply_to_existing(db_conn, "m", "2026-05-01T08:30:00", "api_payload", None)
    assert not apply_to_existing(db_conn, "p", "2026-05-01T08:30:00", "api_payload", None)


def _csv(tmp_path, rows):
    p = tmp_path / "activities.csv"
    lines = ["Activity ID,Activity Date,Activity Name,Activity Type,Distance,Moving Time"]
    lines += [f"{i},\"{d}\",n,Run,{dist},3000" for i, d, dist in rows]
    p.write_text("\n".join(lines), encoding="utf-8")
    return p


def test_csv_import_uses_peer_and_reimport_protects(db_conn, tmp_path):
    from src.import_export.strava_csv import import_strava_activities

    _garmin(db_conn)
    p = _csv(tmp_path, [("101", "May 1, 2026, 12:30:00 AM", "10000"),
                        ("102", "Jun 1, 2026, 12:30:00 AM", "5000")])
    r = import_strava_activities(db_conn, p)
    assert r["inserted"] == 2 and r["tz_resolved"] == {"peer_direct": 1, "fallback": 1}
    assert r["tz_lookup_status"] == "config 없음" and r["tz_backfill_pending"] == 1
    st = dict(db_conn.execute("SELECT source_id, start_time FROM activity_summaries WHERE source='strava'"))
    assert st["101"] == "2026-05-01T09:30:00" and st["102"] == "2026-06-01T09:30:00"
    pl = json.loads(db_conn.execute("SELECT payload FROM source_payloads WHERE entity_id='102'").fetchone()[0])
    assert pl["tz_source"] == "fallback" and pl["start_date_utc"] == "2026-06-01T00:30:00"
    # 재가져오기: 같은 해석 → 변경 없음, 더 높은 순위(피어 추가) → 상향
    r2 = import_strava_activities(db_conn, p)
    assert r2["skipped"] == 2
    _payload(db_conn, "intervals", "activity_summary", "i9",
             {"start_date": "2026-06-01T00:30:00", "start_date_local": "2026-06-01T08:30:00", "distance": 5000})
    import_strava_activities(db_conn, p)
    st = dict(db_conn.execute("SELECT source_id, start_time FROM activity_summaries WHERE source='strava'"))
    assert st["102"] == "2026-06-01T08:30:00"

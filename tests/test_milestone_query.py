"""milestone_query + GET /api/v1/library/milestones — 필터·커서·종류 수·상한 (ADR-057)."""
import sqlite3

import pytest
from flask import Flask

from src.db_setup import create_tables, migrate_db
from src.services import milestone_query as Q

URL = "/api/v1/library/milestones"


def _seed(conn):
    rows = [("distance_threshold", "2026-01-05", "누적 100km 돌파"), ("goal_set", "2026-01-10", "목표 설정: A"),
            ("metric_recompute", "2026-01-11", "RRI 재계산"), ("race_finish", "2026-02-01", "10K 완주"),
            ("goal_changed", "2026-02-02", "목표 수정: A"), ("goal_changed", "2026-02-03", "목표 수정: A"),
            ("goal_changed", "2026-02-04", "목표 수정: A")]
    for t, d, title in rows:
        conn.execute("INSERT INTO milestones(type, date, title) VALUES (?,?,?)", (t, d, title))
    conn.commit()


def test_parse_helpers():
    assert Q.parse_types("pb, goal_set") == ["pb", "goal_set"] and Q.parse_types("") is None
    assert Q.parse_cursor("2026-01-01:5") == ("2026-01-01", 5) and Q.parse_cursor(None) is None
    for bad in ("x;drop", "A"):
        with pytest.raises(ValueError):
            Q.parse_types(bad)
    with pytest.raises(ValueError):
        Q.parse_cursor("2026-01-01")


def test_list_pages_hidden_and_counts(db_conn):
    _seed(db_conn)
    p1 = Q.list_milestones(db_conn, limit=4)
    assert [m["date"] for m in p1["items"]] == ["2026-02-04", "2026-02-03", "2026-02-02", "2026-02-01"]
    p2 = Q.list_milestones(db_conn, before=Q.parse_cursor(p1["next_before"]), limit=4)
    assert [m["type"] for m in p2["items"]] == ["goal_set", "distance_threshold"] and p2["next_before"] is None
    counts = {c["type"]: c["count"] for c in p1["type_counts"]}
    assert "metric_recompute" not in counts and counts["goal_changed"] == 3
    only = Q.list_milestones(db_conn, types=["race_finish", "pb"])
    assert [m["title"] for m in only["items"]] == ["10K 완주"]


def test_diversify_per_type_cap():
    items = [{"type": "goal_changed"}] * 4 + [{"type": "distance_threshold"}, {"type": "pb"}]
    out = Q.diversify(items, per_type=2, total=8)
    assert [m["type"] for m in out] == ["goal_changed", "goal_changed", "distance_threshold", "pb"]
    assert len(Q.diversify(items, per_type=9, total=3)) == 3


@pytest.fixture
def client(tmp_path):
    f = tmp_path / "running.db"
    c = sqlite3.connect(str(f))
    create_tables(c)
    migrate_db(c)
    _seed(c)
    c.close()
    import src.api.routes_library_milestones as mod
    orig = mod.db_path
    mod.db_path = lambda: f
    app = Flask(__name__)
    from src.api import api_bp
    app.register_blueprint(api_bp)
    with app.test_client() as cl:
        yield cl, mod
    mod.db_path = orig


def test_route_ok_and_validation(client):
    cl, mod = client
    r = cl.get(f"{URL}?limit=2&type=goal_changed")
    assert r.status_code == 200
    d = r.get_json()["data"]
    assert len(d["items"]) == 2 and d["next_before"] and set(d) == {"items", "next_before", "type_counts"}
    d2 = cl.get(f"{URL}?type=goal_changed&before={d['next_before']}").get_json()["data"]
    assert len(d2["items"]) == 1
    for q in ("limit=0", "limit=x", "before=bad", "type=Bad!"):
        assert cl.get(f"{URL}?{q}").status_code == 400


def test_route_no_db(client, tmp_path):
    cl, mod = client
    mod.db_path = lambda: tmp_path / "nope.db"
    assert cl.get(URL).status_code == 503

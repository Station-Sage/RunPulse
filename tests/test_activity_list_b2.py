"""활동 목록 입력 검증·종목 칩·행 표시 계약 테스트 (V2-AUDIT-INDIV 묶음 B2: A-14·A-17·A-18·A-19·A-31)."""
from __future__ import annotations

import sqlite3

import pytest
from flask import Flask

from src.db_setup import create_tables, migrate_db
from src.services.activity_list_filters import like_pattern, parse_args
from src.services.activity_list_summary import get_facets
from src.services.activity_service import get_activity_list

# (source_id, name, activity_type, start, distance_m, moving_sec)
ROWS = [
    ("g1", "아침 러닝", "running", "2026-09-01T07:00:00", 10_000, 3000),
    ("g2", "100% 노력", "running", "2026-09-02T07:00:00", 5_000, 1500),
    ("g3", "풀 수영", "lap_swimming", "2026-09-03T07:00:00", 500, 600),
    ("g4", "HIIT", "hiit", "2026-09-04T07:00:00", None, 1800),
    ("g5", "요가", "yoga", "2026-09-05T07:00:00", None, 3600),
    ("g6", "a_b 근력", "strength_training", "2026-09-06T07:00:00", None, 2400),
]


@pytest.fixture
def conn(db_conn):
    for sid, name, typ, start, dist, mv in ROWS:
        db_conn.execute(
            "INSERT INTO activity_summaries (source, source_id, name, activity_type, start_time, distance_m,"
            " duration_sec, moving_time_sec) VALUES ('garmin', ?, ?, ?, ?, ?, ?, ?)",
            (sid, name, typ, start, dist, mv, mv))
    db_conn.commit()
    return db_conn


@pytest.mark.parametrize("args, field", [
    ({"sort": "xxx"}, "sort"),
    ({"from": "abc"}, "from"),
    ({"to": "2026-02-30"}, "to"),
    ({"sport_group": "hiit"}, "sport_group"),
    ({"dist_min": "-5"}, "dist_min"),
    ({"dist_min": "nan"}, "dist_min"),
])
def test_parse_args_rejects_silent_fallbacks(args, field):
    with pytest.raises(ValueError, match=field):
        parse_args(args)


def test_parse_args_accepts_to_with_time_and_date_sort():
    f = parse_args({"to": "2026-09-30 23:59:59", "from": "2026-09-01", "sort": "date", "sport_group": "other"})
    assert f["date_to"] == "2026-09-30 23:59:59" and f["sort"] == "date" and f["sport_group"] == "other"


def test_like_pattern_escapes_wildcards():
    assert like_pattern("100%") == "%100\\%%"
    assert like_pattern("a_b") == "%a\\_b%"


def test_q_percent_and_underscore_match_literally(conn):
    names = lambda q: [a["name"] for a in get_activity_list(conn, filters=parse_args({"q": q}))["activities"]]
    assert names("%") == ["100% 노력"]
    assert names("_") == ["a_b 근력"]


def test_facets_group_non_family_types_as_other_last(conn):
    sports = get_facets(conn, {})["sports"]
    assert [s["key"] for s in sports][-1] == "other"
    other = sports[-1]
    assert other == {"key": "other", "label": "기타", "n": 2}
    assert {s["key"] for s in sports} == {"running", "swimming", "strength", "other"}


def test_sport_group_other_lists_hiit_and_yoga(conn):
    r = get_activity_list(conn, filters=parse_args({"sport_group": "other"}))
    assert sorted(a["name"] for a in r["activities"]) == ["HIIT", "요가"]
    assert all(a["sport_label"] == "기타" for a in r["activities"])


def test_list_rows_carry_display_contract(conn):
    rows = {a["name"]: a for a in get_activity_list(conn, filters={}, per_page=10)["activities"]}
    swim = rows["풀 수영"]
    assert swim["sport_family"] == "swimming" and swim["sport_label"] == "수영"
    assert swim["display"]["pace"] == {"value_sec": 120.0, "unit": "/100m", "basis": "moving"}
    assert rows["a_b 근력"]["display"]["show_distance"] is False
    assert rows["아침 러닝"]["display"]["pace"]["unit"] == "/km"


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_file = tmp_path / "running.db"
    c = sqlite3.connect(str(db_file))
    create_tables(c)
    migrate_db(c)
    c.execute("INSERT INTO activity_summaries (source, source_id, name, activity_type, start_time, distance_m)"
              " VALUES ('garmin', 'g1', '러닝', 'running', '2026-09-01T07:00:00', 5000)")
    c.commit()
    c.close()
    import src.api.routes_library as routes_library
    import src.api.routes_library_activities as routes_acts
    monkeypatch.setattr(routes_library, "db_path", lambda: db_file)
    monkeypatch.setattr(routes_acts, "db_path", lambda: db_file)
    app = Flask(__name__)
    app.config["TESTING"] = True
    from src.api import api_bp
    app.register_blueprint(api_bp)
    with app.test_client() as cl:
        yield cl


@pytest.mark.parametrize("qs, field", [
    ("per_page=0", "per_page"), ("per_page=-1", "per_page"), ("per_page=201", "per_page"),
    ("per_page=abc", "per_page"), ("page=-3", "page"), ("page=0", "page"),
    ("sort=xxx", "sort"), ("from=abc", "from"),
])
def test_list_api_rejects_bad_paging_and_filters(client, qs, field):
    res = client.get(f"/api/v1/library/activities?{qs}")
    assert res.status_code == 400
    err = res.get_json()["error"]
    assert err["code"] == "INVALID_PARAM" and field in err["details"]


def test_list_api_accepts_max_per_page(client):
    res = client.get("/api/v1/library/activities?per_page=200&sort=distance")
    assert res.status_code == 200
    assert res.get_json()["meta"]["per_page"] == 200


def test_facets_api_rejects_bad_sort(client):
    res = client.get("/api/v1/library/activities/facets?sort=nope")
    assert res.status_code == 400
    assert "sort" in res.get_json()["error"]["details"]

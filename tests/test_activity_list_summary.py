"""활동 목록 facets·summary·확장 필터/정렬/행 필드 테스트 (U10, A-17/A-18/B-3)."""
import sqlite3
from datetime import date

import pytest

from src.services.activity_list_filters import parse_args
from src.services.activity_list_rows import display_title
from src.services.activity_list_summary import get_facets, get_summary
from src.services.activity_service import get_activity_list

# (name, type, start, km, class, hrss)
ROWS = [
    ("아침 달리기", "running", "2026-08-31T07:00:00", 10, "easy", 60),    # 월요일, 8월 마지막 날
    ("Lunch Run", "running", "2026-09-01T12:00:00", 8, "interval", 90),
    ("서울 하프", "running", "2026-09-06T08:00:00", 21.1, "race", 150),   # 일요일
    ("Long", "running", "2026-09-07T08:00:00", 25, "long_run", 120),
    ("트레드밀", "indoor_running", "2026-09-10T08:00:00", 5, None, None),
    ("근력", "strength", "2026-09-11T08:00:00", None, None, None),
]


@pytest.fixture
def conn(db_conn):
    c = db_conn
    for i, (name, typ, start, km, cls, hrss) in enumerate(ROWS):
        c.execute("INSERT INTO activity_summaries (source, source_id, name, activity_type, start_time, distance_m)"
                  " VALUES ('garmin', ?, ?, ?, ?, ?)", (f"g{i}", name, typ, start, km and km * 1000))
        aid = c.execute("SELECT id FROM activity_summaries WHERE source_id=?", (f"g{i}",)).fetchone()[0]
        if cls:
            c.execute("INSERT INTO metric_store (scope_type, scope_id, metric_name, category, provider, text_value, is_primary)"
                      " VALUES ('activity', ?, 'workout_type_classified', 'classification', 'runpulse:rule_v1', ?, 1)",
                      (str(aid), cls))
        if hrss:
            c.execute("INSERT INTO metric_store (scope_type, scope_id, metric_name, category, provider, numeric_value, is_primary)"
                      " VALUES ('activity', ?, 'hrss', 'load', 'runpulse:formula_v1', ?, 1)", (str(aid), hrss))
    c.commit()
    return c


def test_facets_running_group_counts_indoor(conn):
    f = get_facets(conn, {})
    sports = {s["key"]: s["n"] for s in f["sports"]}
    assert sports == {"running": 5, "strength": 1}
    assert {t["key"]: t["n"] for t in f["types"]} == {"race": 1, "interval": 1, "long": 1, "easy": 1}
    assert f["months"][0] == {"month": "2026-09", "n": 5}


def test_facets_types_respect_sport_group(conn):
    f = get_facets(conn, {"sport_group": "strength"})
    assert f["types"] == []


def test_list_type_filter_maps_long_run(conn):
    r = get_activity_list(conn, filters=parse_args({"type": "long"}))
    assert [a["name"] for a in r["activities"]] == ["Long"]


def test_list_sport_group_month_and_row_fields(conn):
    r = get_activity_list(conn, filters=parse_args({"sport_group": "running", "month": "2026-09"}))
    assert r["total"] == 4
    race = next(a for a in r["activities"] if a["name"] == "서울 하프")
    assert race["is_race"] and race["workout_class"] == "race" and race["load"] == 150.0
    lunch = next(a for a in r["activities"] if a["name"] == "Lunch Run")
    assert lunch["display_title"] == "인터벌 8.0km"
    plain = next(a for a in r["activities"] if a["name"] == "트레드밀")
    assert plain["load"] is None and plain["is_race"] is False


def test_list_sort_load_and_q(conn):
    f = parse_args({"sport_group": "running"}); f["sort"] = "load"
    names = [a["name"] for a in get_activity_list(conn, filters=f)["activities"]]
    assert names[:2] == ["서울 하프", "Long"] and names[-1] == "트레드밀"
    assert [a["name"] for a in get_activity_list(conn, filters=parse_args({"q": "2026-09-10"}))["activities"]] == ["트레드밀"]


def test_parse_args_rejects_bad_values():
    with pytest.raises(ValueError):
        parse_args({"type": "nope"})
    with pytest.raises(ValueError):
        parse_args({"month": "2026-13"})


def test_display_title_keeps_user_names():
    assert display_title("서울 하프", "레이스", 21100) == "서울 하프"
    assert display_title("Morning Run", "이지런", 9300) == "이지런 9.3km"


def test_summary_boundary_week_in_range_only(conn):
    s = get_summary(conn, parse_args({"month": "2026-09", "sport_group": "running"}), today=date(2026, 9, 30))
    first = s["weeks"][0]
    assert first["start"] == "2026-08-31" and first["in_range_only"] is True
    assert first["km"] == 29.1 and first["n"] == 2      # 8/31 10km는 9월이 아니라 제외
    assert s["weeks"][1]["in_range_only"] is False and s["weeks"][1]["km"] == 30.0


def test_summary_month_block_prev_month_pct(conn):
    s = get_summary(conn, parse_args({"month": "2026-09", "sport_group": "running"}), today=date(2026, 9, 30))
    assert s["month"]["n"] == 4 and s["month"]["km"] == 59.1
    assert s["month"]["prev_month_pct"] == round((59.1 - 10) / 10 * 100)
    assert {c["key"]: c["n"] for c in s["month"]["by_class"]} == {"interval": 1, "race": 1, "long": 1}


def test_summary_prev_month_empty_is_null_and_no_month_without_param(conn):
    s = get_summary(conn, parse_args({"month": "2026-08"}), today=date(2026, 9, 30))
    assert s["month"]["prev_month_pct"] is None
    assert "month" not in get_summary(conn, {}, today=date(2026, 9, 30))


def test_summary_avg_12w_ignores_filters_and_needs_history(conn):
    s = get_summary(conn, parse_args({"type": "interval"}), today=date(2026, 9, 30))
    assert s["avg_week_km_12w"] == round(69.1 / 5, 1)  # 이력 31일 → 5주, 필터 무관(러닝 합계 69.1km)
    assert get_summary(conn, {}, today=date(2026, 9, 10))["avg_week_km_12w"] is None


def test_summary_shares_type_filter(conn):
    s = get_summary(conn, parse_args({"type": "interval"}), today=date(2026, 9, 30))
    assert [w["n"] for w in s["weeks"]] == [1]

"""goals.py 테스트."""

import pytest

from src.training.goals import (
    add_goal,
    cancel_goal,
    complete_goal,
    get_active_goal,
    get_goal,
    list_goals,
    update_goal,
)


def test_add_goal_returns_id(db_conn):
    gid = add_goal(db_conn, name="서울마라톤", distance_km=42.195)
    assert isinstance(gid, int)
    assert gid > 0


def test_get_goal(db_conn):
    gid = add_goal(db_conn, name="10K 테스트", distance_km=10.0,
                   race_date="2026-06-01", target_time_sec=2700)
    g = get_goal(db_conn, gid)
    assert g is not None
    assert g["name"] == "10K 테스트"
    assert g["distance_km"] == 10.0
    assert g["race_date"] == "2026-06-01"
    assert g["target_time_sec"] == 2700
    assert g["status"] == "active"


def test_get_goal_not_found(db_conn):
    assert get_goal(db_conn, 9999) is None


def test_list_goals_active_default(db_conn):
    add_goal(db_conn, name="목표1", distance_km=10.0)
    add_goal(db_conn, name="목표2", distance_km=21.1)
    goals = list_goals(db_conn)
    assert len(goals) == 2
    assert all(g["status"] == "active" for g in goals)


def test_list_goals_all(db_conn):
    gid = add_goal(db_conn, name="완료됨", distance_km=42.195)
    complete_goal(db_conn, gid)
    add_goal(db_conn, name="진행중", distance_km=10.0)

    all_goals = list_goals(db_conn, status="all")
    assert len(all_goals) == 2

    active_only = list_goals(db_conn, status="active")
    assert len(active_only) == 1
    assert active_only[0]["name"] == "진행중"


def test_get_active_goal_returns_latest(db_conn):
    add_goal(db_conn, name="이전 목표", distance_km=10.0)
    add_goal(db_conn, name="최신 목표", distance_km=42.195)
    g = get_active_goal(db_conn)
    assert g["name"] == "최신 목표"


def test_get_active_goal_none_when_empty(db_conn):
    assert get_active_goal(db_conn) is None


def test_update_goal(db_conn):
    gid = add_goal(db_conn, name="원래이름", distance_km=10.0)
    result = update_goal(db_conn, gid, name="바뀐이름", distance_km=21.1)
    assert result is True
    g = get_goal(db_conn, gid)
    assert g["name"] == "바뀐이름"
    assert g["distance_km"] == 21.1


def test_update_goal_invalid_field(db_conn):
    gid = add_goal(db_conn, name="목표", distance_km=10.0)
    result = update_goal(db_conn, gid, nonexistent_field="value")
    assert result is False


def test_complete_goal(db_conn):
    gid = add_goal(db_conn, name="마라톤", distance_km=42.195)
    assert complete_goal(db_conn, gid) is True
    g = get_goal(db_conn, gid)
    assert g["status"] == "completed"


def test_cancel_goal(db_conn):
    gid = add_goal(db_conn, name="취소될 목표", distance_km=10.0)
    assert cancel_goal(db_conn, gid) is True
    g = get_goal(db_conn, gid)
    assert g["status"] == "cancelled"


def test_complete_nonexistent_goal(db_conn):
    assert complete_goal(db_conn, 9999) is False


def test_cancel_nonexistent_goal(db_conn):
    assert cancel_goal(db_conn, 9999) is False


def test_list_goals_empty(db_conn):
    assert list_goals(db_conn) == []


def test_add_goal_minimal(db_conn):
    """race_date/target_time 없이 최소 정보로 추가 가능."""
    gid = add_goal(db_conn, name="자유 달리기", distance_km=5.0)
    g = get_goal(db_conn, gid)
    assert g["race_date"] is None
    assert g["target_time_sec"] is None

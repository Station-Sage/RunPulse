"""milestone_events·milestone_hooks — 출처별 마일스톤 기록·병합·삭제 (ADR-057)."""
import sqlite3

import pytest

from src.services import context_episodes as E
from src.services import milestone_events as ev
from src.services import milestone_hooks as H
from src.services import race_calendar_service as svc
from src.services import race_calendar_state as st
from src.services import race_result_service as rr
from src.services.context_episode_delete import delete_episode
from src.training import goals
from tests.helpers_pred import seed_run


def _rows(conn, type_=None):
    sql = "SELECT type, date, title, detail, source_ref FROM milestones"
    args = ()
    if type_:
        sql, args = sql + " WHERE type=?", (type_,)
    return conn.execute(sql + " ORDER BY id", args).fetchall()


@pytest.fixture
def today(monkeypatch):
    monkeypatch.setattr(ev, "today_local", lambda conn: "2026-11-19")
    monkeypatch.setattr(H, "today_local", lambda conn: "2026-11-19")
    return "2026-11-19"


# ── 원시 함수 ──────────────────────────────────────────────────

def test_record_event_upsert_by_source_ref(db_conn):
    assert ev.record_event(db_conn, "race_finish", "2026-01-01", "10K 완주", source_ref="race_result:1")
    assert ev.record_event(db_conn, "race_finish", "2026-01-01", "10K 도전 (DNF)", source_ref="race_result:1")
    assert [r[2] for r in _rows(db_conn)] == ["10K 도전 (DNF)"]


def test_record_event_unique_ignored_and_per_day(db_conn):
    assert ev.record_event(db_conn, "goal_changed", "2026-01-01", "목표 수정: A", source_ref="goal:1", per_day=True)
    assert ev.record_event(db_conn, "goal_changed", "2026-01-02", "목표 수정: A", source_ref="goal:1", per_day=True)
    assert len(_rows(db_conn, "goal_changed")) == 2          # 다른 날 이력은 보존
    assert not ev.record_event(db_conn, "goal_changed", "2026-01-02", "목표 수정: A")   # UNIQUE 충돌 무시


def test_record_and_remove_swallow_errors():
    c = sqlite3.connect(":memory:")   # milestones 테이블 없음
    assert ev.record_event(c, "goal_set", "2026-01-01", "x") is False
    assert ev.remove_event(c, "goal:1") == 0
    assert ev.prune_orphans(c) == 0


def test_local_date_of_offset(db_conn):
    assert ev.local_date_of(db_conn, "2026-11-18 20:00:00", 9 * 3600) == "2026-11-19"
    assert ev.local_date_of(db_conn, None) is None


def test_dist_label_and_fmt():
    assert (H.dist_label(21.0975), H.dist_label(15.25), H.dist_label(None)) == ("하프마라톤", "15.2km", "거리 미상")
    assert H.fmt_time(3725) == "1:02:05" and H.fmt_time(None) is None


# ── 대회 결과 ──────────────────────────────────────────────────

def test_race_result_finish_dnf_and_remove(db_conn):
    aid = seed_run(db_conn, sid="1", date="2026-10-05", name="춘천 마라톤", dist=42195, moving=12600)
    rr.confirm(db_conn, aid, "allout", official_time_sec=12500)
    assert _rows(db_conn, "race_finish") == [
        ("race_finish", "2026-10-05", "풀마라톤 완주", "춘천 마라톤 · 3:28:20", f"race_result:{aid}")]
    rr.confirm(db_conn, aid, "dnf")
    assert _rows(db_conn, "race_finish")[0][2:4] == ("풀마라톤 도전 (DNF)", "춘천 마라톤")
    rr.remove(db_conn, aid)
    assert _rows(db_conn, "race_finish") == []


# ── 목표 ──────────────────────────────────────────────────────

def test_goal_set_change_merge_and_cancel(db_conn, today, monkeypatch):
    gid = goals.add_goal(db_conn, "봄 하프", 21.0975, target_time_sec=6300)
    assert _rows(db_conn, "goal_set")[0][1:4] == (today, "목표 설정: 봄 하프", "하프마라톤 · 목표 1:45:00")
    goals.update_goal(db_conn, gid, target_time_sec=6000)      # 같은 날 → goal_set 갱신, goal_changed 없음
    assert _rows(db_conn, "goal_changed") == [] and "1:40:00" in _rows(db_conn, "goal_set")[0][3]
    monkeypatch.setattr(H, "today_local", lambda conn: "2026-11-20")
    goals.update_goal(db_conn, gid, target_time_sec=5900)
    goals.update_goal(db_conn, gid, name="봄 하프 PB")
    ch = _rows(db_conn, "goal_changed")
    assert len(ch) == 1 and ch[0][2] == "목표 수정: 봄 하프 PB"
    assert ch[0][3] == "변경: 이름 봄 하프 PB · 목표 기록 1:38:20"
    goals.cancel_goal(db_conn, gid)
    assert _rows(db_conn) == []


def test_goal_supersede_keeps_previous(db_conn, today):
    goals.add_goal(db_conn, "A", 10)
    goals.add_goal(db_conn, "B", 21.0975)
    assert [r[2] for r in _rows(db_conn, "goal_set")] == ["목표 설정: A", "목표 설정: B"]


def test_goal_with_race_registers_both(db_conn, today):
    goals.add_goal(db_conn, "가을 풀", 42.195, race_date="2027-03-01")
    types = sorted(r[0] for r in _rows(db_conn))
    assert types == ["goal_set", "race_registered"]
    assert _rows(db_conn, "race_registered")[0][1] == today     # 등록일(대회일 아님)


# ── 대회 등록 ──────────────────────────────────────────────────

def test_race_registered_update_cancel_restore(db_conn, today, monkeypatch):
    r = svc.add(db_conn, {"name": "서울 10K", "race_date": "2027-04-01", "distance_km": 10, "priority": "B"})
    assert _rows(db_conn, "race_registered")[0][1:4] == (today, "대회 등록: 서울 10K", "10K · 대회일 2027-04-01")
    monkeypatch.setattr(H, "today_local", lambda conn: "2026-12-01")
    svc.update(db_conn, r["id"], {"race_date": "2027-04-08"})
    row = _rows(db_conn, "race_registered")[0]
    assert row[1] == today and "2027-04-08" in row[3]           # 날짜는 등록일 유지, 내용만 갱신
    svc.cancel(db_conn, r["id"])
    assert _rows(db_conn) == []
    st.restore(db_conn, r["id"], "2026-11-19")
    assert len(_rows(db_conn, "race_registered")) == 1


def test_linked_race_update_records_goal_changed(db_conn, monkeypatch, today):
    gid = goals.add_goal(db_conn, "풀", 42.195, race_date="2027-03-01")
    race_id = goals.get_goal(db_conn, gid)["race_id"]
    monkeypatch.setattr(H, "today_local", lambda conn: "2026-11-25")
    svc.update(db_conn, race_id, {"race_date": "2027-03-08"})
    assert _rows(db_conn, "goal_changed")[0][3] == "변경: 대회일 2027-03-08"
    svc.cancel(db_conn, race_id, cancel_goal=True)
    assert _rows(db_conn) == []


# ── 재계획 ────────────────────────────────────────────────────

def test_replan_record_and_undo(db_conn, today):
    rid = db_conn.execute("INSERT INTO plan_replans(goal_id, anchor_monday, start_km, start_source)"
                          " VALUES (1, '2026-11-23', 42.4, 'history')").lastrowid
    assert H.on_replan(db_conn, rid)
    assert _rows(db_conn, "plan_replan")[0][1:4] == (today, "훈련 계획 재조정", "2026-11-23 주부터 · 시작 주간 42km")
    H.on_replan_undone(db_conn, rid)
    assert _rows(db_conn) == []


# ── 질병·부상 ──────────────────────────────────────────────────

def test_illness_start_recovery_delete(db_conn):
    eid = E.open_episode(db_conn, "illness", start_date="2026-11-01", severity=2, detail={"site": "목"})
    assert _rows(db_conn) == [("illness_start", "2026-11-01", "질병 시작", None, f"episode:{eid}")]
    E.close(db_conn, eid, "2026-11-05")
    assert _rows(db_conn, "recovery")[0][1:4] == ("2026-11-05", "질병에서 회복", "4일 만")
    delete_episode(db_conn, eid)
    assert _rows(db_conn) == []


def test_travel_has_no_milestone_and_dismiss_removes(db_conn):
    E.open_episode(db_conn, "travel", start_date="2026-11-01")
    assert _rows(db_conn) == []
    eid = E.open_episode(db_conn, "illness", start_date="2026-11-02", origin="auto", status="candidate")
    assert _rows(db_conn) == []                                  # 후보는 기록하지 않음
    E.confirm(db_conn, eid)
    assert len(_rows(db_conn, "illness_start")) == 1
    db_conn.execute("UPDATE context_episodes SET status='candidate' WHERE id=?", (eid,))
    E.dismiss(db_conn, eid)
    assert _rows(db_conn) == []


def test_prune_orphans(db_conn):
    ev.record_event(db_conn, "race_finish", "2026-01-01", "x", source_ref="race_result:999")
    ev.record_event(db_conn, "goal_set", "2026-01-01", "y", source_ref="goal:999")
    ev.record_event(db_conn, "distance_threshold", "2026-01-01", "누적 100km 돌파")
    assert ev.prune_orphans(db_conn) == 2
    assert [r[0] for r in _rows(db_conn)] == ["distance_threshold"]

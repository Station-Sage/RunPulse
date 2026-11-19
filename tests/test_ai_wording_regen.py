"""AI 다듬기 재생성 기준(ADR-059 D15~D17) — 반올림 해시, 스냅샷형 활동 문구, 교차 의존, 생성 범위."""
from __future__ import annotations

import sqlite3

import pytest

from src.db_setup import create_tables, migrate_db
from src.services import activity_impact_wording as aiw
from src.services import ai_wording as aw
from src.services import ai_wording_live as live
from src.services import metric_interpretation as mi
from src.services import story_service as ss
from src.services import story_wording as sw
from src.services.activity_impact_service import get_activity_impact
from src.services.ai_wording_basis import default_basis, quantize
from src.services.metrics_explain import get_metric_explain

from src.services import today_reason_wording as trw

S = trw.SURFACE


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    migrate_db(c)
    for i in range(8):   # 9월 1~8일 10km 러닝 8건(페이스 6:00~6:14)
        c.execute("INSERT INTO activity_summaries (source, source_id, activity_type, start_time, distance_m,"
                  " duration_sec, avg_pace_sec_km, avg_hr) VALUES ('garmin', ?, 'running', ?, 10000, 3600, ?, 145)",
                  (f"a{i}", f"2026-09-0{i + 1}T07:00:00", 360 + 2 * i))
    yield c
    c.close()


def _ids(c):
    return [r[0] for r in c.execute("SELECT id FROM activity_summaries ORDER BY start_time")]


def _h(c, aid):
    imp = get_activity_impact(c, aid)
    return aw.src_hash(aiw.SURFACE, aiw.item(c, aid, imp, aiw.impact_lines(imp)))


# ── 반올림 ──────────────────────────────────────────────────────────────────

def test_quantize_steps():
    q = quantize({"distance_km": 10.04, "avg_pace": "5:32/km", "pace_sec": 332.0, "acwr": 1.32,
                  "easy_pct": 62.0, "ctl": 42.3, "tsb": -3.24, "n": 7, "pred": "1:45:32"})
    assert q == {"distance_km": 10.0, "avg_pace": "5:30/km", "pace_sec": 330.0, "acwr": 1.3,
                 "easy_pct": 60.0, "ctl": 42, "tsb": -3.2, "n": 7, "pred": "1:45:30"}


def test_small_change_same_hash_big_change_regenerates():
    rule = "ACWR 1.31 로 부하가 빨라요."
    h = lambda f, r=rule: aw.src_hash(S, aw.Item("d", r, f))
    base = h({"acwr": 1.31, "ctl": 42.3})
    assert h({"acwr": 1.32, "ctl": 42.4}, "ACWR 1.32 로 부하가 빨라요.") == base
    assert h({"acwr": 1.45, "ctl": 42.3}) != base
    # facts 로 설명되지 않는 규칙 숫자는 그대로 추적
    assert aw.src_hash(S, aw.Item("d", "7일 연속 달렸어요.", {})) != aw.src_hash(S, aw.Item("d", "8일 연속 달렸어요.", {}))


def test_default_basis_masks_only_covered_numbers():
    b = default_basis("CTL 42.3, 연속 5일", {"ctl": 42.3})
    assert b["rule"] == "CTL #, 연속 5일"


# ── 스냅샷형: 이 러닝의 의미 ─────────────────────────────────────────────────

def test_snapshot_ignores_later_ctl_tsb_and_new_activities(conn):
    aid = _ids(conn)[-1]
    h0 = _h(conn, aid)
    conn.execute("INSERT INTO metric_store(scope_type, scope_id, metric_name, provider, numeric_value, is_primary)"
                 " VALUES ('daily','2026-09-08','ctl','runpulse:formula_v1',50,1)")
    conn.execute("INSERT INTO activity_summaries (source, source_id, activity_type, start_time, distance_m, duration_sec,"
                 " avg_pace_sec_km) VALUES ('garmin','later','running','2026-09-20T07:00:00',10000,3600,350)")
    assert _h(conn, aid) == h0


@pytest.mark.parametrize("sql", [
    "UPDATE activity_summaries SET distance_m=10300 WHERE id={a}",
    "UPDATE activity_summaries SET avg_pace_sec_km=avg_pace_sec_km+10 WHERE id={a}",
    "UPDATE activity_summaries SET avg_hr=152 WHERE id={a}",
    "INSERT INTO activity_laps(activity_id, source, lap_index, distance_m, avg_pace_sec_km) VALUES ({a},'garmin',0,1000,350)",
    "INSERT INTO planned_workouts(date, workout_type, distance_km, source, matched_activity_id) VALUES ('2026-09-08','easy',10,'manual',{a})",
    "INSERT INTO activity_feedback(activity_id, rpe, note) VALUES ({a}, 6, '메모')",
    "INSERT INTO milestones(type, date, title, activity_id) VALUES ('longest_run','2026-09-08','최장거리',{a})",
])
def test_snapshot_regenerates_on_own_data(conn, sql):
    aid = _ids(conn)[-1]
    h0 = _h(conn, aid)
    conn.execute(sql.format(a=aid))
    assert _h(conn, aid) != h0


def test_snapshot_tiny_own_change_is_ignored(conn):
    aid = _ids(conn)[-1]
    h0 = _h(conn, aid)
    conn.execute("UPDATE activity_summaries SET distance_m=10030, avg_pace_sec_km=avg_pace_sec_km+1 WHERE id=?", (aid,))
    assert _h(conn, aid) == h0


def test_relative_compare_only_direct_previous_target(conn):
    ids = _ids(conn)
    last, prev, older = ids[-1], ids[-2], ids[-4]
    assert get_activity_impact(conn, last)["similar"]["latest_id"] == prev
    h0 = _h(conn, last)
    conn.execute("UPDATE activity_summaries SET avg_pace_sec_km=400 WHERE id=?", (older,))
    assert _h(conn, last) == h0                     # 더 오래된 비교 대상 편집은 무시
    conn.execute("UPDATE activity_summaries SET avg_pace_sec_km=400 WHERE id=?", (prev,))
    assert _h(conn, last) != h0                     # 직전 비교 대상 편집 → 재생성


# ── 교차 의존: 기간 이야기·그날 지표 해석 ────────────────────────────────────

def _story_hash(c, pid):
    st = ss.build_story(c, pid)
    return aw.src_hash(sw.SURFACE, sw.item(st, st["paragraph_rule"], c))


def test_edit_and_rematch_invalidate_month_and_week_story(conn):
    aid = _ids(conn)[2]                              # 2026-09-03(W36)
    m0, w0, other = _story_hash(conn, "2026-09"), _story_hash(conn, "2026-W36"), _story_hash(conn, "2026-W37")
    conn.execute("INSERT INTO planned_workouts(date, workout_type, distance_km, source, matched_activity_id)"
                 " VALUES ('2026-09-03','tempo',10,'manual',?)", (aid,))
    assert _story_hash(conn, "2026-09") != m0 and _story_hash(conn, "2026-W36") != w0
    assert _story_hash(conn, "2026-W37") == other


def test_milestone_create_delete_invalidates_month_story_and_activity(conn):
    aid = _ids(conn)[4]
    m0, a0 = _story_hash(conn, "2026-09"), _h(conn, aid)
    conn.execute("INSERT INTO milestones(type, date, title, activity_id) VALUES ('pb','2026-09-05','10km 최고 기록',?)", (aid,))
    m1 = _story_hash(conn, "2026-09")
    assert m1 != m0 and _h(conn, aid) != a0
    conn.execute("DELETE FROM milestones")
    assert _story_hash(conn, "2026-09") == m0 and _h(conn, aid) == a0


def test_rematch_invalidates_that_day_metric_interp_only(conn):
    for d in ("2026-09-03", "2026-09-04"):
        for n, v in (("tsb", -12.0), ("ctl", 40.0), ("atl", 52.0)):
            conn.execute("INSERT INTO metric_store(scope_type, scope_id, metric_name, provider, numeric_value, is_primary)"
                         " VALUES ('daily',?,?,'runpulse:formula_v1',?,1)", (d, n, v))
    h = lambda d: aw.src_hash(mi.SURFACE, mi.build_item(conn, get_metric_explain(conn, "daily", d, "tsb")))
    d3, d4 = h("2026-09-03"), h("2026-09-04")
    conn.execute("INSERT INTO planned_workouts(date, workout_type, distance_km, source, matched_activity_id)"
                 " VALUES ('2026-09-03','easy',10,'manual',?)", (_ids(conn)[2],))
    assert h("2026-09-03") != d3 and h("2026-09-04") == d4


# ── 생성 범위(D17) ─────────────────────────────────────────────────────────

def test_sync_warm_covers_last_14_days_only(conn):
    keys = {i.scope_key for i in aiw.collect(conn, "2026-09-20")}
    ids = _ids(conn)
    assert keys == {str(i) for i in ids[-2:]}        # 9/7·9/8 만 14일 안(9/20 기준)
    assert aiw.collect(conn, "2026-12-01") == []


def test_old_activity_generates_once_on_open(conn, monkeypatch):
    calls: list = []
    monkeypatch.setattr(aw, "warm_in_background", lambda *a, **k: calls.append(a))
    monkeypatch.setattr(live, "_db_path", lambda c: "/tmp/regen.db")
    live.reset_cooldown()
    aid = _ids(conn)[-1]
    imp = get_activity_impact(conn, aid)
    assert aiw.attach(conn, aid, imp, {}, schedule=True)["wording"]["source"] == "rule"
    aiw.attach(conn, aid, get_activity_impact(conn, aid), {}, schedule=True)
    assert len(calls) == 1                           # 쿨다운 안 재예약 없음, 요청 스레드는 대기하지 않음

"""milestone_running — 최장거리·연속 훈련 주 탐지(날짜 = 사건일, 멱등, 러닝만)."""
from datetime import date, timedelta

from src.services import milestone_running as M
from tests.helpers_pred import seed_run

_SID = iter(range(1, 10_000))


def _run(conn, day, km, atype="running", moving=None):
    return seed_run(conn, sid=str(next(_SID)), date=day, dist=km * 1000, moving=moving or int(km * 330), atype=atype)


def _titles(conn, t):
    return conn.execute("SELECT date, title FROM milestones WHERE type=? ORDER BY date", (t,)).fetchall()


def test_longest_run_needs_history_min_km_and_margin(db_conn):
    d0 = date(2026, 1, 1)
    _run(db_conn, d0.isoformat(), 20)                         # 초기 이력 — 기록 안 함
    for i in range(1, 10):
        _run(db_conn, (d0 + timedelta(days=i)).isoformat(), 8)
    _run(db_conn, "2026-02-01", 20.3)                         # 마진 0.5km 미만
    _run(db_conn, "2026-02-08", 24.0)
    _run(db_conn, "2026-02-15", 30.0, atype="cycling")       # 러닝 아님
    _run(db_conn, "2026-02-20", 26.0)
    out = M.detect_longest_runs(db_conn)
    assert [m["title"] for m in out] == ["최장거리 24.0km", "최장거리 26.0km"]
    assert _titles(db_conn, "longest_run")[0] == ("2026-02-08", "최장거리 24.0km")
    assert M.detect_longest_runs(db_conn) == []               # 멱등


def test_longest_run_skips_vehicle_pace(db_conn):
    for i in range(10):
        _run(db_conn, f"2026-01-{i + 1:02d}", 10)
    _run(db_conn, "2026-02-01", 60, moving=60 * 100)          # 1:40/km — 오기록
    assert M.detect_longest_runs(db_conn) == []


def test_week_start_sunday():
    assert M.week_start(date(2026, 11, 19)) == date(2026, 11, 15)   # 목 → 일
    assert M.week_start(date(2026, 11, 15)) == date(2026, 11, 15)


def test_streak_tiers():
    assert [n for n in range(1, 110) if M.streak_tiers(n)] == [4, 8, 12, 26, 52, 104]


def test_streak_weeks_dates_and_reset(db_conn):
    sun = date(2026, 1, 4)                                    # 일요일
    for w in range(5):                                        # 5주 연속 주 2회
        for d in (1, 3):
            _run(db_conn, (sun + timedelta(weeks=w, days=d)).isoformat(), 6)
    _run(db_conn, (sun + timedelta(weeks=5, days=1)).isoformat(), 6)   # 6주차 1회 → 끊김
    out = M.detect_streaks(db_conn, "2026-12-31")
    assert [(m["date"], m["title"]) for m in out] == [("2026-01-31", "4주 연속 훈련")]   # 4주차 토요일
    assert M.detect_streaks(db_conn, "2026-12-31") == []


def test_streak_not_before_week_end(db_conn):
    sun = date(2026, 1, 4)
    for w in range(4):
        for d in (0, 1):
            _run(db_conn, (sun + timedelta(weeks=w, days=d)).isoformat(), 6)
    assert M.detect_streaks(db_conn, "2026-01-27") == []      # 4주차 토요일(1/31) 전 — 보류
    assert len(M.detect_streaks(db_conn, "2026-01-31")) == 1


def test_no_runs(db_conn):
    assert M.detect_streaks(db_conn, "2026-01-01") == [] and M.detect_longest_runs(db_conn) == []


def test_sync_detection_includes_running_and_prunes(db_conn):
    from src.services.milestone_events import record_event
    from src.services.milestone_service import detect_and_store_milestones
    for i in range(10):
        _run(db_conn, f"2026-01-{i + 1:02d}", 10)
    _run(db_conn, "2026-01-20", 21.1)
    record_event(db_conn, "goal_set", "2026-01-01", "목표 설정: 없음", source_ref="goal:404")
    out = detect_and_store_milestones(db_conn, "2026-01-01", "2026-01-31")
    assert "longest_run" in {m["type"] for m in out}
    assert db_conn.execute("SELECT count(*) FROM milestones WHERE source_ref='goal:404'").fetchone()[0] == 0

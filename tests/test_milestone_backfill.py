"""milestone_backfill — 기존 출처에서 마일스톤 재구성(날짜 규칙·멱등·dry-run 롤백) + 스크립트."""
import sqlite3

from src.db_setup import create_tables, migrate_db
from src.services import milestone_backfill as B
from tests.helpers_pred import seed_run


def _seed(conn):
    aid = seed_run(conn, sid="r1", date="2026-04-05", name="서울 하프", dist=21100, moving=6300)
    conn.execute("INSERT INTO race_results(activity_id, distance_m, effort, confirmed_at) VALUES (?, 21100, 'allout', datetime('now'))", (aid,))
    conn.execute("INSERT INTO goals(name, distance_km, status, created_at) VALUES ('옛 목표', 10, 'cancelled', '2026-01-01 03:00:00')")
    conn.execute("INSERT INTO goals(name, distance_km, status, created_at) VALUES ('새 목표', 21.0975, 'active', '2026-02-01 03:00:00')")
    conn.execute("INSERT INTO race_calendar(name, race_date, distance_km, priority, created_at)"
                 " VALUES ('서울 하프', '2026-04-05', 21.0975, 'B', '2026-01-10 03:00:00')")
    conn.execute("INSERT INTO race_calendar(name, race_date, distance_km, priority, status, created_at)"
                 " VALUES ('취소 대회', '2026-05-05', 10, 'C', 'cancelled', '2026-01-11 03:00:00')")
    conn.execute("INSERT INTO context_episodes(kind, start_date, end_date, origin, status)"
                 " VALUES ('injury', '2026-03-01', '2026-03-15', 'user', 'confirmed')")
    conn.execute("INSERT INTO context_episodes(kind, start_date, origin, status) VALUES ('travel', '2026-03-01', 'user', 'confirmed')")
    conn.execute("INSERT INTO plan_replans(goal_id, anchor_monday, start_km, start_source, created_at)"
                 " VALUES (2, '2026-03-02', 30, 'history', '2026-02-27 01:00:00')")
    conn.commit()


def test_backfill_dates_and_idempotent(db_conn):
    _seed(db_conn)
    out = B.backfill(db_conn)
    assert out == {"goal_set": 1, "injury_start": 1, "plan_replan": 1, "race_finish": 1,
                   "race_registered": 1, "recovery": 1}
    rows = dict(db_conn.execute("SELECT type || ':' || title, date FROM milestones").fetchall())
    assert rows["race_finish:하프마라톤 완주"] == "2026-04-05"           # 대회일
    assert rows["race_registered:대회 등록: 서울 하프"][:7] == "2026-01"   # 등록일(대회일 아님)
    assert "goal_set:목표 설정: 옛 목표" not in rows                      # 취소된 목표는 만들지 않음
    assert rows["recovery:부상에서 회복"] == "2026-03-15"
    assert B.backfill(db_conn) == {}                                       # 재실행 — 변화 없음


def test_run_backfill_dry_run_rolls_back(tmp_path):
    p = tmp_path / "running.db"
    c = sqlite3.connect(str(p))
    create_tables(c)
    migrate_db(c)
    _seed(c)
    assert B.run_backfill(c, apply=False)["goal_set"] == 1
    assert c.execute("SELECT count(*) FROM milestones").fetchone()[0] == 0
    assert B.run_backfill(c, apply=True)["goal_set"] == 1
    assert c.execute("SELECT count(*) FROM milestones").fetchone()[0] == 6
    c.close()


def test_script_main_dry_run_and_apply(tmp_path, capsys):
    import importlib.util
    spec = importlib.util.spec_from_file_location("bf", "scripts/backfill_milestones.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    p = tmp_path / "running.db"
    c = sqlite3.connect(str(p))
    create_tables(c)
    migrate_db(c)
    _seed(c)
    c.close()
    assert mod.main(["--db", str(p)]) == 0
    assert "dry-run" in capsys.readouterr().out
    assert mod.main(["--db", str(p), "--apply"]) == 0
    assert list(tmp_path.glob("running.db.bak-milestones-*"))
    with sqlite3.connect(str(p)) as c2:
        assert c2.execute("SELECT count(*) FROM milestones").fetchone()[0] == 6


def test_replaced_goal_milestone_removed(db_conn):
    from src.services import goal_service as gs
    db_conn.execute("INSERT INTO goals(name, distance_km, status) VALUES ('옛', 10, 'active')")
    gid = db_conn.execute("SELECT id FROM goals").fetchone()[0]
    from src.services import milestone_hooks as H
    H.on_goal_set(db_conn, gid, "2026-01-01")
    assert db_conn.execute("SELECT count(*) FROM milestones WHERE type='goal_set'").fetchone()[0] == 1
    gs.create_goal_with_race(db_conn, name="새", distance_km=21.0975, race_date="2027-03-01")
    titles = [r[0] for r in db_conn.execute("SELECT title FROM milestones WHERE type='goal_set'")]
    assert "목표 설정: 옛" not in titles

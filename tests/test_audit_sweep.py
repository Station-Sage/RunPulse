"""감사 스윕 러너의 순수 로직(경로 치환·원장 기록) 테스트."""
import sqlite3

from scripts.audit import inventory, sweep


def test_resolve_path_uses_db_sample_and_defaults():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE activity_summaries (id INTEGER, start_time TEXT)")
    conn.execute("INSERT INTO activity_summaries VALUES (42, '2026-01-01')")
    assert sweep.resolve_path("/library/[id]/laps", conn) == "/library/42/laps"
    assert sweep.resolve_path("/library/providers/[group]", conn) == "/library/providers/garmin-strava"
    assert sweep.resolve_path("/today", None) == "/today"
    assert sweep.resolve_path("/library/shoes/[id]", conn) == "/library/shoes/1"   # 테이블 없음 → 기본값


def test_apply_results_records_ledger(tmp_path):
    p = tmp_path / "ledger.json"
    n = sweep.apply_results([{"cell": "/a|small|390", "issues": []},
                             {"cell": "/b|small|390", "issues": ["overflow-x: 5px", "no-h1"]}], p)
    assert n == {"confirmed": 1, "issues": 1}
    led = inventory.load_ledger(p)
    assert led["/a|small|390"]["status"] == "확인"
    assert led["/b|small|390"]["status"] == "이슈" and "overflow-x" in led["/b|small|390"]["note"]


def test_stop_kills_stubborn_process():
    import subprocess
    import sys
    from scripts.audit.sweep import stop

    p = subprocess.Popen([sys.executable, "-c", "import signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);time.sleep(60)"])
    import time
    time.sleep(0.5)
    stop(p)
    assert p.poll() is not None

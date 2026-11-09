"""scripts/ops_report.py(T9) — 빈 DB·샘플 DB 리포트, 읽기 전용."""
import importlib.util
from datetime import datetime, timedelta
from pathlib import Path

from src.ai.llm_budget import LIMITS
from src.ops.store import OpsStore

_spec = importlib.util.spec_from_file_location(
    "ops_report", Path(__file__).resolve().parent.parent / "scripts" / "ops_report.py")
R = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(R)
NOW = datetime(2026, 11, 6, 12, 0, 0)


def test_empty_report_when_no_db(tmp_path):
    assert R.open_readonly(tmp_path / "none.db") is None
    rep = R.build_report(None, NOW, "2026-11-06", LIMITS)
    assert rep["users"] == [] and rep["llm_global"]["calls"] == 0
    assert not (tmp_path / "none.db").exists()


def test_sample_report(tmp_path):
    s = OpsStore(tmp_path / "ops.db")
    for i, res in enumerate(["ok", "ok", "fail", "skipped_busy"]):
        s.add_run("a@x.com", started_at=NOW - timedelta(hours=i + 1), finished_at=NOW - timedelta(hours=i),
                  result=res)
    s.put_state("a@x.com", next_due_at=NOW - timedelta(hours=2))
    s.put_state("d@x.com", next_due_at=NOW, state="dormant")
    s.add_usage("2026-11-06", "a@x.com", "coach", calls=400, tokens_in=10)
    conn = R.open_readonly(tmp_path / "ops.db")
    rep = R.build_report(conn, NOW, "2026-11-06", LIMITS, mask=lambda u: u)
    conn.close()
    assert rep["users"] == [{"uid": "a@x.com", "runs": 3, "success_rate": 0.67, "p95_s": 3600.0}]
    assert rep["dormant"] == 1 and rep["max_overdue_h"] == 2.0
    assert rep["llm_top"][0]["calls"] == 400 and rep["llm_global"]["ratio"] == 0.1


def test_main_json(tmp_path, capsys):
    assert R.main(["--db", str(tmp_path / "x.db"), "--json"]) == 0
    assert '"users": []' in capsys.readouterr().out
    assert R._p95([]) is None and R._p95([1.0, 2.0, 3.0]) == 3.0

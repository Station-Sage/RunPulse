"""scripts/synth_smoke 합성 DB 시드 테스트 — 시드가 기능 기대치(서비스 입력)와 어긋나면 UI 스모크가 헛돈다."""
from __future__ import annotations

import sqlite3

from scripts.synth_smoke.seed_synth import seed
from src.services import adaptation_service, provider_status_service


def _count(conn, table: str) -> int:
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def test_seed_creates_expected_rows(tmp_path):
    out = tmp_path / "running.db"
    assert seed(out) == {"activities": 14}
    conn = sqlite3.connect(out)
    assert _count(conn, "activity_summaries") == 14
    assert _count(conn, "daily_wellness") == 30
    assert _count(conn, "milestones") == 3
    assert conn.execute("SELECT COUNT(*) FROM activity_laps WHERE activity_id=100").fetchone()[0] == 8
    assert conn.execute("SELECT COUNT(*) FROM activity_streams WHERE activity_id=100").fetchone()[0] == 300
    conn.close()


def test_seed_feeds_provider_status_and_adaptation(tmp_path):
    """Provider 현황·적응 상태 화면이 합성 DB에서 실제 값을 보이도록 시드가 채워져 있어야 한다."""
    out = tmp_path / "running.db"
    seed(out)
    conn = sqlite3.connect(out)
    garmin = next(r for r in provider_status_service.get_provider_status(conn) if r["provider"] == "garmin")
    assert garmin["has_data"] is True and garmin["activity_count"] == 14 and garmin["last_new_data_at"]
    adaptation = adaptation_service.get_adaptation_status(conn)
    assert adaptation["acwr"] is not None
    assert adaptation["hrv"]["delta_pct"] is not None
    conn.close()


def test_seed_empty_has_schema_but_no_rows(tmp_path):
    out = tmp_path / "empty.db"
    assert seed(out, empty=True) == {"activities": 0}
    conn = sqlite3.connect(out)
    assert _count(conn, "activity_summaries") == 0
    assert _count(conn, "metric_store") == 0
    conn.close()


def test_seed_overwrites_existing_file_and_writes_only_there(tmp_path):
    out = tmp_path / "sub" / "running.db"
    seed(out)
    seed(out)  # 두 번째 호출은 파일을 지우고 다시 만든다(중복 행 없음)
    conn = sqlite3.connect(out)
    assert _count(conn, "activity_summaries") == 14
    conn.close()
    assert sorted(p.name for p in tmp_path.iterdir()) == ["sub"]

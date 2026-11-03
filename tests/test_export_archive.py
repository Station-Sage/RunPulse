"""export_archive — 그룹 선택, 기간 필터, 해제 에피소드, 미마이그레이션 skip, 비밀 차단, 디스크, 부분 파일 정리."""
from __future__ import annotations

import json
import sqlite3
import zipfile

import pytest

from src.db_setup import create_tables, migrate_db
from src.services import export_archive as ea


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    migrate_db(c)
    c.execute("INSERT INTO source_payloads (source, entity_type, entity_id, entity_date, fetched_at, payload) "
              "VALUES ('garmin','activity','1','2026-10-01','t','{\"a\":1}')")
    yield c
    c.close()


def _manifest(path):
    with zipfile.ZipFile(path) as z:
        return json.loads(z.read("manifest.json")), z.namelist()


def test_manifest_and_readme(conn, tmp_path):
    info = ea.build_archive(conn, tmp_path / "a.zip", ("raw",), "2026-10-01", "2026-10-31")
    m, names = _manifest(tmp_path / "a.zip")
    assert m["format_version"] == ea.FORMAT_VERSION and m["range"] == {"from": "2026-10-01", "to": "2026-10-31"}
    assert m["include_dismissed"] is False and m["sensitive_groups"] == []
    assert "README.txt" in names and "raw_payloads/garmin.jsonl" in names
    assert info["row_counts"]["source_payloads"] == 1


def test_sensitive_groups_listed(conn, tmp_path):
    ea.build_archive(conn, tmp_path / "a.zip", ("profile", "episodes"))
    m, _ = _manifest(tmp_path / "a.zip")
    assert set(m["sensitive_groups"]) == {"profile", "episodes"}


def test_dismissed_episodes_excluded_by_default(conn, tmp_path):
    cols = [r[1] for r in conn.execute("PRAGMA table_info(context_episodes)")]
    assert "status" in cols
    conn.execute("INSERT INTO context_episodes (kind, start_date, origin, status) VALUES ('illness','2026-10-01','user','dismissed')")
    conn.execute("INSERT INTO context_episodes (kind, start_date, origin, status) VALUES ('illness','2026-10-02','user','confirmed')")
    ea.build_archive(conn, tmp_path / "a.zip", ("episodes",))
    ea.build_archive(conn, tmp_path / "b.zip", ("episodes",), include_dismissed=True)
    assert _manifest(tmp_path / "a.zip")[0]["groups"][0]["row_counts"]["context_episodes"] == 1
    assert _manifest(tmp_path / "b.zip")[0]["groups"][0]["row_counts"]["context_episodes"] == 2


def test_optional_table_missing_is_skipped(conn, tmp_path):
    conn.execute("DROP TABLE context_episodes")
    ea.build_archive(conn, tmp_path / "a.zip", ("episodes",))
    entry = _manifest(tmp_path / "a.zip")[0]["groups"][0]
    assert entry["skipped"] == {"context_episodes": "not_migrated"}


def test_required_table_missing_fails_and_cleans_up(conn, tmp_path):
    conn.execute("DROP TABLE metric_store")
    with pytest.raises(ea.ExportError) as e:
        ea.build_archive(conn, tmp_path / "a.zip", ("metrics",))
    assert e.value.code == "EXPORT_FAILED" and not (tmp_path / "a.zip").exists()


def test_secret_value_aborts(conn, tmp_path):
    conn.execute("INSERT INTO source_payloads (source, entity_type, entity_id, entity_date, fetched_at, payload) "
                 "VALUES ('garmin','x','2','2026-10-02','t','enc:abcd')")
    with pytest.raises(ea.ExportError) as e:
        ea.build_archive(conn, tmp_path / "a.zip", ("raw",))
    assert e.value.code == "EXPORT_SECRET_DETECTED" and not (tmp_path / "a.zip").exists()


def test_disk_full(conn, tmp_path):
    with pytest.raises(ea.ExportError) as e:
        ea.build_archive(conn, tmp_path / "a.zip", ("raw",), min_free=1 << 60)
    assert e.value.code == "EXPORT_DISK_FULL" and not (tmp_path / "a.zip").exists()


def test_check_free_space_ok(tmp_path):
    ea.check_free_space(tmp_path, 1)


def test_purge_all_runs_per_user(monkeypatch):
    from src.services import export_purge

    seen = []
    monkeypatch.setattr("src.utils.user_context.list_user_ids", lambda: ["a", "b"])
    monkeypatch.setattr(export_purge.export_service, "purge_expired", lambda uid: seen.append(uid) or 1)
    assert export_purge.purge_all() == 2 and seen == ["a", "b"]

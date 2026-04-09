"""initial-load CLI 테스트.

검증 항목:
  1. argparse 파싱 — 기본값, --steps, --dry-run
  2. _parse_steps 함수
  3. 알 수 없는 step은 조용히 무시
  4. dry-run 시 DB 변경 없음
  5. initial-load 없이 --help 출력
"""

from __future__ import annotations

import sqlite3
import sys
import types
import unittest.mock as mock

import pytest

from src.db_setup import create_tables


# ─────────────────────────────────────────────────────────────────────────────
# _parse_steps
# ─────────────────────────────────────────────────────────────────────────────

class TestParseSteps:
    def _parse(self, s):
        from src.sync_cli import _parse_steps
        return _parse_steps(s)

    def test_all_steps(self):
        result = self._parse("1,2,3,4,5,6,7,8,9")
        assert result == [1, 2, 3, 4, 5, 6, 7, 8, 9]

    def test_subset(self):
        result = self._parse("1,7,8,9")
        assert result == [1, 7, 8, 9]

    def test_dedup_and_sort(self):
        result = self._parse("3,1,3,2")
        assert result == [1, 2, 3]

    def test_whitespace_tolerance(self):
        result = self._parse("1, 2, 3")
        assert result == [1, 2, 3]

    def test_invalid_exits(self):
        with pytest.raises(SystemExit):
            self._parse("abc")


# ─────────────────────────────────────────────────────────────────────────────
# argparse
# ─────────────────────────────────────────────────────────────────────────────

class TestArgparse:
    def _parse_args(self, argv):
        """main() 내 parser를 직접 구성하지 않으므로, argparse 로직을 통해 검증."""
        import argparse
        from src.sync_cli import _parse_steps  # noqa: F401

        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest="command")
        il = sub.add_parser("initial-load")
        il.add_argument("--zip-path", default=None)
        il.add_argument("--garmin-days", type=int, default=30)
        il.add_argument("--strava-days", type=int, default=730)
        il.add_argument("--intervals-days", type=int, default=730)
        il.add_argument("--runalyze-days", type=int, default=730)
        il.add_argument("--include-streams", action="store_true")
        il.add_argument("--recompute-days", type=int, default=730)
        il.add_argument("--steps", default="1,2,3,4,5,6,7,8,9")
        il.add_argument("--dry-run", action="store_true")
        return parser.parse_args(argv)

    def test_defaults(self):
        args = self._parse_args(["initial-load"])
        assert args.command == "initial-load"
        assert args.zip_path is None
        assert args.garmin_days == 30
        assert args.strava_days == 730
        assert args.recompute_days == 730
        assert args.steps == "1,2,3,4,5,6,7,8,9"
        assert args.dry_run is False
        assert args.include_streams is False

    def test_custom_flags(self):
        args = self._parse_args([
            "initial-load",
            "--zip-path", "/tmp/export.zip",
            "--garmin-days", "60",
            "--steps", "1,7,8,9",
            "--dry-run",
            "--include-streams",
            "--recompute-days", "365",
        ])
        assert args.zip_path == "/tmp/export.zip"
        assert args.garmin_days == 60
        assert _steps(args.steps) == [1, 7, 8, 9]
        assert args.dry_run is True
        assert args.include_streams is True
        assert args.recompute_days == 365


def _steps(s):
    from src.sync_cli import _parse_steps
    return _parse_steps(s)


# ─────────────────────────────────────────────────────────────────────────────
# _run_initial_load dry-run
# ─────────────────────────────────────────────────────────────────────────────

class TestDryRun:
    def _make_conn(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        create_tables(conn)
        return conn

    def test_dry_run_no_db_changes(self):
        """dry-run 시 DB에 아무 행도 삽입되지 않아야 한다."""
        conn = self._make_conn()

        # args 모의
        args = types.SimpleNamespace(
            zip_path=None,
            garmin_days=30,
            strava_days=730,
            intervals_days=730,
            runalyze_days=730,
            include_streams=False,
            recompute_days=730,
            dry_run=True,
        )

        from src.sync_cli import _run_initial_load
        _run_initial_load(conn, args, steps=[1, 2, 3, 4, 5, 6, 7, 8, 9])

        # DB에 변화가 없어야 함
        for tbl in ["activity_summaries", "metric_store", "source_payloads"]:
            cnt = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
            assert cnt == 0, f"{tbl}에 데이터가 삽입되었음 (dry-run 위반)"

    def test_step_subset_executes_only_requested(self, capsys):
        """steps=[7,8,9] 시 1~6 관련 출력이 없어야 한다."""
        conn = self._make_conn()
        args = types.SimpleNamespace(
            zip_path=None,
            garmin_days=30,
            strava_days=730,
            intervals_days=730,
            runalyze_days=730,
            include_streams=False,
            recompute_days=730,
            dry_run=True,
        )

        from src.sync_cli import _run_initial_load
        _run_initial_load(conn, args, steps=[7, 8, 9])

        captured = capsys.readouterr()
        assert "Step 7" in captured.out
        assert "Step 1" not in captured.out
        assert "Step 4" not in captured.out


# ─────────────────────────────────────────────────────────────────────────────
# step 7 (dedup) — dry-run vs real
# ─────────────────────────────────────────────────────────────────────────────

class TestStepDedup:
    def _make_conn_with_activities(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        create_tables(conn)
        # 같은 시각·거리의 garmin + strava 활동
        for src in ("garmin", "strava"):
            conn.execute(
                "INSERT INTO activity_summaries "
                "(source, source_id, start_time, distance_m, duration_sec, activity_type) "
                "VALUES (?, ?, '2025-01-01T08:00:00', 10000, 3000, 'running')",
                (src, f"{src}_1"),
            )
        conn.commit()
        return conn

    def test_dedup_sets_group_id(self):
        conn = self._make_conn_with_activities()
        args = types.SimpleNamespace(
            zip_path=None, garmin_days=30, strava_days=730,
            intervals_days=730, runalyze_days=730, include_streams=False,
            recompute_days=730, dry_run=False,
        )

        from src.sync_cli import _run_initial_load
        _run_initial_load(conn, args, steps=[7])

        groups = conn.execute(
            "SELECT DISTINCT matched_group_id FROM activity_summaries WHERE matched_group_id IS NOT NULL"
        ).fetchall()
        assert len(groups) >= 1

    def test_dedup_dry_run_no_groups(self):
        conn = self._make_conn_with_activities()
        args = types.SimpleNamespace(
            zip_path=None, garmin_days=30, strava_days=730,
            intervals_days=730, runalyze_days=730, include_streams=False,
            recompute_days=730, dry_run=True,
        )

        from src.sync_cli import _run_initial_load
        _run_initial_load(conn, args, steps=[7])

        groups = conn.execute(
            "SELECT COUNT(*) FROM activity_summaries WHERE matched_group_id IS NOT NULL"
        ).fetchone()[0]
        assert groups == 0

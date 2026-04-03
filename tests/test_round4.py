"""라운드 4 테스트: 메타데이터, semantic grouping, CLI."""
import sqlite3
import pytest
from src.db_setup import create_tables
from src.metrics.engine import ALL_CALCULATORS
from src.utils.metric_groups import (
    SEMANTIC_GROUPS, get_group_for_metric, get_group_members,
)
from src.metrics.cli import show_metric_status, main as cli_main


class TestCalculatorMetadata:
    def test_all_have_display_name(self):
        for calc in ALL_CALCULATORS:
            assert calc.display_name, f"{calc.name} missing display_name"

    def test_all_have_description(self):
        for calc in ALL_CALCULATORS:
            assert calc.description, f"{calc.name} missing description"

    def test_format_types_valid(self):
        valid = {"number", "time", "pace", "percentage", "json"}
        for calc in ALL_CALCULATORS:
            assert calc.format_type in valid, (
                f"{calc.name} has invalid format_type: {calc.format_type}"
            )

    def test_ranges_are_dict_or_none(self):
        for calc in ALL_CALCULATORS:
            if calc.ranges is not None:
                assert isinstance(calc.ranges, dict), f"{calc.name} ranges not dict"
                for label, bounds in calc.ranges.items():
                    if isinstance(bounds, (list, tuple)):
                        assert len(bounds) == 2, f"{calc.name} range needs [low, high]"
                    else:
                        assert isinstance(bounds, (int, float)), f"{calc.name} range must be number or list"

    def test_groups_have_members(self):
        for name, group in SEMANTIC_GROUPS.items():
            assert len(group["members"]) >= 1, f"Group '{name}' has no members"
            assert "display_name" in group
            assert "primary_strategy" in group

    def test_get_group_for_metric(self):
        assert get_group_for_metric("trimp", "runpulse:formula_v1") == "trimp"
        assert get_group_for_metric("utrs", "runpulse:formula_v1") == "readiness"
        assert get_group_for_metric("nonexistent") is None

    def test_get_group_members(self):
        members = get_group_members("trimp")
        assert len(members) == 2
        assert ("trimp", "runpulse:formula_v1") in members

    def test_get_group_members_nonexistent(self):
        assert get_group_members("nonexistent") == []


class TestCLI:
    def _conn(self):
        conn = sqlite3.connect(":memory:")
        conn.execute("PRAGMA foreign_keys=ON")
        create_tables(conn)
        return conn

    def test_status_empty(self, capsys):
        conn = self._conn()
        show_metric_status(conn)
        captured = capsys.readouterr()
        assert "RunPulse 메트릭이 없습니다" in captured.out

    def test_status_with_data(self, capsys):
        conn = self._conn()
        from src.utils.db_helpers import upsert_metric
        upsert_metric(conn, "activity", "1", "trimp", "runpulse:formula_v1",
                       numeric_value=85.0, category="rp_load", confidence=0.9)
        conn.commit()
        show_metric_status(conn)
        captured = capsys.readouterr()
        assert "trimp" in captured.out
        assert "runpulse" in captured.out

    def test_cli_no_command(self, capsys):
        """인자 없이 실행하면 help 출력."""
        cli_main([])
        captured = capsys.readouterr()
        assert "RunPulse Metrics CLI" in captured.out or "usage" in captured.out.lower()

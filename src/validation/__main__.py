"""python -m src.validation CLI 진입점.

사용법:
    python -m src.validation
    python -m src.validation --json
    python -m src.validation --expected-activities 600
    python -m src.validation --sources garmin strava
"""

from __future__ import annotations

import argparse
import json
import sys

from src.db_setup import get_connection, get_db_path
from src.validation.validator import DataValidator


def main():
    parser = argparse.ArgumentParser(description="RunPulse Data Validation")
    parser.add_argument("--db-path", default=None, help="DB 경로 (기본: get_db_path())")
    parser.add_argument("--json", action="store_true", help="JSON 형식으로 출력")
    parser.add_argument("--expected-activities", type=int, default=None)
    parser.add_argument(
        "--sources", nargs="+",
        default=["garmin", "strava", "intervals", "runalyze"],
        help="기대 소스 목록",
    )
    args = parser.parse_args()

    if args.db_path:
        import sqlite3
        conn = sqlite3.connect(args.db_path)
        conn.row_factory = sqlite3.Row
    else:
        conn = get_connection()

    try:
        validator = DataValidator(
            conn,
            expected_sources=args.sources,
            expected_activities=args.expected_activities,
        )
        results = validator.run_all()
    finally:
        conn.close()

    if args.json:
        print(json.dumps([
            {
                "name": r.name,
                "status": r.status,
                "expected": r.expected,
                "actual": r.actual,
                "message": r.message,
            }
            for r in results
        ], ensure_ascii=False, indent=2))
    else:
        _print_report(results)

    has_fail = any(r.status == "FAIL" for r in results)
    sys.exit(1 if has_fail else 0)


_STATUS_ICON = {"PASS": "✅", "WARN": "⚠️ ", "FAIL": "❌"}


def _print_report(results):
    width = 63
    print("═" * width)
    print("RunPulse Data Validation Report")
    print("═" * width)
    for r in results:
        icon = _STATUS_ICON.get(r.status, "?")
        name_padded = r.name.ljust(25)
        status_padded = r.status.ljust(5)
        line = f"{icon} {name_padded} {status_padded} ({r.actual})"
        if r.message:
            line += f"  — {r.message}"
        print(line)
    print("═" * width)
    n_pass = sum(1 for r in results if r.status == "PASS")
    n_warn = sum(1 for r in results if r.status == "WARN")
    n_fail = sum(1 for r in results if r.status == "FAIL")
    print(f"Result: {n_pass} PASS, {n_warn} WARN, {n_fail} FAIL")
    print("═" * width)


if __name__ == "__main__":
    main()

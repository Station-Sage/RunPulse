"""RunPulse 분석 CLI."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.analysis import (
    compare_this_month_vs_last,
    compare_this_week_vs_last,
    compare_today_vs_yesterday,
    deep_analyze,
    generate_ai_context,
    generate_report,
    weekly_trends,
)
from src.utils.clipboard import copy_to_clipboard
from src.utils.config import load_config


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _db_path() -> Path:
    config = load_config()
    db_value = config.get("database", {}).get("path")
    if db_value:
        return Path(db_value).expanduser()
    return _project_root() / "running.db"


def _save_output(text: str, save_path: str | None) -> None:
    if not save_path:
        return
    path = Path(save_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _to_jsonable(obj):
    if isinstance(obj, dict):
        return {k: _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_jsonable(v) for v in obj]
    return obj


def _json_for_command(conn: sqlite3.Connection, args, config: dict) -> dict:
    command = args.command

    if args.ai_context:
        return {
            "command": command,
            "type": "ai_context",
            "content": generate_ai_context(conn, context_type="brief", config=config),
        }

    if command in {"today", "week", "month", "race", "full"}:
        return {
            "command": command,
            "type": "report",
            "content": generate_report(conn, report_type=command, config=config),
        }

    if command == "deep":
        return {
            "command": command,
            "type": "deep_analysis",
            "content": deep_analyze(conn, activity_id=args.id, date=args.date, config=config),
        }

    if command == "compare":
        if args.period == "today":
            content = compare_today_vs_yesterday(conn)
        elif args.period == "month":
            content = compare_this_month_vs_last(conn)
        else:
            content = compare_this_week_vs_last(conn)
        return {"command": command, "type": "compare", "content": content}

    if command == "trends":
        return {
            "command": command,
            "type": "trends",
            "content": weekly_trends(conn, weeks=args.weeks),
        }

    return {"command": command, "type": "unknown", "content": None}


def _text_for_command(conn: sqlite3.Connection, args, config: dict) -> str:
    command = args.command

    if args.ai_context:
        return generate_ai_context(conn, context_type="brief", config=config)

    if command in {"today", "week", "month", "race", "full"}:
        return generate_report(conn, report_type=command, config=config)

    if command == "deep":
        result = deep_analyze(conn, activity_id=args.id, date=args.date, config=config)
        if result is None:
            return "활동을 찾을 수 없습니다."
        return json.dumps(_to_jsonable(result), ensure_ascii=False, indent=2)

    if command == "compare":
        if args.period == "today":
            result = compare_today_vs_yesterday(conn)
            title = "# 오늘 vs 어제 비교"
        elif args.period == "month":
            result = compare_this_month_vs_last(conn)
            title = "# 이번 달 vs 지난 달 비교"
        else:
            result = compare_this_week_vs_last(conn)
            title = "# 이번 주 vs 지난 주 비교"
        return title + "\n\n" + json.dumps(_to_jsonable(result), ensure_ascii=False, indent=2)

    if command == "trends":
        result = weekly_trends(conn, weeks=args.weeks)
        return "# 주간 추세\n\n" + json.dumps(_to_jsonable(result), ensure_ascii=False, indent=2)

    return "지원하지 않는 명령입니다."


def _add_common_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--clipboard", action="store_true", help="결과를 클립보드에 복사")
    parser.add_argument("--save", help="결과를 파일로 저장할 경로")
    parser.add_argument("--json", action="store_true", dest="as_json", help="JSON 형식으로 출력")
    parser.add_argument("--ai-context", action="store_true", help="AI 코치용 컨텍스트만 출력")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="RunPulse 분석 CLI",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    _add_common_options(parser)

    subparsers = parser.add_subparsers(dest="command", required=True)

    p_today = subparsers.add_parser("today", help="오늘 리포트")
    _add_common_options(p_today)

    p_week = subparsers.add_parser("week", help="주간 리포트")
    _add_common_options(p_week)
    p_week.add_argument("--weeks", type=int, default=1, help="최근 N주 기준")

    p_month = subparsers.add_parser("month", help="월간 리포트")
    _add_common_options(p_month)
    p_month.add_argument("--months", type=int, default=1, help="최근 N개월 기준")

    p_race = subparsers.add_parser("race", help="레이스 준비도 리포트")
    _add_common_options(p_race)
    p_race.add_argument("--date", help="레이스 날짜 (YYYY-MM-DD)")
    p_race.add_argument("--distance", type=float, help="레이스 거리 (km)")

    p_deep = subparsers.add_parser("deep", help="활동 상세 분석")
    _add_common_options(p_deep)
    p_deep.add_argument("--id", type=int, help="활동 ID")
    p_deep.add_argument("--date", help="활동 날짜 (YYYY-MM-DD)")

    p_compare = subparsers.add_parser("compare", help="기간 비교")
    _add_common_options(p_compare)
    p_compare.add_argument(
        "--period",
        choices=["today", "week", "month"],
        default="week",
        help="비교 기간",
    )

    p_trends = subparsers.add_parser("trends", help="주간 추세")
    _add_common_options(p_trends)
    p_trends.add_argument("--weeks", type=int, default=8, help="최근 N주 추세")

    p_full = subparsers.add_parser("full", help="전체 리포트")
    _add_common_options(p_full)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    config = load_config()
    db_path = _db_path()

    if not Path(db_path).exists():
        print(f"데이터베이스가 없습니다: {db_path}", file=sys.stderr)
        return 1

    conn = sqlite3.connect(str(db_path))
    try:
        if args.as_json:
            payload = _json_for_command(conn, args, config)
            output = json.dumps(_to_jsonable(payload), ensure_ascii=False, indent=2)
        else:
            output = _text_for_command(conn, args, config)

        _save_output(output, args.save)

        if args.clipboard:
            copy_to_clipboard(output)

        print(output)
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())

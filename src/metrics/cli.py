"""Metrics CLI 인터페이스 (보강 #10).

사용법:
    python -m src.metrics.cli status
    python -m src.metrics.cli recompute --days 7
    python -m src.metrics.cli recompute-all
    python -m src.metrics.cli recompute-single trimp --days 30
    python -m src.metrics.cli clear
"""
from __future__ import annotations

import argparse
import sqlite3
import logging
import sys

log = logging.getLogger(__name__)


def show_metric_status(conn: sqlite3.Connection):
    """메트릭 상태 요약 출력."""
    rows = conn.execute("""
        SELECT metric_name, provider, COUNT(*) as cnt,
               COUNT(CASE WHEN is_primary=1 THEN 1 END) as primary_count,
               AVG(confidence) as avg_confidence
        FROM metric_store
        WHERE provider LIKE 'runpulse%'
        GROUP BY metric_name, provider
        ORDER BY metric_name
    """).fetchall()

    if not rows:
        print("RunPulse 메트릭이 없습니다.")
        return

    print(f"\n{'Metric':<30} {'Provider':<25} {'Count':>6} {'Primary':>8} {'Avg Conf':>9}")
    print("-" * 80)
    total = 0
    for name, provider, count, primary, conf in rows:
        conf_str = f"{conf:.2f}" if conf else "N/A"
        print(f"{name:<30} {provider:<25} {count:>6} {primary:>8} {conf_str:>9}")
        total += count
    print("-" * 80)
    print(f"{'Total':<56} {total:>6}")

    # 소스 메트릭 요약
    src_rows = conn.execute("""
        SELECT provider, COUNT(*) as cnt
        FROM metric_store
        WHERE provider NOT LIKE 'runpulse%'
        GROUP BY provider
        ORDER BY cnt DESC
    """).fetchall()
    if src_rows:
        print(f"\n소스 메트릭:")
        for prov, cnt in src_rows:
            print(f"  {prov:<40} {cnt:>6}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="RunPulse Metrics CLI")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status", help="메트릭 상태 요약")

    p_recompute = sub.add_parser("recompute", help="최근 N일 재계산")
    p_recompute.add_argument("--days", type=int, default=7)

    sub.add_parser("recompute-all", help="전체 재계산 (90일)")
    sub.add_parser("clear", help="RunPulse 메트릭 삭제")

    p_single = sub.add_parser("recompute-single", help="특정 메트릭 재계산")
    p_single.add_argument("name", help="메트릭 이름 (예: trimp, utrs)")
    p_single.add_argument("--days", type=int, default=30)

    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return

    # DB 연결
    import os
    db_path = os.environ.get("RUNPULSE_DB", "runpulse.db")
    conn = sqlite3.connect(db_path)

    from src.metrics.engine import (
        recompute_recent, recompute_all, clear_runpulse_metrics,
        recompute_single_metric, ComputeResult,
    )

    if args.command == "status":
        show_metric_status(conn)

    elif args.command == "recompute":
        print(f"최근 {args.days}일 재계산 중...")
        results = recompute_recent(conn, days=args.days)
        print(f"완료: {len(results)}일 처리")

    elif args.command == "recompute-all":
        print("전체 재계산 중 (90일)...")
        results = recompute_all(conn)
        print(f"완료: {len(results)}일 처리")

    elif args.command == "clear":
        deleted = clear_runpulse_metrics(conn)
        print(f"삭제: {deleted}행")

    elif args.command == "recompute-single":
        print(f"'{args.name}' 메트릭 {args.days}일 재계산 중...")
        try:
            result = recompute_single_metric(conn, args.name, days=args.days)
            print(f"완료: {result.summary()}")
        except ValueError as e:
            print(f"오류: {e}")
            sys.exit(1)

    conn.close()


if __name__ == "__main__":
    main()

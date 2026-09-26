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

    p_all = sub.add_parser("recompute-all", help="재계산(기본: 전 기간, 범위 밖 이력은 보존)")
    p_all.add_argument("--days", type=int, default=None)
    sub.add_parser("recompute-missing", help="부하(TRIMP) 누락 활동 보정 + CTL/ATL/TSB 재계산")
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
        print("재계산 중 (" + (f"최근 {args.days}일" if args.days else "전 기간") + ", 범위 밖 이력 보존)...")
        results = recompute_all(conn, days=args.days)
        print(f"완료: {len(results)}일 처리")

    elif args.command == "recompute-missing":
        from src.metrics.engine import backfill_missing_loads, find_missing_load_dates
        n = len(find_missing_load_dates(conn))
        print(f"부하 누락 날짜 {n}일 — 보정 중...")
        results = backfill_missing_loads(conn)
        print(f"완료: {len(results)}일 재계산")

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

    conn.commit()  # 재계산 결과가 저장되도록(이전에는 commit 없이 닫혀 recompute가 무효였음)
    conn.close()


if __name__ == "__main__":
    main()

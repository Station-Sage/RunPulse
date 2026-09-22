"""자율 실행 현황 요약 — 원장·큐·게이트 상태를 한 화면에 출력한다.

용법: python3 -m scripts.autopilot.status
"""
from __future__ import annotations

import time
from datetime import datetime, timezone

from . import gate, ledger, queue, settings, worktree


def _fmt_ts(ts: float) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M")


def main() -> None:
    print("=== 예산 ===")
    entries = ledger.read_all()
    today = ledger.total_cost(ledger.since(24, entries))
    week = ledger.total_cost(ledger.since(24 * 7, entries))
    print(f"오늘   ${today:.2f} / ${settings.DAILY_MAX_USD:.2f}")
    print(f"이번주 ${week:.2f} / ${settings.WEEKLY_MAX_USD:.2f}")
    print(f"실행당 상한 ${settings.PER_RUN_MAX_USD:.2f} (총 실행 {len(entries)}건)")

    print("\n=== 최근 실행 5건 ===")
    for e in entries[-5:]:
        cost = e.get("cost_usd")
        cost_s = f"${cost:.3f}" if cost is not None else "N/A"
        print(f"  {_fmt_ts(e['ts'])}  {e.get('unit_id','?'):20s} {e.get('outcome','?'):8s} {cost_s}")
    if not entries:
        print("  (없음)")

    print("\n=== 게이트 ===")
    gr = gate.check()
    print(f"  지금 실행 가능: {gr.allowed}  ({gr.reason})")
    print(f"  STOP: {settings.STOP_PATH.exists()}  PAUSE: {settings.PAUSE_PATH.exists()}")

    print("\n=== 큐 (v0.3/data/phase-7-ui-renewal/BACKLOG.md) ===")
    malformed = queue.find_malformed_meta(settings.QUEUE_PATH)
    if malformed:
        print(f"  ⚠ 메타 주석 파싱 의심 {len(malformed)}건 (조용히 manual 취급됐을 수 있음):")
        for w in malformed:
            print(f"    {w}")
    items = queue.parse(settings.QUEUE_PATH)
    auto_items = [it for it in items if it.mode == "auto"]
    by_stage: dict[str, int] = {}
    for it in auto_items:
        by_stage[it.stage] = by_stage.get(it.stage, 0) + 1
    print(f"  자동 항목 {len(auto_items)}개: {by_stage or '(없음)'}")
    nr = queue.next_runnable(items)
    print(f"  다음 실행 대상: {nr.item_id if nr else '(없음)'}")
    for it in auto_items:
        if it.stage in ("blocked", "review"):
            print(f"    [{it.stage}/{it.kind}] {it.item_id}: {it.text[:60]}")

    print("\n=== worktree ===")
    print(f"  경로: {settings.WORKTREE_DIR} (존재: {settings.WORKTREE_DIR.exists()})")
    if settings.WORKTREE_DIR.exists():
        base = "renew/data-architecture"
        ahead = worktree.commits_ahead_of(base)
        print(f"  {base} 대비 {ahead}개 커밋 앞섬, 청결: {worktree.is_clean()}")

    if settings.DECISIONS_PATH.exists():
        n = settings.DECISIONS_PATH.read_text(encoding="utf-8").count("\n## [")
        print(f"\n=== 대기 중인 사람 결정 ===\n  DECISIONS.md 섹션 {n}개 — {settings.DECISIONS_PATH}")


if __name__ == "__main__":
    main()

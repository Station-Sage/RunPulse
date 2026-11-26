"""기존 failed 항목 1회 이행 — DECISIONS.md 에 질문이 남아 있으면 asked 카드로 재분류하고 needs_decision 으로 되돌린다.

사용: .venv/bin/python -m scripts.autopilot.migrate_failed [--apply]   (기본은 dry-run, 사용자 지시 시에만 --apply)
"""
from __future__ import annotations

import argparse
from pathlib import Path

from scripts.audit import decisions

from . import fail_handling, queue, settings


def migrate(queue_path: Path, decisions_md: Path, decisions_path: Path | None = None, apply: bool = False) -> list[str]:
    """fail_kind 없는 failed 항목 중 DECISIONS.md 에 같은 id 섹션이 있는 것만 이행. 이행(대상) id 목록 반환."""
    try:
        secs = fail_handling.parse_sections(decisions_md.read_text(encoding="utf-8"))
    except OSError:
        return []
    done: list[str] = []
    for it in queue.parse(queue_path):
        sec = next((s for s in secs if s["id"] == it.item_id), None)
        if it.stage != "failed" or it.fail_kind or sec is None:
            continue
        done.append(it.item_id)
        if apply:
            decisions.append([fail_handling.build_asked_card(it.item_id, sec, it.text, 1)], decisions_path)
            queue.update_item(queue_path, it.item_id, stage="needs_decision", asks=1, fail_kind="asked",
                              fail_reason=f"결정 요청: {sec['title']}"[:300])
    return done


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    md = settings.WORKTREE_DIR / fail_handling.DECISIONS_DIR / "DECISIONS.md"
    ids = migrate(settings.QUEUE_PATH, md, apply=args.apply)
    print(("이행: " if args.apply else "이행 대상(dry-run): ") + (", ".join(ids) or "없음"))


if __name__ == "__main__":
    main()

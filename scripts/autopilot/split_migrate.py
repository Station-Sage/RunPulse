"""분할 결정 카드 도입 전에 queued 로 등록된 SPLIT-* 항목을 1회 이행 — 결정 카드를 만들고 needs_decision 으로 돌린다.

사용: .venv/bin/python -m scripts.autopilot.split_migrate [--apply]   (기본은 dry-run, 사용자 지시 시에만 --apply)
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

from scripts.audit import decisions

from . import queue, settings, split_card

_TEXT = re.compile(r"\(후속: (?P<origin>\S+) 에서 발견\).*? (?P<path>\S+) 가 (?P<lines>\d+)줄")


def migrate(queue_path: Path, decisions_path: Path | None = None, apply: bool = False) -> list[str]:
    """실행 이력 없는 queued SPLIT-* 항목 → split 카드 + needs_decision. 이행(대상) id 목록 반환."""
    have = {r["id"] for r in decisions.load(decisions_path)}
    done: list[str] = []
    for it in queue.parse(queue_path):
        m = _TEXT.search(it.text)
        if not it.item_id.startswith("SPLIT-") or it.stage != "queued" or it.attempts or it.item_id in have or not m:
            continue
        done.append(it.item_id)
        if apply:
            decisions.append([split_card.build_split_card(it.item_id, m["path"], int(m["lines"]), m["origin"])], decisions_path)
            queue.update_item(queue_path, it.item_id, stage="needs_decision")
    return done


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    ids = migrate(settings.QUEUE_PATH, apply=args.apply)
    print(("이행: " if args.apply else "이행 대상(dry-run): ") + (", ".join(ids) or "없음"))


if __name__ == "__main__":
    main()

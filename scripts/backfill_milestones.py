#!/usr/bin/env python3
"""마일스톤 1회 백필(ADR-057). 사용: PYTHONPATH=. python3 scripts/backfill_milestones.py (--db <path> | --all-users) [--apply]

기본은 dry-run(종류별 증감만 출력, 쓰기 없음). --apply 는 DB 마다 같은 폴더에 sqlite backup API 로 백업한 뒤 적용한다.
재실행해도 같은 결과(멱등). 운영 컨테이너에서는 앱과 같은 data/users 경로로 실행한다.
"""
import argparse
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.services.milestone_backfill import run_backfill  # noqa: E402


def _targets(a) -> list[Path]:
    if a.db:
        return [Path(a.db)]
    from src.utils.user_context import list_user_ids, users_root
    return [p for p in (users_root() / uid / "running.db" for uid in list_user_ids()) if p.exists()]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--db")
    g.add_argument("--all-users", action="store_true")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args(argv)
    for path in _targets(a):
        with sqlite3.connect(str(path), timeout=30) as c:
            if a.apply:
                bak = path.with_name(f"{path.name}.bak-milestones-{datetime.now():%Y%m%d%H%M%S}")
                with sqlite3.connect(str(bak)) as b:
                    c.backup(b)
                print("backup:", bak)
            out = run_backfill(c, apply=a.apply)
        print(("applied" if a.apply else "dry-run"), path, out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

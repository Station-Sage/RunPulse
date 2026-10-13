#!/usr/bin/env python3
"""운영 점검 — `data/users/` 의 디렉터리가 uid 허용 규칙(SRV-13)에 맞는지 읽기 전용으로 확인한다 (S3-1).

규칙에 맞지 않는 디렉터리는 S3 3단계 이후 `get_db_path`·`get_config_path` 가 거부(InvalidUserId)하고,
앱 시작 시 `list_user_ids()` 가 건너뛴다. enforce 로 가기 **전에** 운영 서버에서 한 번 실행해 영향 목록을 본다.

사용법:
    python scripts/check_user_dirs.py [--root PATH] [--show-names]

- 기본은 이름을 마스킹(`ab***(len=N)`)해 출력한다. `--show-names` 는 터미널에서 직접 볼 때만 쓴다.
- 파일·디렉터리를 만들거나 바꾸지 않는다. 심볼릭 링크는 따로 표시한다(get_db_path 가 링크 이탈을 거부).

종료 코드: 0 = 위반 없음, 1 = 위반 있음, 2 = 루트 디렉터리 없음
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.utils.user_context import InvalidUserId, mask_uid, validate_uid  # noqa: E402


def check(root: Path) -> list[tuple[str, str]]:
    """(이름, 사유) 목록 — 사유는 'rule' | 'symlink-escape'."""
    problems: list[tuple[str, str]] = []
    for d in sorted(root.iterdir()):
        if not d.is_dir():
            continue
        try:
            validate_uid(d.name)
        except InvalidUserId:
            problems.append((d.name, "rule"))
            continue
        if d.is_symlink() and d.resolve().parent != root.resolve():
            problems.append((d.name, "symlink-escape"))
    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", type=Path, default=ROOT / "data" / "users")
    ap.add_argument("--show-names", action="store_true", help="마스킹하지 않고 이름 출력")
    args = ap.parse_args(argv)
    if not args.root.is_dir():
        print(f"사용자 디렉터리 없음: {args.root}")
        return 2
    total = sum(1 for d in args.root.iterdir() if d.is_dir())
    problems = check(args.root)
    for name, reason in problems:
        shown = name if args.show_names else mask_uid(name)
        print(f"위반 [{reason}] {shown}")
    print(f"검사 {total}개 중 위반 {len(problems)}개")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())

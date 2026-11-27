"""의존성 설치 — 사용자가 결정함에서 승인한 누락 패키지만 허용 목록 방식으로 설치한다.

verify 가 'Cannot find module'/'No module named' 로 실패하고 환경 복구(링크)로 해결되지 않으면, 오토파일럿은 임의 설치 대신
결정 카드(install_dep)를 올린다. 승인 시 npm 은 워크트리 frontend(package.json 변경이 항목 브랜치에 남음), pip 은 메인 .venv 에 설치한다.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

from scripts.autopilot import settings

_NAME = re.compile(r"^(@[a-z0-9][\w.-]*/)?[a-z0-9][\w.-]*$", re.I)


def command(eco: str, name: str, root: Path, main: Path) -> tuple[list[str], Path] | None:
    """(argv, cwd). 허용 안 되는 생태계·패키지명이면 None."""
    if not _NAME.match(name or ""):
        return None
    if eco == "npm":
        return ["npm", "install", "-D", name], root / "frontend"
    if eco == "pip":
        return [str(main / ".venv" / "bin" / "python"), "-m", "pip", "install", name], main
    return None


def install(eco: str, name: str, root: Path | None = None, main: Path | None = None, run=subprocess.run) -> tuple[bool, str]:
    root, main = root or settings.WORKTREE_DIR, main or settings._main_checkout()
    cmd = command(eco, name, root, main)
    if cmd is None:
        return False, f"허용되지 않는 설치 요청: {eco} {name!r}"
    try:
        r = run(cmd[0], cwd=cmd[1], capture_output=True, text=True, timeout=600)
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, f"설치 실행 실패: {e}"
    tail = (r.stdout[-300:] + r.stderr[-300:]).strip()
    return r.returncode == 0, f"{' '.join(cmd[0])} → rc={r.returncode} {tail}"

"""격리 실행 환경 — autopilot 전용 git worktree/브랜치 보장 + 청결 상태 확인.

자동 실행은 사용자의 실제 작업 브랜치(예: renew/data-architecture)를 절대 건드리지
않는다. 항상 별도 브랜치(settings.AUTOPILOT_BRANCH)의 별도 worktree
(settings.WORKTREE_DIR, .claude/worktrees/ 하위 — 기존 gitignore 규칙 적용됨)에서만
파일을 쓰고 커밋한다. 병합은 사람이 한다.
"""
from __future__ import annotations

import subprocess

from . import settings


def _run(args: list[str], cwd=None) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=60)


def ensure() -> None:
    """worktree가 없으면 만든다. 브랜치가 없으면 현재 HEAD에서 새로 만든다."""
    if settings.WORKTREE_DIR.exists():
        return
    settings.WORKTREE_DIR.parent.mkdir(parents=True, exist_ok=True)
    branch_exists = _run(
        ["git", "rev-parse", "--verify", settings.AUTOPILOT_BRANCH],
        cwd=settings.PROJECT_ROOT,
    ).returncode == 0
    args = ["git", "worktree", "add", str(settings.WORKTREE_DIR)]
    args += [settings.AUTOPILOT_BRANCH] if branch_exists else ["-b", settings.AUTOPILOT_BRANCH]
    r = _run(args, cwd=settings.PROJECT_ROOT)
    if r.returncode != 0:
        raise RuntimeError(f"worktree 생성 실패: {r.stderr}")


def is_clean() -> bool:
    """이전 실행이 커밋하지 않은 변경을 남겼으면 그 위에 새 작업을 얹지 않는다."""
    if not settings.WORKTREE_DIR.exists():
        return True
    r = _run(["git", "status", "--porcelain"], cwd=settings.WORKTREE_DIR)
    return r.returncode == 0 and not r.stdout.strip()


def commits_ahead_of(base_branch: str) -> int:
    r = _run(["git", "rev-list", "--count", f"{base_branch}..{settings.AUTOPILOT_BRANCH}"],
              cwd=settings.PROJECT_ROOT)
    return int(r.stdout.strip()) if r.returncode == 0 and r.stdout.strip().isdigit() else -1

"""격리 실행 환경 — autopilot 전용 git worktree/브랜치 보장 + 청결 상태 확인.

자동 실행은 사용자의 실제 작업 브랜치(예: renew/data-architecture)를 절대 건드리지
않는다. 항상 별도 브랜치(settings.AUTOPILOT_BRANCH)의 별도 worktree
(settings.WORKTREE_DIR, .claude/worktrees/ 하위 — 기존 gitignore 규칙 적용됨)에서만
파일을 쓰고 커밋한다. 병합은 사람이 한다.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from . import settings

# git 에 추적되지 않는 실행 의존성 — verify 가 격리 워크트리에서 돌려면 메인 체크아웃 것을 심볼릭 링크로 걸어야 한다.
PROVISION_PATHS = (".venv", "frontend/node_modules", "scripts/synth_smoke/pw/node_modules")


def provision(wt: Path | None = None, src: Path | None = None) -> list[str]:
    """누락된 untracked 의존성(.venv·node_modules)을 메인 체크아웃에서 링크한다. 새로 건 경로 목록을 반환.

    깨진 링크는 다시 건다. 링크는 `node_modules/` 패턴에 안 걸리므로 워크트리 info/exclude 에 올려 dirty 판정을 막는다.
    """
    wt, src = wt or settings.WORKTREE_DIR, src or settings._main_checkout()
    done: list[str] = []
    if not wt.exists() or wt.resolve() == src.resolve():
        return done
    for rel in PROVISION_PATHS:
        target, link = src / rel, wt / rel
        if not target.exists() or link.exists():
            continue
        if link.is_symlink():
            link.unlink()
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(target)
        done.append(rel)
    if done:
        ex = _run(["git", "rev-parse", "--path-format=absolute", "--git-path", "info/exclude"], cwd=wt).stdout.strip()
        if ex:
            exp = Path(ex)
            exp.parent.mkdir(parents=True, exist_ok=True)
            cur = exp.read_text(encoding="utf-8") if exp.exists() else ""
            add = [r for r in PROVISION_PATHS if r not in cur.splitlines()]
            if add:
                exp.write_text(cur + ("" if cur.endswith("\n") or not cur else "\n") + "\n".join(add) + "\n", encoding="utf-8")
    return done


def verify_env(base: dict | None = None) -> dict:
    """verify 서브프로세스용 환경 — systemd 의 최소 PATH 에서도 venv·node·bun 이 잡히고 HOME 이 보장되도록 정규화한다."""
    env = dict(base if base is not None else os.environ)
    home = env.get("HOME") or str(Path.home())
    extra = [str(settings.PROJECT_ROOT / ".venv/bin"), f"{home}/.local/bin", f"{home}/.bun/bin", "/usr/local/bin", "/usr/bin", "/bin"]
    node = shutil.which("node", path=env.get("PATH"))
    if node:
        extra.insert(0, str(Path(node).parent))
    cur = [p for p in env.get("PATH", "").split(":") if p]
    env["PATH"] = ":".join(dict.fromkeys(extra + cur))
    env["HOME"] = home
    env["VIRTUAL_ENV"] = str(settings.PROJECT_ROOT / ".venv")
    env["CI"] = "1"
    for k in ("PYTHONHOME", "PYTHONPATH", "NODE_OPTIONS"):
        env.pop(k, None)
    return env


def _run(args: list[str], cwd=None) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=60)


def ensure() -> None:
    """worktree가 없으면 만든다. 브랜치가 없으면 현재 HEAD에서 새로 만든다."""
    if settings.WORKTREE_DIR.exists():
        provision()
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
    provision()


def is_clean() -> bool:
    """이전 실행이 커밋하지 않은 변경을 남겼으면 그 위에 새 작업을 얹지 않는다."""
    if not settings.WORKTREE_DIR.exists():
        return True
    r = _run(["git", "status", "--porcelain"], cwd=settings.WORKTREE_DIR)
    return r.returncode == 0 and not r.stdout.strip()


DIRTY = "worktree가 청결하지 않음 (이전 실행 잔재 의심)"


def discard_leftovers() -> list[str]:
    """자율 worktree 의 미커밋 변경·미추적 파일을 폐기하고 그 경로 목록을 돌려준다(항목 재시도 시 재생성되므로 백업하지 않는다)."""
    wt = settings.WORKTREE_DIR
    if not wt.exists() or wt.resolve() == settings.PROJECT_ROOT.resolve():
        return []
    r = _run(["git", "status", "--porcelain"], cwd=wt)
    names = [ln[3:].strip() for ln in r.stdout.splitlines() if ln.strip()] if r.returncode == 0 else []
    _run(["git", "checkout", "--", "."], cwd=wt)
    _run(["git", "clean", "-fd"], cwd=wt)
    return names


def sync() -> str:
    """base 브랜치 최신 커밋을 autopilot 브랜치로 merge(79커밋 rebase 는 커밋마다 충돌 지점이 생겨 깨지기 쉬움).

    ensure()는 worktree가 없을 때만 만들고 그 뒤로는 손대지 않으므로, 이걸 부르지
    않으면 worktree는 처음 만들어진 시점의 커밋에 영원히 멈춰 있는다 — base에서
    이후 추가된 문서·코드를 에이전트가 못 보게 된다(실제로 한 번 이렇게 실패함,
    2026-09-22: REVIEW-02/03·DECISIONS.md가 없는 채로 작업해 예산 초과로 실패).

    Returns: "" 성공, 아니면 차단 사유(dirty | merge_conflict).
    """
    if not settings.WORKTREE_DIR.exists():
        return ""
    if not is_clean():
        removed = discard_leftovers()
        if not is_clean():
            return f"{DIRTY} — 자동 정리 실패"
        if removed:
            from scripts.audit import progress
            progress.mark(f"[worktree] 이전 실행 잔재 {len(removed)}건 폐기(재시도 시 재생성): {', '.join(removed[:10])}{' 외' if len(removed) > 10 else ''}")
    return _merge_base()


GENERATED = "v0.3/data/files_index.md"


def _merge_base() -> str:
    """base 를 autopilot 브랜치로 merge. 생성 파일(files_index.md)만 충돌이면 base 쪽을 취하고 재생성, 그 외 충돌은 abort 후 사유 반환."""
    cwd = settings.WORKTREE_DIR
    r = _run(["git", "merge", "--no-edit", settings.BASE_BRANCH], cwd=cwd)
    if r.returncode == 0:
        return ""
    conflicted = _run(["git", "diff", "--name-only", "--diff-filter=U"], cwd=cwd).stdout.split()
    if conflicted == [GENERATED]:
        _run(["git", "checkout", "--theirs", GENERATED], cwd=cwd)
        _run(["python3", "scripts/gen_files_index.py"], cwd=cwd)
        _run(["git", "add", GENERATED], cwd=cwd)
        if _run(["git", "commit", "--no-edit"], cwd=cwd).returncode == 0:
            return ""
    _run(["git", "merge", "--abort"], cwd=cwd)
    return f"{settings.BASE_BRANCH} 병합 충돌 — 수동 개입 필요: {', '.join(conflicted) or r.stderr.strip()[:300]}"


def commits_ahead_of(base_branch: str) -> int:
    r = _run(["git", "rev-list", "--count", f"{base_branch}..{settings.AUTOPILOT_BRANCH}"],
              cwd=settings.PROJECT_ROOT)
    return int(r.stdout.strip()) if r.returncode == 0 and r.stdout.strip().isdigit() else -1

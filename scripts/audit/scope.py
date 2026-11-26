"""테스트 범위 축소 — 단위가 바꾼 파일에서 스윕할 화면을 뽑는다. 전체 스윕은 라운드 종료(운영 반영 직전) 때 1회만 돌린다.

screens_for: None=전 화면(공용 코드 변경), []=스윕 불필요(백엔드·문서만), 목록=그 화면들만.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from scripts.autopilot import settings

from . import inventory

ROUTES = "frontend/src/routes/"
FRONT = "frontend/"


def changed_files(worktree: Path | None = None, base: str | None = None) -> list[str]:
    """개발 워크트리가 기준 브랜치 대비 바꾼 파일(라운드 누적). git 실패 시 None 대신 빈 목록이 아니라 예외로 올려 전체 스윕을 유도한다."""
    wt = worktree or settings.WORKTREE_DIR
    out = subprocess.run(["git", "diff", "--name-only", f"{base or settings.BASE_BRANCH}...HEAD"], cwd=wt, capture_output=True, text=True, timeout=60, check=True)
    return [ln for ln in out.stdout.splitlines() if ln.strip()]


def screens_for(files: list[str], all_screens: list[str] | None = None) -> list[str] | None:
    all_screens = inventory.frontend_screens() if all_screens is None else all_screens
    hit: set[str] = set()
    for f in files:
        if f.startswith(ROUTES):
            rel = f[len(ROUTES):]
            d = "/".join(s for s in rel.split("/")[:-1] if not (s.startswith("(") and s.endswith(")")))
            base = "/" + d
            name = rel.rsplit("/", 1)[-1]
            if name.startswith("+layout"):
                hit.update(s for s in all_screens if s == base or s.startswith(base.rstrip("/") + "/"))
            elif name.startswith("+page"):
                hit.add(base)
            else:
                hit.update(s for s in all_screens if s == base or s.startswith(base.rstrip("/") + "/"))
        elif f.startswith(FRONT) and not f.startswith(FRONT + "tests/") and not f.endswith((".md", ".test.ts", ".spec.ts")):
            return None
    return sorted(s for s in hit if s in all_screens)


def unit_screens() -> list[str] | None:
    """현재 워크트리 변경분에서 스윕 대상 화면을 정한다. 판단 실패 시 안전하게 전 화면."""
    try:
        return screens_for(changed_files())
    except Exception:
        return None

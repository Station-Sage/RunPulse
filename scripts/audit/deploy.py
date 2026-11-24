"""운영 반영 — 안쪽 루프(개발→테스트→수정)에서 통과한 단위를 운영 폴더(BASE_BRANCH)에 fast-forward 병합한다.

run(units_done, sh=...) → {"ran", "outcome", "reason", "commits"}. 안전 가드(하나라도 어기면 아무것도 바꾸지 않고 사유 반환):
  - 이번 라운드에 통과(done)한 단위가 1건 이상
  - 운영 폴더가 BASE_BRANCH 이고 추적 파일 변경 없음
  - autopilot 브랜치에 반영할 커밋이 있음, 그리고 BASE_BRANCH 의 후손(fast-forward 가능; 갈라졌으면 중단·알림)
  - autopilot 워크트리에서 전체 pytest 통과(실패 시 실패 테스트만 1회 재실행 — 순서 의존 flaky 흡수; 그래도 실패면 병합 안 함)
병합 후 frontend/ 가 바뀌었으면 운영 폴더에서 `npm run build` (gunicorn --reload 는 코드만 반영하므로 정적 빌드는 직접 생성).
push 는 하지 않는다. 롤백 = 운영 폴더에서 `git reset --hard <이전 HEAD>`(결과의 prev 값).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.autopilot import settings


def prod_dir() -> Path:
    r = subprocess.run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], cwd=settings.PROJECT_ROOT,
                       capture_output=True, text=True, check=True)
    return Path(r.stdout.strip()).parent


def _sh(args: list[str], cwd: Path) -> tuple[int, str]:
    slow = "pytest" in args
    try:
        r = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=3000 if slow else 900)
    except subprocess.TimeoutExpired:
        return 124, "시간 초과"
    return r.returncode, (r.stdout + r.stderr).strip()


def _tests_pass(sh, prod: Path) -> tuple[bool, str]:
    py = sys.executable  # 운영 폴더엔 .venv 가 없을 수 있다(루프를 돌리는 인터프리터 사용)
    cmd = [py, "-m", "pytest", "tests/", "-q", "--no-header"]
    rc, out = sh(cmd, settings.WORKTREE_DIR)
    if not rc:
        return True, ""
    rc, out2 = sh([py, "-m", "pytest", "tests/", "-q", "--lf"], settings.WORKTREE_DIR)
    return (not rc), (out2 or out)[-200:]


def run(units_done: int, *, sh=_sh, prod: Path | None = None) -> dict:
    base, br = settings.BASE_BRANCH, settings.AUTOPILOT_BRANCH
    if units_done < 1:
        return {"ran": False, "reason": "통과한 단위 없음"}
    prod = prod or prod_dir()
    rc, cur = sh(["git", "rev-parse", "--abbrev-ref", "HEAD"], prod)
    if rc or cur != base:
        return {"ran": False, "reason": f"운영 폴더 브랜치가 {base} 가 아님({cur})"}
    rc, dirty = sh(["git", "status", "--porcelain", "--untracked-files=no"], prod)
    if rc or dirty:
        return {"ran": False, "reason": "운영 폴더에 추적 파일 변경 있음 — 반영 중단"}
    rc, ahead = sh(["git", "rev-list", "--count", f"{base}..{br}"], prod)
    if rc or not ahead.isdigit():
        return {"ran": False, "reason": f"{br} 확인 실패: {ahead[:100]}"}
    if int(ahead) == 0:
        return {"ran": False, "reason": "반영할 커밋 없음"}
    if sh(["git", "merge-base", "--is-ancestor", base, br], prod)[0]:
        return {"ran": True, "outcome": "failed", "reason": f"{br} 가 {base} 의 후손이 아님(갈라짐) — 사람 확인 필요"}
    ok, tail = _tests_pass(sh, prod)
    if not ok:
        return {"ran": True, "outcome": "failed", "commits": int(ahead), "reason": f"전체 테스트 실패 — 병합 안 함: {tail}"}
    _, prev = sh(["git", "rev-parse", "HEAD"], prod)
    rc, out = sh(["git", "merge", "--ff-only", br], prod)
    if rc:
        return {"ran": True, "outcome": "failed", "reason": f"병합 실패: {out[:200]}"}
    _, files = sh(["git", "diff", "--name-only", prev, "HEAD"], prod)
    built = ""
    if any(f.startswith("frontend/") for f in files.splitlines()):
        rc, out = sh(["npm", "run", "build"], prod / "frontend")
        built = "빌드 성공" if not rc else f"빌드 실패: {out[-200:]}"
        if rc:
            return {"ran": True, "outcome": "failed", "commits": int(ahead), "prev": prev, "reason": built}
    return {"ran": True, "outcome": "done", "commits": int(ahead), "prev": prev, "reason": built or "백엔드만 반영"}

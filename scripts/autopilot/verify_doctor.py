"""verify 진단·사전 점검 — 실패 원인을 종류별로 가르고, 실행 불가능한 verify 를 큐 진입 전에 잡는다.

diagnose: missing_target(대상 파일 없음)|usage(인자·모듈 오류)|absence_hit(`! grep`·`test $(grep …|wc -l) -eq 0` 부재 검사 적중)|real(실제 테스트 실패)|env.
lint: 큐에 넣기 전 verify 가 실행 가능한지 점검(존재하지 않는 테스트 파일·스크립트, 범위 밖 파일에 이미 적중하는 `! grep` 부재 검사).
"""
from __future__ import annotations

import re
import shlex
import subprocess
from pathlib import Path

TAG = re.compile(r"^\[(missing_target|usage|absence_hit|real)\]\s*")
REPEAT_FATAL = ("missing_target", "usage")  # 같은 원인 반복 시 재시도 무의미
MAX_ATTEMPTS = 3
_ENV = ("No module named pytest", "command not found", "Cannot find module", "MODULE_NOT_FOUND")
_MISSING = ("No test files found", "Could not find", "no tests found", "file or directory not found",
            "ERROR: file or directory not found", "ENOENT", "Cannot find test")
_USAGE = ("ERR_INVALID_ARG_TYPE", "usage:", "Usage:", "unrecognized arguments", "required argument", "Missing required",
          "error: the following arguments are required")
_TESTFILE = re.compile(r"(?:^|[\s'\"])((?:[\w./-]*/)?[\w.-]*(?:\.test\.(?:mjs|ts|js)|test_[\w]+\.py))\b")


def is_negative_grep(cmd: str) -> bool:
    return bool(re.search(r"(?:^|&&|;)\s*(?:cd [^&;]+&&\s*)?!\s*grep\b", cmd))


_COUNT_ABSENCE = re.compile(r"test\s+\$\(\s*(grep\b.*?)\s*\|\s*wc\s+-l\s*\)\s*-eq\s+0")


def is_absence_check(cmd: str) -> bool:
    """`! grep …` 또는 `test $(grep … | wc -l) -eq 0` — 특정 패턴이 0건이어야 통과하는 부재 검사."""
    return is_negative_grep(cmd) or bool(_COUNT_ABSENCE.search(cmd))


def diagnose(cmd: str, rc: int | None, output: str) -> str:
    """verify 실패 → env|missing_target|usage|absence_hit|real."""
    if rc == 127 or any(m in output for m in _ENV):
        return "env"
    if any(m in output for m in _MISSING):
        return "missing_target"
    if any(m in output for m in _USAGE):
        return "usage"
    if is_absence_check(cmd) and rc == 1:
        return "absence_hit"
    return "real"


_ERRLINE = re.compile(r"error|cannot find|not ok|fail|assert|traceback|no module named", re.I)
_WARNLINE = re.compile(r"^\s*(warn|hint)\b", re.I)


def tag_reason(kind: str, output: str, limit: int = 2500) -> str:
    """사유 문자열 — svelte 경고가 앞을 채워 진짜 오류가 잘리지 않게 오류 줄을 먼저 둔다."""
    lines = [ln for ln in output.splitlines() if not _WARNLINE.match(ln)]
    errs = [ln for ln in lines if _ERRLINE.search(ln)]
    rest = [ln for ln in lines if ln not in errs]
    body = "\n".join(errs[:30] + (["--"] + rest if rest and errs else rest))
    return f"[{kind}] {body[:limit]}"


_JS_MOD = re.compile(r"Cannot find (?:package|module) '(@[\w.-]+/[\w.-]+|[\w][\w.-]*)'")
_PY_MOD = re.compile(r"No module named '?([A-Za-z_][\w]*)")


def missing_package(output: str) -> tuple[str, str]:
    """누락된 외부 의존성 (생태계 'npm'|'pip', 패키지명). 상대경로 모듈·pytest 자체 부재는 제외 — 없으면 ('','')."""
    m = _JS_MOD.search(output)
    if m:
        return "npm", m.group(1)
    m = _PY_MOD.search(output)
    if m and m.group(1) != "pytest":
        return "pip", m.group(1)
    return "", ""


_RUNNERS = ("vitest", "jest", "mocha")


def _runner_installed(name: str, root: Path) -> bool:
    if (root / "frontend" / "node_modules" / ".bin" / name).exists():
        return True
    pkg = root / "frontend" / "package.json"
    return pkg.exists() and f'"{name}"' in pkg.read_text(encoding="utf-8")


def split_reason(reason: str) -> tuple[str, str]:
    m = TAG.match(reason or "")
    return (m.group(1), reason[m.end():]) if m else ("", reason or "")


def should_stop(attempts_done: int, kind: str, prev_reason: str) -> bool:
    """재시도 예산 소진 또는 '고칠 수 없는 같은 원인' 반복이면 True(= 실패 카드)."""
    if attempts_done >= MAX_ATTEMPTS:
        return True
    prev_kind, _ = split_reason(prev_reason)
    return kind in REPEAT_FATAL and prev_kind == kind


def retry_hint(kind: str, body: str) -> str:
    """진단별 재시도 지시문."""
    head = f"직전 시도는 독립 verify 에서 실패했습니다(진단: {kind}). 같은 실수를 반복하지 마세요.\n"
    tail = f"\n--- verify 실패 출력 ---\n{body}\n"
    if kind == "missing_target":
        return head + "verify 가 가리키는 테스트 파일이 없습니다. 그 파일을 직접 만들고(경로는 verify 그대로) 통과시키세요." + tail
    if kind == "absence_hit":
        return head + "`! grep` 부재 검사에 아직 걸리는 위치가 남아 있습니다. 아래 출력의 모든 위치를 고쳐서 0건으로 만드세요." + tail
    if kind == "usage":
        return head + "verify 명령의 인자·모듈 사용이 잘못됐습니다. 명령이 요구하는 입력을 만족하도록 구현/스크립트를 고치세요." + tail
    return head + "아래 실패를 원인부터 고쳐 통과시키세요." + tail


_HITLINE = re.compile(r"^\s*(?:\./)?([\w@./-]+\.[A-Za-z]{1,6}):\d+", re.M)
_FAILFILE = re.compile(r"((?:[\w@.-]+/)*[\w.-]*(?:\.test\.(?:mjs|ts|js)|test_[\w]+\.py))(?::\d+|\b)")


def fix_target(kind: str, out: str, scope: list[str]) -> str:
    """자동으로 범위에 더할 파일 — absence_hit 은 적중 위치, real 은 실패한 테스트 파일. scope 안에 이미 있거나 못 찾으면 ''."""
    pat = _HITLINE if kind == "absence_hit" else _FAILFILE if kind == "real" else None
    if pat is None:
        return ""
    inside = [s.rstrip("/") for s in scope]
    for m in pat.finditer(out):
        root = re.search(r"(?:^|/)((?:frontend|tests|src|scripts)/.*)$", m.group(1))
        path = root.group(1) if root else m.group(1)
        if not any(path == s or path.startswith(s + "/") for s in inside):
            return path
    return ""


def hit_target(cmd: str, scope: list[str], root: Path) -> str:
    """부재 검사의 grep 부분을 다시 돌려 scope 밖 적중 파일(repo 기준)을 찾는다 — 출력에 위치가 없는 count 형 검사용. 없으면 ''."""
    m = _COUNT_ABSENCE.search(cmd)
    if not m or not root.exists():
        return ""
    base = "frontend/" if "cd frontend" in cmd else ""
    try:
        r = subprocess.run(["bash", "-c", m.group(1)], cwd=root / base.rstrip("/"), capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    inside = [s.rstrip("/") for s in scope]
    for ln in r.stdout.splitlines():
        f = ln.split(":", 1)[0].removeprefix("./")
        full = f if f.startswith(base) else base + f
        if f and not any(full == s or full.startswith(s + "/") for s in inside):
            return full
    return ""


def failed_diagnosis(reason: str, scope: list[str]) -> tuple[str, str, str]:
    """failed 항목의 fail_reason → (진단, 실패 출력, 범위 밖 원인 파일). 진단 태그가 없으면 ('', reason, '')."""
    kind, body = split_reason(reason)
    return kind, body, (fix_target(kind, body, scope) if kind else "")


def lint(verify: list[str], scope: list[str], root: Path) -> list[str]:
    """실행 불가능한 verify 의 문제 목록(빈 리스트 = 통과). scope 안 파일은 생성 예정이므로 허용."""
    problems: list[str] = []
    scoped = {s.rstrip("/") for s in scope}
    for cmd in verify:
        for m in _TESTFILE.finditer(cmd):
            path = m.group(1)
            cand = [path, f"frontend/{path}"] if "cd frontend" in cmd else [path]
            if any((root / c).exists() or c in scoped for c in cand):
                continue
            problems.append(f"테스트 파일 `{path}` 이 디스크에도 scope 에도 없음")
        try:
            toks = shlex.split(cmd.split("|")[0])
        except ValueError:
            continue
        for i, t in enumerate(toks[:-1]):
            if t == "node" and toks[i + 1].endswith((".mjs", ".js")) and not toks[i + 1].startswith("-"):
                script = toks[i + 1]
                if not (root / script).exists() and script not in scoped:
                    problems.append(f"스크립트 `{script}` 없음")
        for r in _RUNNERS:
            if re.search(rf"\b{r}\b", cmd) and not _runner_installed(r, root):
                problems.append(f"테스트 러너 `{r}` 가 설치돼 있지 않음 — `node --test` 또는 pytest 사용")
        problems.extend(_absence_baseline(cmd, scoped, root))
    return problems


def _absence_baseline(cmd: str, scoped: set[str], root: Path) -> list[str]:
    """`! grep` 부재 검사가 현재 트리에서 범위 밖 파일에 이미 적중하면 항목이 고칠 수 없다 — 패턴이 과도하게 넓다."""
    if not is_negative_grep(cmd) or not root.exists():
        return []
    try:
        r = subprocess.run(["bash", "-c", cmd], cwd=root, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return []
    if r.returncode != 1 or not r.stdout.strip():
        return []
    base = "frontend/" if "cd frontend" in cmd else ""
    outside = set()
    for ln in r.stdout.splitlines():
        f = ln.split(":", 1)[0]
        full = f if f.startswith(base) else base + f
        if not any(full == sc or full.startswith(sc + "/") for sc in scoped):
            outside.add(full)
    if not outside:
        return []
    return [f"부재 검사 `{cmd[:80]}` 가 범위 밖 파일 {len(outside)}곳에 이미 적중({sorted(outside)[0]} 등) — 패턴을 좁혀야 함"]


def missing_file(cmd: str, output: str) -> str:
    """missing_target 일 때 개발자가 만들어야 할 테스트 파일 경로(repo 기준). 못 찾으면 빈 문자열."""
    m = _TESTFILE.search(cmd)
    if not m:
        return ""
    return f"frontend/{m.group(1)}" if "cd frontend" in cmd and not m.group(1).startswith("frontend/") else m.group(1)


STOP_NOTE = {
    "missing_target": "verify 의 테스트 파일이 없다 — 범위에 추가해 재시도했으나 반복",
    "usage": "verify 명령 인자·호출 방식 오류가 반복 — 코드가 아닌 verify 수정 필요",
    "absence_hit": "부재 검사(`! grep`·`test $(grep …) -eq 0`)가 계속 적중 — scope 부족이거나 패턴이 과도하게 넓은지 확인",
    "real": "테스트 실패가 해소되지 않음",
}

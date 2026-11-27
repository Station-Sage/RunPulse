"""verify 진단·사전 점검 — 실패 원인을 종류별로 가르고, 실행 불가능한 verify 를 큐 진입 전에 잡는다.

diagnose: missing_target(대상 파일 없음)|usage(인자·모듈 오류)|absence_hit(`! grep` 부재 검사 적중)|real(실제 테스트 실패)|env.
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


def diagnose(cmd: str, rc: int | None, output: str) -> str:
    """verify 실패 → env|missing_target|usage|absence_hit|real."""
    if rc == 127 or any(m in output for m in _ENV):
        return "env"
    if any(m in output for m in _MISSING):
        return "missing_target"
    if any(m in output for m in _USAGE):
        return "usage"
    if is_negative_grep(cmd) and rc == 1:
        return "absence_hit"
    return "real"


def tag_reason(kind: str, output: str, limit: int = 2500) -> str:
    return f"[{kind}] {output[:limit]}"


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
    "absence_hit": "`! grep` 부재 검사가 계속 적중 — 패턴이 과도하게 넓은지 확인",
    "real": "테스트 실패가 해소되지 않음",
}

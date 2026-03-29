#!/usr/bin/env python3
"""문서 정합성 검증 스크립트.

검사 항목:
1. BACKLOG.md NOW 항목 수 (3개 이하)
2. 각 GUIDE.md 파일맵 vs 실제 파일 불일치
3. 300줄 초과 파일 목록
4. pytest 수집 수 출력
"""
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GUIDE_DIRS = ["src/web", "src/metrics", "src/sync", "src/ai", "src/training"]
MAX_LINES = 300
errors = 0


def section(title: str) -> None:
    print(f"\n{'='*60}\n  {title}\n{'='*60}")


# ── 1. BACKLOG.md NOW 항목 수 ──────────────────────────────
section("1. BACKLOG.md NOW 항목 수")
backlog = ROOT / "BACKLOG.md"
if not backlog.exists():
    print("  [ERROR] BACKLOG.md 없음")
    errors += 1
else:
    text = backlog.read_text(encoding="utf-8")
    # NOW 섹션 내 "- [ ]" 항목 수 세기
    now_match = re.search(r"## NOW.*?\n(.*?)(?=\n## |\Z)", text, re.DOTALL)
    if now_match:
        now_items = re.findall(r"^- \[ \]", now_match.group(1), re.MULTILINE)
        count = len(now_items)
        status = "OK" if count <= 3 else "WARN"
        symbol = "[OK]" if count <= 3 else "[WARN]"
        print(f"  {symbol} NOW 항목: {count}개 (최대 3개)")
        if count > 3:
            errors += 1
    else:
        print("  [WARN] NOW 섹션을 찾을 수 없음")


# ── 2. GUIDE.md 파일맵 vs 실제 파일 ──────────────────────
section("2. GUIDE.md 파일맵 정합성")
for guide_dir in GUIDE_DIRS:
    guide_path = ROOT / guide_dir / "GUIDE.md"
    if not guide_path.exists():
        print(f"  [ERROR] {guide_dir}/GUIDE.md 없음")
        errors += 1
        continue

    guide_text = guide_path.read_text(encoding="utf-8")
    # 파일맵에서 .py 파일명 추출 (backtick으로 감싸진 패턴)
    documented = set()
    for m in re.finditer(r"`([a-zA-Z_][a-zA-Z0-9_]*\.py)`", guide_text):
        documented.add(m.group(1))

    # 실제 .py 파일 (테스트 제외, __init__.py 제외)
    actual_dir = ROOT / guide_dir
    actual = set()
    for f in actual_dir.iterdir():
        if f.suffix == ".py" and f.name != "__init__.py":
            actual.add(f.name)

    missing_doc = actual - documented
    missing_file = documented - actual

    if missing_doc or missing_file:
        print(f"  [{guide_dir}]")
        if missing_doc:
            print(f"    파일 존재하나 GUIDE.md에 미등록: {sorted(missing_doc)}")
            errors += 1
        if missing_file:
            print(f"    GUIDE.md에 등록되었으나 파일 없음: {sorted(missing_file)}")
            errors += 1
    else:
        print(f"  [OK] {guide_dir}/GUIDE.md — 정합")


# ── 3. 300줄 초과 파일 ────────────────────────────────────
section("3. 300줄 초과 .py 파일")
over_limit = []
src_dir = ROOT / "src"
for py_file in sorted(src_dir.rglob("*.py")):
    if py_file.name == "__init__.py":
        continue
    try:
        line_count = len(py_file.read_text(encoding="utf-8").splitlines())
        if line_count > MAX_LINES:
            rel = py_file.relative_to(ROOT)
            over_limit.append((str(rel), line_count))
    except Exception:
        pass

if over_limit:
    for path, count in over_limit:
        print(f"  [WARN] {path}: {count}줄")
    print(f"  총 {len(over_limit)}개 파일이 {MAX_LINES}줄 초과")
else:
    print(f"  [OK] 모든 파일이 {MAX_LINES}줄 이하")


# ── 4. pytest 수집 수 ─────────────────────────────────────
section("4. pytest 테스트 수집")
try:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "tests/"],
        capture_output=True, text=True, cwd=str(ROOT), timeout=60
    )
    # 마지막 줄에서 숫자 추출
    lines = result.stdout.strip().splitlines()
    if lines:
        last = lines[-1]
        match = re.search(r"(\d+)\s+test", last)
        if match:
            print(f"  [INFO] 수집된 테스트: {match.group(1)}개")
        else:
            print(f"  [INFO] {last}")
    if result.returncode != 0 and result.stderr:
        err_lines = result.stderr.strip().splitlines()[:5]
        for line in err_lines:
            print(f"  [WARN] {line}")
except subprocess.TimeoutExpired:
    print("  [WARN] pytest 수집 타임아웃 (60초)")
except FileNotFoundError:
    print("  [WARN] pytest 미설치")


# ── 결과 요약 ─────────────────────────────────────────────
section("결과 요약")
if errors == 0:
    print("  [PASS] 모든 검사 통과")
else:
    print(f"  [FAIL] {errors}개 문제 발견")
sys.exit(1 if errors else 0)

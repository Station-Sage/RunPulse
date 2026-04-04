#!/usr/bin/env python3
"""문서 정합성 검증 스크립트 (v0.3 확장판).

검사 항목:
1. BACKLOG.md NOW 항목 수 (3개 이하)
2. 각 GUIDE.md 파일맵 vs 실제 파일 불일치
3. 300줄 초과 파일 목록
4. pytest 수집 수 출력
5. [신규] metric_dictionary.md 동기화 검증
6. [신규] ALL_CALCULATORS 수 vs 문서 기재 수 비교
7. [신규] SEMANTIC_GROUPS 수 vs 문서 기재 수 비교
8. [신규] 테스트 파일 수 vs files_index.md 비교
9. [신규] "13개 테이블" 같은 outdated 표현 스캔
"""
# === 검사 추가 방법 ===
# 1. 이 파일에 check_ 로 시작하는 함수를 추가
# 2. 함수 내에서 error("msg") 또는 warn("msg") 호출
# 3. main() 하단의 검사 호출 목록에 함수 등록
# === 검사 15개 초과 시 scripts/checks/ 디렉토리로 플러그인 구조 분리 검토 ===
import os
import re
import subprocess
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

GUIDE_DIRS = ["src/web", "src/metrics", "src/sync", "src/ai", "src/training"]
MAX_LINES = 300
errors = 0
warnings = 0


def section(title: str) -> None:
    print(f"\n{'='*60}\n  {title}\n{'='*60}")


def error(msg: str) -> None:
    global errors
    print(f"  [ERROR] {msg}")
    errors += 1


def warn(msg: str) -> None:
    global warnings
    print(f"  [WARN] {msg}")
    warnings += 1


def ok(msg: str) -> None:
    print(f"  [OK] {msg}")


# ── 1. BACKLOG.md NOW 항목 수 ──
section("1. BACKLOG.md NOW 항목 수")
backlog = ROOT / "BACKLOG.md"
if not backlog.exists():
    warn("BACKLOG.md 없음 (선택 사항)")
else:
    text = backlog.read_text(encoding="utf-8")
    now_match = re.search(r"## NOW.*?\n(.*?)(?=\n## |\Z)", text, re.DOTALL)
    if now_match:
        now_items = re.findall(r"^- \[ \]", now_match.group(1), re.MULTILINE)
        count = len(now_items)
        if count <= 3:
            ok(f"NOW 항목: {count}개 (최대 3개)")
        else:
            warn(f"NOW 항목: {count}개 (최대 3개 권장)")
    else:
        ok("NOW 섹션 없음 (정상)")


# ── 2. GUIDE.md 파일맵 vs 실제 파일 ──
section("2. GUIDE.md 파일맵 정합성")
for guide_dir in GUIDE_DIRS:
    guide_path = ROOT / guide_dir / "GUIDE.md"
    if not guide_path.exists():
        warn(f"{guide_dir}/GUIDE.md 없음")
        continue

    guide_text = guide_path.read_text(encoding="utf-8")
    documented = set()
    for m in re.finditer(r"`([a-zA-Z_][a-zA-Z0-9_]*\.py)`", guide_text):
        documented.add(m.group(1))

    actual_dir = ROOT / guide_dir
    actual = set()
    if actual_dir.exists():
        for f in actual_dir.iterdir():
            if f.suffix == ".py" and f.name != "__init__.py":
                actual.add(f.name)

    missing_doc = actual - documented
    missing_file = documented - actual

    if missing_doc or missing_file:
        if missing_doc:
            error(f"{guide_dir}: 파일 존재하나 GUIDE.md에 미등록: {sorted(missing_doc)}")
        if missing_file:
            warn(f"{guide_dir}: GUIDE.md에 등록되었으나 파일 없음: {sorted(missing_file)}")
    else:
        ok(f"{guide_dir}/GUIDE.md — 정합")


# ── 3. 300줄 초과 파일 ──
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
        warn(f"{path}: {count}줄")
    print(f"  총 {len(over_limit)}개 파일이 {MAX_LINES}줄 초과")
else:
    ok(f"모든 파일이 {MAX_LINES}줄 이하")


# ── 4. pytest 수집 수 ──
section("4. pytest 테스트 수집")
collected_tests = 0
try:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "tests/"],
        capture_output=True, text=True, cwd=str(ROOT), timeout=60
    )
    lines_out = result.stdout.strip().splitlines()
    if lines_out:
        last = lines_out[-1]
        match = re.search(r"(\d+)\s+test", last)
        if match:
            collected_tests = int(match.group(1))
            ok(f"수집된 테스트: {collected_tests}개")
        else:
            print(f"  [INFO] {last}")
except subprocess.TimeoutExpired:
    warn("pytest 수집 타임아웃 (60초)")
except FileNotFoundError:
    warn("pytest 미설치")


# ── 5. metric_dictionary.md 동기화 검증 ──
section("5. metric_dictionary.md 동기화")
try:
    from scripts.gen_metric_dictionary import get_structural_fingerprint

    fp = get_structural_fingerprint()

    dict_path = ROOT / "v0.3" / "data" / "metric_dictionary.md"
    if not dict_path.exists():
        error("metric_dictionary.md 없음 — python scripts/gen_metric_dictionary.py 실행 필요")
    else:
        dict_text = dict_path.read_text(encoding="utf-8")

        # calculator 수 확인
        calc_match = re.search(r"(\d+) calculators", dict_text)
        if calc_match:
            doc_calc = int(calc_match.group(1))
            if doc_calc != fp["calculator_count"]:
                error(f"metric_dictionary.md calculator 수 불일치: 문서={doc_calc}, 코드={fp['calculator_count']}")
            else:
                ok(f"Calculator 수 일치: {doc_calc}")
        else:
            error("metric_dictionary.md에서 calculator 수를 찾을 수 없음")

        # group 수 확인
        group_match = re.search(r"(\d+) semantic groups", dict_text)
        if group_match:
            doc_groups = int(group_match.group(1))
            if doc_groups != fp["group_count"]:
                error(f"metric_dictionary.md group 수 불일치: 문서={doc_groups}, 코드={fp['group_count']}")
            else:
                ok(f"Semantic group 수 일치: {doc_groups}")

        # 각 calculator가 문서에 있는지 확인
        missing_calcs = []
        for name in fp["calculator_names"]:
            if name not in dict_text:
                missing_calcs.append(name)
        if missing_calcs:
            error(f"metric_dictionary.md에 누락된 calculator: {missing_calcs}")
        else:
            ok(f"모든 calculator ({fp['calculator_count']}개) 문서에 포함")

except ImportError:
    warn("gen_metric_dictionary.py import 실패 — 검증 건너뜀")


# ── 6. 주요 문서의 calculator 수 일치 ──
section("6. 문서 간 calculator 수 일치")
try:
    from src.metrics.engine import ALL_CALCULATORS
    code_calc_count = len(ALL_CALCULATORS)

    doc_files = {
        "GUIDE.md": ROOT / "src" / "metrics" / "GUIDE.md",
        "files_index.md": ROOT / "v0.3" / "data" / "files_index.md",
        "phase_summary.md": ROOT / "v0.3" / "data" / "phase_summary.md",
    }

    for doc_name, doc_path in doc_files.items():
        if not doc_path.exists():
            continue
        text = doc_path.read_text(encoding="utf-8")
        matches = re.findall(r"(?<![A-Za-z])(\d+)개\s*calculator", text)
        if not matches:
            matches = re.findall(r"(?<![A-Za-z])(\d+)\s+calculators?", text, re.IGNORECASE)
        for m in matches:
            doc_num = int(m)
            if doc_num != code_calc_count:
                error(f"{doc_name}: calculator 수 불일치 (문서={doc_num}, 코드={code_calc_count})")
                break
        else:
            if matches:
                ok(f"{doc_name}: calculator 수 일치 ({code_calc_count})")
except ImportError:
    warn("ALL_CALCULATORS import 실패")


# ── 7. SEMANTIC_GROUPS 수 일치 ──
section("7. Semantic groups 수 일치")
try:
    from src.utils.metric_groups import SEMANTIC_GROUPS
    code_group_count = len(SEMANTIC_GROUPS)

    for doc_name, doc_path in doc_files.items():
        if not doc_path.exists():
            continue
        text = doc_path.read_text(encoding="utf-8")
        matches = re.findall(r"(\d+)개?\s*(?:시맨틱\s*)?(?:그룹|semantic\s*group|group)", text, re.IGNORECASE)
        for m in matches:
            doc_num = int(m)
            if doc_num != code_group_count:
                error(f"{doc_name}: semantic group 수 불일치 (문서={doc_num}, 코드={code_group_count})")
                break
        else:
            if matches:
                ok(f"{doc_name}: group 수 일치 ({code_group_count})")
except ImportError:
    warn("SEMANTIC_GROUPS import 실패")


# ── 8. 테스트 파일 수 검증 ──
section("8. 테스트 파일 수 검증")
actual_test_files = len(list((ROOT / "tests").glob("test_*.py")))
files_index = ROOT / "v0.3" / "data" / "files_index.md"
if files_index.exists():
    text = files_index.read_text(encoding="utf-8")
    match = re.search(r"(\d+)\s*test\s*files?", text, re.IGNORECASE)
    if match:
        doc_test_files = int(match.group(1))
        if doc_test_files != actual_test_files:
            warn(f"files_index.md 테스트 파일 수: 문서={doc_test_files}, 실제={actual_test_files}")
        else:
            ok(f"테스트 파일 수 일치: {actual_test_files}")
else:
    ok(f"실제 테스트 파일: {actual_test_files}개")


# ── 9. outdated 표현 스캔 ──
section("9. Outdated 표현 스캔")
outdated_patterns = [
    (r"13개 테이블", "12개 파이프라인 + 5개 앱 테이블"),
    (r"computed_metrics", "metric_store"),
    (r"(?<!raw_)(?<!credential_)store\.py", "metric_store (base.py)"),
]
scan_dirs = [ROOT / "v0.3" / "data", ROOT / "src" / "metrics"]
found_outdated = False
for scan_dir in scan_dirs:
    if not scan_dir.exists():
        continue
    for md_file in scan_dir.glob("*.md"):
        text = md_file.read_text(encoding="utf-8")
        for pattern, replacement in outdated_patterns:
            for m in re.finditer(pattern, text):
                line_start = text.rfind('\n', 0, m.start()) + 1
                line_end = text.find('\n', m.end())
                if line_end < 0:
                    line_end = len(text)
                line_text = text[line_start:line_end]
                # 변경 이력/비교 문맥은 무시
                if any(skip in line_text for skip in ['→', '흡수', '잔존', '변경', '기존:', '기존 ']):
                    continue
                rel = md_file.relative_to(ROOT)
                line_num = text[:m.start()].count('\n') + 1
                warn(f"{rel}:{line_num} — \'{pattern}\' 발견 (→ {replacement})")
                found_outdated = True
if not found_outdated:
    ok("outdated 표현 없음")


# ── 결과 요약 ──
section("결과 요약")
print(f"  Errors: {errors}")
print(f"  Warnings: {warnings}")
if errors == 0:
    print("  [PASS] 모든 필수 검사 통과")
else:
    print(f"  [FAIL] {errors}개 필수 문제 발견")
if warnings > 0:
    print(f"  [INFO] {warnings}개 경고 (권장 수정)")
sys.exit(1 if errors else 0)

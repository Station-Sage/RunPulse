#!/usr/bin/env python3
"""문서 정합성 검증 스크립트 (v0.3 Phase 5 확장판).

검사 항목:
 1. BACKLOG.md NOW 항목 수 (3개 이하)                    [general]
 2. files_index.md 동기화 검증                            [code]
 3. 300줄 초과 파일 목록                                  [code]
 4. pytest 수집 수 출력                                   [code]
 5. metric_dictionary.md 동기화 검증                      [metric]
 6. ALL_CALCULATORS 수 vs 문서 기재 수 비교               [metric]
 7. SEMANTIC_GROUPS 수 vs 문서 기재 수 비교               [metric]
 8. 테스트 파일 수 vs files_index.md 비교                 [code]
 9. Outdated 표현 스캔                                    [general]
10. (삭제됨) phase_summary.md → architecture.md 대체     [phase]
11. architecture.md DDL vs db_setup.py DDL 컬럼 수        [schema]
12. 카테고리 삼중 정합성 (calculator vs registry vs dict)  [metric]
13. 서비스 레이어 의존 함수 존재 검증                      [phase]
14. 설계서 숫자 표현 일치 (테이블 수, 컬럼 수)            [schema]
15. docstring 누락 검사                                   [code]
16. Phase 2 Extractor 파일 존재 & 인터페이스 검증          [phase]
17. Phase 3 Sync 핵심 파일 존재 검증                      [phase]
18. Phase 4 Metrics Engine 파일 존재 & 인터페이스 검증    [phase]
19. Phase 5 서비스 레이어 파일 존재 검증                  [phase]

사용법:
  python3 scripts/check_docs.py              # 전체 실행
  python3 scripts/check_docs.py --tag metric  # metric 관련만
  python3 scripts/check_docs.py --tag schema  # 스키마 관련만
  python3 scripts/check_docs.py --tag phase   # Phase 문서 관련만
  python3 scripts/check_docs.py --tag code    # 코드 규칙만
  python3 scripts/check_docs.py --list        # 검사 목록 출력
"""
import argparse
import ast
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

SCAN_DIRS = [
    "src/services", "src/metrics", "src/sync", "src/sync/extractors",
    "src/ai", "src/web", "src/training", "src/utils",
]
MAX_LINES = 300
errors = 0
warnings = 0

_checks: list[tuple[str, list[str], Callable]] = []


def check(title: str, tags: list[str]):
    def decorator(fn: Callable):
        _checks.append((title, tags, fn))
        return fn
    return decorator


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


def _parse_columns_from_ddl(ddl_text: str, table_name: str) -> list[str]:
    pattern = rf"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?{table_name}\s*\((.*?)\);"
    m = re.search(pattern, ddl_text, re.DOTALL | re.IGNORECASE)
    if not m:
        return []
    body = m.group(1)
    cols = []
    for line in body.split("\n"):
        line = line.strip().rstrip(",")
        if not line:
            continue
        if re.match(r"^(UNIQUE|FOREIGN|CHECK|CONSTRAINT)\b", line, re.IGNORECASE):
            continue
        col_match = re.match(r"^(\w+)\s+", line)
        if col_match:
            cols.append(col_match.group(1))
    return cols


def _get_docstring(filepath: Path) -> str:
    try:
        tree = ast.parse(filepath.read_text(encoding="utf-8"))
        ds = ast.get_docstring(tree)
        return ds.strip() if ds else ""
    except (SyntaxError, UnicodeDecodeError):
        return ""


# ════════════════════════════════════════
#  1. BACKLOG.md NOW 항목 수
# ════════════════════════════════════════
@check("1. BACKLOG.md NOW 항목 수", ["general"])
def check_backlog():
    backlog = ROOT / "BACKLOG.md"
    if not backlog.exists():
        warn("BACKLOG.md 없음 (선택 사항)")
        return
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


# ════════════════════════════════════════
#  2. files_index.md 동기화 검증
# ════════════════════════════════════════
@check("2. files_index.md 동기화", ["code"])
def check_files_index():
    index_path = ROOT / "v0.3" / "data" / "files_index.md"
    if not index_path.exists():
        error("files_index.md 없음 — python3 scripts/gen_files_index.py 실행 필요")
        return

    text = index_path.read_text(encoding="utf-8")

    # files_index.md에 등록된 파일명 추출
    documented = set()
    for m in re.finditer(r"### `([a-zA-Z_][a-zA-Z0-9_]*\.py)`", text):
        documented.add(m.group(1))

    # 실제 파일 — SCAN_DIRS + tests + scripts 전부 포함
    all_dirs = SCAN_DIRS + ["tests", "scripts"]
    actual = set()
    for dir_key in all_dirs:
        dir_path = ROOT / dir_key
        if not dir_path.exists():
            continue
        for f in dir_path.iterdir():
            if f.suffix == ".py" and f.name != "__init__.py":
                actual.add(f.name)

    missing_in_doc = actual - documented
    missing_on_disk = documented - actual

    if missing_in_doc:
        for p in sorted(missing_in_doc):
            error(f"파일 존재하나 files_index.md에 미등록: {p}")
    if missing_on_disk:
        for p in sorted(missing_on_disk):
            warn(f"files_index.md에 등록되었으나 파일 없음: {p}")
    if not missing_in_doc and not missing_on_disk:
        ok(f"files_index.md 정합 ({len(documented)}개 파일)")



# ════════════════════════════════════════
#  3. 300줄 초과 파일
# ════════════════════════════════════════
@check("3. 300줄 초과 .py 파일", ["code"])
def check_line_count():
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


# ════════════════════════════════════════
#  4. pytest 수집 수
# ════════════════════════════════════════
@check("4. pytest 테스트 수집", ["code"])
def check_pytest_collect():
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
                ok(f"수집된 테스트: {match.group(1)}개")
            else:
                print(f"  [INFO] {last}")
    except subprocess.TimeoutExpired:
        warn("pytest 수집 타임아웃 (60초)")
    except FileNotFoundError:
        warn("pytest 미설치")


# ════════════════════════════════════════
#  5. metric_dictionary.md 동기화
# ════════════════════════════════════════
@check("5. metric_dictionary.md 동기화", ["metric"])
def check_metric_dictionary():
    try:
        from scripts.gen_metric_dictionary import get_structural_fingerprint
        fp = get_structural_fingerprint()
    except ImportError:
        warn("gen_metric_dictionary.py import 실패 — 검증 건너뜀")
        return

    dict_path = ROOT / "v0.3" / "data" / "metric_dictionary.md"
    if not dict_path.exists():
        error("metric_dictionary.md 없음 — python3 scripts/gen_metric_dictionary.py 실행 필요")
        return

    dict_text = dict_path.read_text(encoding="utf-8")

    calc_match = re.search(r"(\d+) calculators", dict_text)
    if calc_match:
        doc_calc = int(calc_match.group(1))
        if doc_calc != fp["calculator_count"]:
            error(f"calculator 수 불일치: 문서={doc_calc}, 코드={fp['calculator_count']}")
        else:
            ok(f"Calculator 수 일치: {doc_calc}")

    group_match = re.search(r"(\d+) semantic groups", dict_text)
    if group_match:
        doc_groups = int(group_match.group(1))
        if doc_groups != fp["group_count"]:
            error(f"group 수 불일치: 문서={doc_groups}, 코드={fp['group_count']}")
        else:
            ok(f"Semantic group 수 일치: {doc_groups}")

    missing_calcs = [n for n in fp["calculator_names"] if n not in dict_text]
    if missing_calcs:
        error(f"dictionary에 누락된 calculator: {missing_calcs}")
    else:
        ok(f"모든 calculator ({fp['calculator_count']}개) 문서에 포함")


# ════════════════════════════════════════
#  6. 문서 간 calculator 수 일치
# ════════════════════════════════════════
@check("6. 문서 간 calculator 수 일치", ["metric"])
def check_calculator_count():
    try:
        from src.metrics.engine import ALL_CALCULATORS
        code_count = len(ALL_CALCULATORS)
    except ImportError:
        warn("ALL_CALCULATORS import 실패")
        return

    doc_files = {
        "files_index.md": ROOT / "v0.3" / "data" / "files_index.md",
        "architecture.md": ROOT / "v0.3" / "data" / "architecture.md",
    }
    for doc_name, doc_path in doc_files.items():
        if not doc_path.exists():
            continue
        text = doc_path.read_text(encoding="utf-8")
        matches = re.findall(r"(?<![A-Za-z])(\d+)개?\s*calculator", text, re.IGNORECASE)
        if not matches:
            matches = re.findall(r"(?<![A-Za-z])(\d+)\s+calculators?", text, re.IGNORECASE)
        for m in matches:
            doc_num = int(m)
            if doc_num != code_count:
                error(f"{doc_name}: calculator 수 불일치 (문서={doc_num}, 코드={code_count})")
                break
        else:
            if matches:
                ok(f"{doc_name}: calculator 수 일치 ({code_count})")


# ════════════════════════════════════════
#  7. SEMANTIC_GROUPS 수 일치
# ════════════════════════════════════════
@check("7. Semantic groups 수 일치", ["metric"])
def check_semantic_groups():
    try:
        from src.utils.metric_groups import SEMANTIC_GROUPS
        code_count = len(SEMANTIC_GROUPS)
    except ImportError:
        warn("SEMANTIC_GROUPS import 실패")
        return

    doc_files = {
        "files_index.md": ROOT / "v0.3" / "data" / "files_index.md",
        "architecture.md": ROOT / "v0.3" / "data" / "architecture.md",
    }
    for doc_name, doc_path in doc_files.items():
        if not doc_path.exists():
            continue
        text = doc_path.read_text(encoding="utf-8")
        matches = re.findall(
            r"(\d+)개?\s*(?:시맨틱\s*)?(?:그룹|semantic\s*group|group)",
            text, re.IGNORECASE,
        )
        for m in matches:
            doc_num = int(m)
            if doc_num != code_count:
                error(f"{doc_name}: semantic group 수 불일치 (문서={doc_num}, 코드={code_count})")
                break
        else:
            if matches:
                ok(f"{doc_name}: group 수 일치 ({code_count})")


# ════════════════════════════════════════
#  8. 테스트 파일 수
# ════════════════════════════════════════
@check("8. 테스트 파일 수 검증", ["code"])
def check_test_file_count():
    actual = len(list((ROOT / "tests").glob("test_*.py")))
    files_index = ROOT / "v0.3" / "data" / "files_index.md"
    if files_index.exists():
        text = files_index.read_text(encoding="utf-8")
        # files_index.md의 tests/ 섹션에서 파일 수 세기
        in_tests = False
        doc_count = 0
        for line in text.split("\n"):
            if line.startswith("## `tests/`"):
                in_tests = True
                continue
            if in_tests and line.startswith("## "):
                break
            if in_tests and line.startswith("### `test_"):
                doc_count += 1
        if doc_count > 0 and doc_count != actual:
            warn(f"files_index.md 테스트 파일 수: 문서={doc_count}, 실제={actual}")
        elif doc_count > 0:
            ok(f"테스트 파일 수 일치: {actual}")
        else:
            ok(f"실제 테스트 파일: {actual}개")
    else:
        ok(f"실제 테스트 파일: {actual}개")


# ════════════════════════════════════════
#  9. Outdated 표현 스캔
# ════════════════════════════════════════
@check("9. Outdated 표현 스캔", ["general"])
def check_outdated():
    outdated_patterns = [
        (r"12개 파이프라인", "11개 파이프라인 + 5개 앱 = 16개 테이블"),
        (r"13개 테이블", "11개 파이프라인 + 5개 앱 = 16개 테이블"),
        (r"44컬럼|44개 컬럼|44 col", "38컬럼 (id 포함)"),
        (r"computed_metrics", "metric_store"),
        (r"darp_5k(?!.*alias)", "race_pred_5k"),
        (r"GUIDE\.md", "files_index.md + docstring"),
    ]
    scan_dirs = [ROOT / "v0.3" / "data", ROOT / "src" / "metrics"]
    found = False
    for scan_dir in scan_dirs:
        if not scan_dir.exists():
            continue
        for md_file in scan_dir.glob("*.md"):
            # files_index.md는 자동 생성이라 건너뛰기
            if md_file.name == "files_index.md":
                continue
            text = md_file.read_text(encoding="utf-8")
            for pattern, replacement in outdated_patterns:
                for m in re.finditer(pattern, text):
                    line_start = text.rfind("\n", 0, m.start()) + 1
                    line_end = text.find("\n", m.end())
                    if line_end < 0:
                        line_end = len(text)
                    line_text = text[line_start:line_end]
                    if any(skip in line_text for skip in
                           ["→", "흡수", "잔존", "변경", "기존:", "기존 ", "aliases", "canonicalize",
                            "자동 생성", "수동 편집 금지", "삭제"]):
                        continue
                    rel = md_file.relative_to(ROOT)
                    line_num = text[:m.start()].count("\n") + 1
                    warn(f"{rel}:{line_num} — '{pattern}' 발견 (→ {replacement})")
                    found = True
    if not found:
        ok("outdated 표현 없음")


# ════════════════════════════════════════
#  10. phase_summary.md 소스 파일 목록 vs 실제
# ════════════════════════════════════════
@check("10. phase_summary.md 파일 목록 정합성", ["phase"])
def check_phase_summary_files():
    # phase_summary.md 삭제됨 (2026-04-05). architecture.md + phase-N.md로 대체.
    ok("phase_summary.md 삭제됨 — architecture.md + phase-N.md로 대체")


# ════════════════════════════════════════
#  11. architecture.md DDL vs db_setup.py DDL 컬럼 수
# ════════════════════════════════════════
@check("11. 스키마 DDL 컬럼 수 정합성", ["schema"])
def check_schema_columns():
    arch_path = ROOT / "v0.3" / "data" / "architecture.md"
    phase1_path = ROOT / "v0.3" / "data" / "phase-1.md"
    setup_path = ROOT / "src" / "db_setup.py"

    if not setup_path.exists():
        warn("db_setup.py 없음")
        return

    setup_text = setup_path.read_text(encoding="utf-8")

    doc_sources = {}
    if arch_path.exists():
        doc_sources["architecture.md"] = arch_path.read_text(encoding="utf-8")
    if phase1_path.exists():
        doc_sources["phase-1.md"] = phase1_path.read_text(encoding="utf-8")

    if not doc_sources:
        warn("architecture.md, phase-1.md 모두 없음")
        return

    for table in ["activity_summaries", "daily_wellness", "daily_fitness", "metric_store"]:
        setup_cols = _parse_columns_from_ddl(setup_text, table)
        if not setup_cols:
            warn(f"db_setup.py에서 {table} DDL을 찾을 수 없음")
            continue

        for doc_name, doc_text in doc_sources.items():
            doc_cols = _parse_columns_from_ddl(doc_text, table)
            if not doc_cols:
                continue

            if len(doc_cols) != len(setup_cols):
                doc_set, setup_set = set(doc_cols), set(setup_cols)
                only_doc = doc_set - setup_set
                only_setup = setup_set - doc_set
                error(f"{table} 컬럼 수 불일치: {doc_name}={len(doc_cols)}, db_setup.py={len(setup_cols)}")
                if only_doc:
                    print(f"    {doc_name}에만 있음: {sorted(only_doc)}")
                if only_setup:
                    print(f"    db_setup.py에만 있음: {sorted(only_setup)}")
            else:
                doc_set, setup_set = set(doc_cols), set(setup_cols)
                if doc_set != setup_set:
                    diff = doc_set.symmetric_difference(setup_set)
                    error(f"{table} 컬럼명 불일치 ({doc_name}): {sorted(diff)}")
                else:
                    ok(f"{table}: {doc_name} vs db_setup.py 일치 ({len(doc_cols)}개)")


# ════════════════════════════════════════
#  12. 카테고리 삼중 정합성
# ════════════════════════════════════════
@check("12. 카테고리 삼중 정합성", ["metric"])
def check_category_triple():
    calc_categories = {}
    try:
        from src.metrics.engine import ALL_CALCULATORS
        for calc in ALL_CALCULATORS:
            name = getattr(calc, "name", None)
            cat = getattr(calc, "category", None)
            if name and cat:
                calc_categories[name] = cat
                produces = getattr(calc, "produces", None)
                if produces:
                    for p in produces:
                        if isinstance(p, str):
                            calc_categories[p] = cat
    except ImportError:
        warn("ALL_CALCULATORS import 실패")
        return

    reg_categories = {}
    try:
        from src.utils.metric_registry import METRIC_REGISTRY
        for name, md in METRIC_REGISTRY.items():
            reg_categories[name] = md.category
    except ImportError:
        warn("METRIC_REGISTRY import 실패")

    dict_categories = {}
    dict_path = ROOT / "v0.3" / "data" / "metric_dictionary.md"
    if dict_path.exists():
        text = dict_path.read_text(encoding="utf-8")
        current_metric = None
        for line in text.split("\n"):
            name_match = re.match(r"^[-*]+\s*\*\*(\w+)\*\*", line)
            if name_match:
                current_metric = name_match.group(1)
            cat_match = re.search(r"\|\s*카테고리\s*\|\s*`(\w+)`", line)
            if cat_match and current_metric:
                dict_categories[current_metric] = cat_match.group(1)

    mismatches = []
    for name, calc_cat in sorted(calc_categories.items()):
        reg_cat = reg_categories.get(name)
        dict_cat = dict_categories.get(name)
        issues = []
        if reg_cat and reg_cat != calc_cat:
            issues.append(f"registry={reg_cat}")
        if dict_cat and dict_cat != calc_cat:
            issues.append(f"dictionary={dict_cat}")
        if issues:
            mismatches.append(f"{name}: calculator={calc_cat}, {', '.join(issues)}")

    if mismatches:
        for m in mismatches:
            error(f"카테고리 불일치 — {m}")
    else:
        ok(f"카테고리 삼중 정합: {len(calc_categories)}개 메트릭 일치")


# ════════════════════════════════════════
#  13. db_helpers 의존 함수 존재 검증
# ════════════════════════════════════════
@check("13. db_helpers 의존 함수 존재 검증", ["phase"])
def check_db_helpers_functions():
    required_db_helpers = [
        "upsert_activity", "upsert_metric", "upsert_metrics_batch",
        "get_primary_metric", "get_primary_metrics", "get_all_providers",
        "get_metrics_by_category", "get_metric_history",
        "upsert_daily_wellness", "upsert_daily_fitness",
    ]
    required_metric_priority = [
        "resolve_primary", "resolve_for_scope", "resolve_all_primaries",
    ]

    helpers_path = ROOT / "src" / "utils" / "db_helpers.py"
    if not helpers_path.exists():
        error("src/utils/db_helpers.py 없음")
        return
    text = helpers_path.read_text(encoding="utf-8")
    defined = set(re.findall(r"^def (\w+)", text, re.MULTILINE))
    missing = [f for f in required_db_helpers if f not in defined]
    if missing:
        for f in missing:
            error(f"db_helpers.py에 {f}() 없음")
    else:
        ok(f"db_helpers.py 필수 함수 {len(required_db_helpers)}개 전부 존재")

    priority_path = ROOT / "src" / "utils" / "metric_priority.py"
    if not priority_path.exists():
        error("src/utils/metric_priority.py 없음")
        return
    text2 = priority_path.read_text(encoding="utf-8")
    defined2 = set(re.findall(r"^def (\w+)", text2, re.MULTILINE))
    missing2 = [f for f in required_metric_priority if f not in defined2]
    if missing2:
        for f in missing2:
            error(f"metric_priority.py에 {f}() 없음")
    else:
        ok(f"metric_priority.py 필수 함수 {len(required_metric_priority)}개 전부 존재")



# ════════════════════════════════════════
#  14. 설계서 숫자 표현 일치
# ════════════════════════════════════════
@check("14. 설계서 숫자 표현 일치", ["schema"])
def check_doc_numbers():
    setup_path = ROOT / "src" / "db_setup.py"
    if not setup_path.exists():
        warn("db_setup.py 없음")
        return

    setup_text = setup_path.read_text(encoding="utf-8")
    actual_counts = {}
    for table in ["activity_summaries", "daily_wellness", "daily_fitness", "metric_store"]:
        cols = _parse_columns_from_ddl(setup_text, table)
        if cols:
            actual_counts[table] = len(cols)

    doc_paths = [
        ROOT / "v0.3" / "data" / "architecture.md",
        ROOT / "v0.3" / "data" / "phase-1.md",
    ]

    for doc_path in doc_paths:
        if not doc_path.exists():
            continue
        text = doc_path.read_text(encoding="utf-8")
        rel = doc_path.relative_to(ROOT)

        for table, actual in actual_counts.items():
            patterns = [
                rf"{table}\s*[\(（]\s*(\d+)\s*(?:컬럼|cols?|columns?)",
                rf"{table}.*?(\d+)\s*(?:컬럼|cols?|columns?)",
            ]
            for pat in patterns:
                for m in re.finditer(pat, text, re.IGNORECASE):
                    doc_num = int(m.group(1))
                    if doc_num != actual:
                        line_num = text[:m.start()].count("\n") + 1
                        error(f"{rel}:{line_num} — {table} 컬럼 수: 문서={doc_num}, 코드={actual}")
                    break

    if not actual_counts:
        warn("db_setup.py에서 DDL 파싱 실패")
    else:
        ok(f"숫자 표현 검사 완료 (테이블 {len(actual_counts)}개)")


# ════════════════════════════════════════
#  15. docstring 누락 검사
# ════════════════════════════════════════
@check("15. docstring 누락 검사", ["code"])
def check_docstrings():
    missing = []

    for dir_key in SCAN_DIRS:
        dir_path = ROOT / dir_key
        if not dir_path.exists():
            continue

        # __init__.py docstring
        init_file = dir_path / "__init__.py"
        if init_file.exists() and not _get_docstring(init_file):
            missing.append(f"{dir_key}/__init__.py")

        # 각 모듈 docstring
        for f in sorted(dir_path.iterdir()):
            if f.suffix == ".py" and f.name != "__init__.py":
                if not _get_docstring(f):
                    rel = f.relative_to(ROOT)
                    missing.append(str(rel))

    if missing:
        for p in missing:
            warn(f"docstring 누락: {p}")
        print(f"  총 {len(missing)}개 파일에 docstring 없음")
    else:
        ok("모든 .py 파일에 docstring 있음")


# ════════════════════════════════════════
#  16. Phase 2 Extractor 파일 존재 & 인터페이스
# ════════════════════════════════════════
@check("16. Phase 2 Extractor 파일 존재 & 인터페이스", ["phase"])
def check_phase2_extractors():
    extractors_dir = ROOT / "src" / "sync" / "extractors"

    # 필수 파일 존재 확인
    required = [
        "base.py", "__init__.py",
        "garmin_extractor.py", "strava_extractor.py",
        "intervals_extractor.py", "runalyze_extractor.py",
    ]
    missing = [f for f in required if not (extractors_dir / f).exists()]
    if missing:
        for f in missing:
            error(f"src/sync/extractors/{f} 없음")
        return
    ok(f"Extractor 파일 {len(required)}개 전부 존재")

    # get_extractor() 팩토리 함수 확인
    init_text = (extractors_dir / "__init__.py").read_text(encoding="utf-8")
    if "def get_extractor" not in init_text:
        error("get_extractor() 없음 — src/sync/extractors/__init__.py")
    else:
        ok("get_extractor() 팩토리 함수 존재")

    # activity_types.py 존재 확인
    if not (ROOT / "src" / "utils" / "activity_types.py").exists():
        error("src/utils/activity_types.py 없음")
    else:
        ok("activity_types.py 존재")

    # 각 extractor에 SOURCE 클래스 변수 및 필수 메서드 확인
    ext_files = [
        ("garmin_extractor.py", "garmin"),
        ("strava_extractor.py", "strava"),
        ("intervals_extractor.py", "intervals"),
        ("runalyze_extractor.py", "runalyze"),
    ]
    for fname, source in ext_files:
        text = (extractors_dir / fname).read_text(encoding="utf-8")
        if f'SOURCE = "{source}"' not in text:
            warn(f"{fname}: SOURCE = \"{source}\" 없음")
        if "def extract_activity_core" not in text:
            error(f"{fname}: extract_activity_core() 미구현")
        if "def extract_activity_metrics" not in text:
            error(f"{fname}: extract_activity_metrics() 미구현")

    ok("4개 Extractor SOURCE, extract_activity_core/metrics 구현 확인")


# ════════════════════════════════════════
#  17. Phase 3 Sync 핵심 파일 존재 검증
# ════════════════════════════════════════
@check("17. Phase 3 Sync 핵심 파일 존재 검증", ["phase"])
def check_phase3_sync():
    sync_dir = ROOT / "src" / "sync"
    required = [
        "sync_result.py", "rate_limiter.py", "raw_store.py", "_helpers.py",
        "dedup.py", "orchestrator.py", "reprocess.py",
        "garmin_activity_sync.py", "garmin_wellness_sync.py",
        "strava_activity_sync.py", "intervals_activity_sync.py",
        "runalyze_activity_sync.py",
    ]
    missing = [f for f in required if not (sync_dir / f).exists()]
    if missing:
        for f in missing:
            error(f"src/sync/{f} 없음")
    else:
        ok(f"Phase 3 핵심 파일 {len(required)}개 전부 존재")

    # CLI 진입점
    if not (ROOT / "src" / "sync_cli.py").exists():
        warn("src/sync_cli.py 없음")
    else:
        ok("sync_cli.py 존재")

    # full_sync() 존재 확인
    orch = sync_dir / "orchestrator.py"
    if orch.exists():
        text = orch.read_text(encoding="utf-8")
        if "def full_sync" not in text:
            warn("orchestrator.py: full_sync() 없음")
        else:
            ok("orchestrator.py: full_sync() 존재")

    # dedup.run() 존재 + 전체 초기화 설계 확인
    dedup = sync_dir / "dedup.py"
    if dedup.exists():
        text = dedup.read_text(encoding="utf-8")
        if "def run" not in text:
            warn("dedup.py: run() 없음")
        else:
            ok("dedup.py: run() 존재")
        if "matched_group_id = NULL" not in text:
            error("dedup.py: run() 시작 시 matched_group_id 전체 초기화 없음 (설계: 전체 reset 후 재계산)")
        else:
            ok("dedup.py: matched_group_id 전체 초기화 확인")

    # reprocess_all() 존재 확인
    rp = sync_dir / "reprocess.py"
    if rp.exists():
        text = rp.read_text(encoding="utf-8")
        if "def reprocess_all" not in text:
            warn("reprocess.py: reprocess_all() 없음")
        else:
            ok("reprocess.py: reprocess_all() 존재")

    # wellness entity_type 이름 검증 (설계: wellness_* prefix)
    OLD_WELLNESS_TYPES = {"sleep_day", "hrv_day", "body_battery_day",
                          "stress_day", "user_summary_day"}
    gws = sync_dir / "garmin_wellness_sync.py"
    if gws.exists():
        text = gws.read_text(encoding="utf-8")
        old_found = [t for t in OLD_WELLNESS_TYPES if f'"{t}"' in text or f"'{t}'" in text]
        if old_found:
            error(f"garmin_wellness_sync.py: 구버전 entity_type 사용 — {', '.join(old_found)} (→ wellness_* 로 변경)")
        else:
            ok("garmin_wellness_sync.py: wellness_* entity_type 사용 확인")
    if rp.exists():
        text = (sync_dir / "reprocess.py").read_text(encoding="utf-8")
        old_found = [t for t in OLD_WELLNESS_TYPES if f'"{t}"' in text or f"'{t}'" in text]
        if old_found:
            error(f"reprocess.py: 구버전 wellness entity_type 사용 — {', '.join(old_found)}")
        else:
            ok("reprocess.py: wellness_* entity_type 사용 확인")


@check("18. Phase 4 Metrics Engine 파일 존재 & 인터페이스 검증", ["phase"])
def check_phase4_metrics():
    metrics_dir = ROOT / "src" / "metrics"

    # 핵심 파일 확인
    required = [
        "base.py", "engine.py", "cli.py", "reprocess.py",
        "trimp.py", "hrss.py", "pmc.py", "acwr.py", "cirs.py",
        "utrs.py", "vdot.py", "darp.py", "classifier.py",
    ]
    missing = [f for f in required if not (metrics_dir / f).exists()]
    if missing:
        for f in missing:
            error(f"src/metrics/{f} 없음")
    else:
        ok(f"Phase 4 핵심 파일 {len(required)}개 전부 존재")

    # engine.py: ALL_CALCULATORS 수 + topological_sort + 핵심 함수
    engine = metrics_dir / "engine.py"
    if engine.exists():
        text = engine.read_text(encoding="utf-8")
        if "ALL_CALCULATORS" not in text:
            error("engine.py: ALL_CALCULATORS 없음")
        else:
            ok("engine.py: ALL_CALCULATORS 존재")
        if "_topological_sort" not in text:
            error("engine.py: _topological_sort() 없음")
        else:
            ok("engine.py: _topological_sort() 존재")
        required_fns = ["recompute_recent", "recompute_all", "clear_runpulse_metrics"]
        missing_fns = [f for f in required_fns if f"def {f}" not in text]
        if missing_fns:
            for fn in missing_fns:
                error(f"engine.py: {fn}() 없음")
        else:
            ok(f"engine.py: 실행 함수 {required_fns} 전부 존재")
        # ALL_CALCULATORS 수 검증 (설계: 32개)
        try:
            from src.metrics.engine import ALL_CALCULATORS
            if len(ALL_CALCULATORS) != 32:
                error(f"ALL_CALCULATORS 수: {len(ALL_CALCULATORS)}개 (설계: 32개)")
            else:
                ok(f"ALL_CALCULATORS 수: {len(ALL_CALCULATORS)}개 (설계 32개 일치)")
        except Exception:
            warn("ALL_CALCULATORS import 실패 — 수 검증 건너뜀")

    # base.py: CalcContext 전체 API (14개) + CalcResult + ConfidenceBuilder
    base = metrics_dir / "base.py"
    if base.exists():
        text = base.read_text(encoding="utf-8")
        required_apis = [
            "def get_metric", "def get_metric_json", "def get_metric_text",
            "def get_wellness", "def get_streams", "def get_laps",
            "def get_activities_in_range", "def get_activity_metric",
            "def get_activity_metric_text", "def get_activity_metric_series",
            "def get_daily_load", "def get_daily_metric_series",
            "def get_wellness_series", "def update_metric_cache",
        ]
        missing_api = [api for api in required_apis if api not in text]
        if missing_api:
            for api in missing_api:
                error(f"base.py: CalcContext {api}() 없음")
        else:
            ok(f"base.py: CalcContext API {len(required_apis)}개 전부 존재")
        for cls in ["CalcResult", "ConfidenceBuilder"]:
            if f"class {cls}" not in text:
                error(f"base.py: {cls} 없음")
            else:
                ok(f"base.py: {cls} 존재")

    # SEMANTIC_GROUPS 확인 (metric_groups.py)
    mg = ROOT / "src" / "utils" / "metric_groups.py"
    if not mg.exists():
        error("src/utils/metric_groups.py 없음")
    else:
        text = mg.read_text(encoding="utf-8")
        if "SEMANTIC_GROUPS" not in text:
            error("metric_groups.py: SEMANTIC_GROUPS 없음")
        else:
            ok("metric_groups.py: SEMANTIC_GROUPS 존재")


# ════════════════════════════════════════
#  19. Phase 5 서비스 레이어 파일 존재 검증
# ════════════════════════════════════════
@check("19. Phase 5 서비스 레이어 파일 존재 검증", ["phase"])
def check_phase5_services():
    required_services = [
        ("src/services/activity_service.py",   "ActivityService"),
        ("src/services/dashboard_service.py",  "DashboardService"),
        ("src/services/wellness_service.py",   "WellnessService"),
    ]
    required_helpers = [
        ("src/ai/ai_context.py",               "build_ai_context"),
        ("src/web/template_helpers.py",        "format_pace"),
    ]

    services_dir = ROOT / "src" / "services"
    missing_files = []
    missing_classes = []

    for rel_path, cls_name in required_services:
        path = ROOT / rel_path
        if not path.exists():
            missing_files.append(rel_path)
        else:
            text = path.read_text(encoding="utf-8")
            if f"class {cls_name}" not in text and f"def " not in text:
                missing_classes.append(f"{rel_path}: {cls_name} 없음")

    for rel_path, fn_name in required_helpers:
        path = ROOT / rel_path
        if not path.exists():
            missing_files.append(rel_path)
        else:
            text = path.read_text(encoding="utf-8")
            if f"def {fn_name}" not in text:
                missing_classes.append(f"{rel_path}: {fn_name}() 없음")

    if missing_files:
        for f in missing_files:
            warn(f"Phase 5 미구현: {f}")
    if missing_classes:
        for m in missing_classes:
            warn(f"Phase 5 미구현 함수: {m}")
    if not missing_files and not missing_classes:
        ok(f"Phase 5 서비스 파일 {len(required_services)}개 + 헬퍼 {len(required_helpers)}개 전부 존재")


# ════════════════════════════════════════
#  main
# ════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(description="문서 정합성 검증")
    parser.add_argument("--tag", type=str, default=None,
                        help="특정 태그만 실행 (metric, schema, phase, code, general)")
    parser.add_argument("--list", action="store_true", dest="list_checks",
                        help="검사 목록만 출력")
    args = parser.parse_args()

    if args.list_checks:
        print("등록된 검사 목록:")
        for title, tags, _ in _checks:
            print(f"  [{', '.join(tags)}] {title}")
        print(f"\n총 {len(_checks)}개 검사")
        return

    run_tag = args.tag.lower() if args.tag else None
    ran = 0

    for title, tags, fn in _checks:
        if run_tag and run_tag not in tags:
            continue
        section(title)
        ran += 1
        try:
            fn()
        except Exception as e:
            error(f"검사 실행 중 예외: {e}")

    section("결과 요약")
    tag_label = f" (태그: {run_tag})" if run_tag else ""
    print(f"  실행{tag_label}: {ran}개 검사")
    print(f"  Errors: {errors}")
    print(f"  Warnings: {warnings}")
    if errors == 0:
        print("  [PASS] 모든 필수 검사 통과")
    else:
        print(f"  [FAIL] {errors}개 필수 문제 발견")
    if warnings > 0:
        print(f"  [INFO] {warnings}개 경고 (권장 수정)")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()

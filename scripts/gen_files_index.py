#!/usr/bin/env python3
"""files_index.md 자동 생성.

소스: 각 __init__.py docstring (디렉토리 설명) + 각 .py 모듈 docstring + AST.
수동 관리 대상: 코드의 docstring만. 별도 메타데이터 파일 없음.

NOTE: 파일 100개 초과 시 디렉토리별 분리 생성 검토
"""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "v0.3" / "data" / "files_index.md"

SCAN_DIRS = [
    "src/services", "src/metrics", "src/sync", "src/sync/extractors",
    "src/ai", "src/web", "src/training", "src/utils", "tests", "scripts",
]


def get_docstring(filepath: Path) -> str:
    try:
        tree = ast.parse(filepath.read_text(encoding="utf-8"))
        ds = ast.get_docstring(tree)
        return ds.strip() if ds else ""
    except (SyntaxError, UnicodeDecodeError):
        return ""


def get_docstring_first_line(filepath: Path) -> str:
    ds = get_docstring(filepath)
    return ds.split("\n")[0] if ds else ""


def get_public_api(filepath: Path) -> dict:
    source = filepath.read_text(encoding="utf-8")
    result = {"lines": len(source.splitlines()), "classes": [], "functions": []}
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return result

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            methods = [
                item.name for item in node.body
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                and not item.name.startswith("_")
            ]
            result["classes"].append({"name": node.name, "methods": methods})
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith("_"):
                result["functions"].append(node.name)
    return result


def main():
    lines = [
        "# RunPulse 파일 인덱스",
        "",
        "> 자동 생성 (`python3 scripts/gen_files_index.py`) — 수동 편집 금지",
        "> 디렉토리 설명 변경: 해당 `__init__.py` docstring 수정 후 재생성",
        "> 파일 설명 변경: 해당 `.py` 모듈 docstring 수정 후 재생성",
        "",
    ]
    total = 0
    no_docstring = []

    for dir_key in SCAN_DIRS:
        dir_path = ROOT / dir_key
        if not dir_path.exists():
            continue

        files = sorted(
            f for f in dir_path.iterdir()
            if f.suffix == ".py" and f.name != "__init__.py"
        )
        if not files:
            continue

        # 디렉토리 설명 = __init__.py docstring
        init_file = dir_path / "__init__.py"
        dir_doc = get_docstring(init_file) if init_file.exists() else ""

        lines.append(f"## `{dir_key}/`")
        lines.append("")
        if dir_doc:
            for doc_line in dir_doc.split("\n"):
                lines.append(f"> {doc_line}")
            lines.append("")
        else:
            if init_file.exists():
                no_docstring.append(f"{dir_key}/__init__.py")

        for f in files:
            api = get_public_api(f)
            doc_first = get_docstring_first_line(f)
            total += 1

            desc = f" — {doc_first}" if doc_first else ""
            lines.append(f"### `{f.name}` ({api['lines']}줄){desc}")
            lines.append("")

            for cls in api["classes"]:
                methods = ", ".join(cls["methods"]) if cls["methods"] else "없음"
                lines.append(f"- class **{cls['name']}**: {methods}")
            if api["functions"]:
                lines.append(f"- functions: {', '.join(api['functions'])}")
            if not api["classes"] and not api["functions"]:
                lines.append("- (public API 없음)")
            lines.append("")

            if not doc_first:
                rel = f.relative_to(ROOT)
                no_docstring.append(str(rel))

    lines.append("---")
    lines.append(f"총 {total}개 파일")

    if no_docstring:
        lines.append("")
        lines.append("## docstring 누락")
        lines.append("")
        for p in no_docstring:
            lines.append(f"- `{p}`")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Generated {OUTPUT}")
    print(f"  Files: {total}")
    if no_docstring:
        print(f"  Missing docstrings: {len(no_docstring)}")


if __name__ == "__main__":
    main()
    

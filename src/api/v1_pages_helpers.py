"""v1 import·sync-status 화면용 작은 HTML/스캔 헬퍼 (views_dev 에서 이관, S4-33)."""
from __future__ import annotations

import html
from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _rel(p: Path) -> str:
    try:
        return str(p.relative_to(_project_root()))
    except ValueError:
        return str(p)


def table(headers: list[str], rows: list[tuple]) -> str:
    if not rows:
        return "<p class='muted'>(no rows)</p>"
    head = "".join(f"<th>{html.escape(h)}</th>" for h in headers)
    body_rows = []
    for row in rows:
        cols = "".join(f"<td>{html.escape(str(v))}</td>" for v in row)
        body_rows.append(f"<tr>{cols}</tr>")
    body = "".join(body_rows)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def scan_history_dir(base_dir: Path) -> dict:
    from collections import Counter

    _SUPPORTED = {".fit", ".gpx", ".tcx", ".fit.gz", ".gpx.gz", ".tcx.gz"}
    if not base_dir.exists():
        return {
            "exists": False,
            "base_dir": str(base_dir),
            "total_files": 0,
            "by_ext": [],
            "sample_files": [],
        }

    files = [
        p for p in base_dir.rglob("*")
        if p.is_file() and any(
            "".join(p.suffixes).lower().endswith(ext) for ext in _SUPPORTED
        )
    ]

    def _ext(p: Path) -> str:
        s = "".join(p.suffixes).lower()
        for ext in (".fit.gz", ".gpx.gz", ".tcx.gz"):
            if s.endswith(ext):
                return ext
        return p.suffix.lower()

    counts = Counter(_ext(p) for p in files)
    samples = [_rel(p) for p in sorted(files)[:20]]

    return {
        "exists": True,
        "base_dir": str(base_dir),
        "total_files": len(files),
        "by_ext": sorted(counts.items()),
        "sample_files": samples,
    }


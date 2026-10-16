"""v39 백필 드라이런 — DB 사본에 ensure_v39를 적용하고 보고서를 출력(원본 쓰기 없음)."""
from __future__ import annotations

import json
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.db_schema_v39 import ensure_v39  # noqa: E402


def run(db_path: str) -> dict:
    with tempfile.TemporaryDirectory() as td:
        copy = Path(td) / "running.db"
        src = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        dst = sqlite3.connect(copy)
        src.backup(dst)
        src.close()
        try:
            return ensure_v39(dst, backup=False)
        finally:
            dst.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: race_backfill_dry_run.py <running.db>")
    print(json.dumps(run(sys.argv[1]), ensure_ascii=False, indent=2))

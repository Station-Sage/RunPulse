"""계획 엔진 백테스트 CLI — 실DB 사본(읽기 전용)의 역사 시나리오와 합성 격자를 돌려 게이트 결과를 JSON 으로 낸다."""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.training import plan_backtest as B  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", help="실DB 경로(읽기 전용). 없으면 합성 격자만")
    ap.add_argument("--out", default="plan_backtest.json")
    ap.add_argument("--engine", choices=["v1", "v2"], default="v1")
    ap.add_argument("--grid-limit", type=int, default=0, help="격자 시나리오 수 제한(0=전부)")
    ap.add_argument("--distance", help="격자 거리 필터(예: full)")
    a = ap.parse_args()
    scenarios, base = [], None
    if a.db:
        src = sqlite3.connect(f"file:{a.db}?mode=ro", uri=True)
        base = sqlite3.connect(":memory:")
        src.backup(base)
        src.close()
        base.row_factory = sqlite3.Row
        from src.db_setup import migrate_db
        migrate_db(base)       # 사본을 최신 스키마로(운영 DB는 건드리지 않음)
        scenarios += B.history_scenarios(base)
    grid = [g for g in B.grid_scenarios() if not a.distance or g.distance == a.distance]
    scenarios += grid[: a.grid_limit] if a.grid_limit else grid
    results = [B.run_scenario(s, base, engine=B.engine_v2 if a.engine == "v2" else B.engine_v1) for s in scenarios]
    summary = B.summarize(results)
    Path(a.out).write_text(json.dumps({"summary": summary, "results": results}, ensure_ascii=False, indent=1))
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0 if summary["passed"] == summary["total"] else 1


if __name__ == "__main__":
    sys.exit(main())

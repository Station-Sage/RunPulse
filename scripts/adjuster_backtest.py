"""조정기 v2 vs v3 백테스트 — DB 사본에서 최근 N일(기본 90)의 일별 제안 건수를 비교한다 (ADJ §3.13).

원본 DB 는 읽기만 하고 임시 사본에서 adjuster_version 을 바꿔 가며 제안만 만든다(저장 안 함).
이미 수행한 날의 계획은 제안 대상이 아니므로(adjuster 가 None 반환) 과거 일수가 많을수록 과소 집계될 수 있다.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
import tempfile
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.services import plan_adjustment_proposal as prop  # noqa: E402
from src.services.user_settings_service import set_setting  # noqa: E402


def run(conn: sqlite3.Connection, today: date, days: int = 90) -> dict:
    """사본 conn 에서 v2/v3 일별 제안을 비교해 요약 dict 를 돌려준다."""
    out = {"days": days, "v2": 0, "v3": 0, "both": 0, "v3_only": 0, "v2_only": 0,
           "v3_sources": Counter(), "weekly_v3": Counter()}
    for i in range(days, 0, -1):
        d = (today - timedelta(days=i)).isoformat()
        res = {}
        for ver in ("v2", "v3"):
            set_setting(conn, "adjuster_version", ver)
            try:
                w, _ = prop._propose(conn, d)
            except Exception:
                w = None
            res[ver] = bool(w and w.get("adjusted"))
            if ver == "v3" and res[ver]:
                out["v3_sources"][w.get("source") or "readiness"] += 1
                y, wk, _ = date.fromisoformat(d).isocalendar()
                out["weekly_v3"][f"{y}-W{wk:02d}"] += 1
        out["v2"] += res["v2"]
        out["v3"] += res["v3"]
        out["both"] += res["v2"] and res["v3"]
        out["v3_only"] += res["v3"] and not res["v2"]
        out["v2_only"] += res["v2"] and not res["v3"]
    out["v3_sources"], out["weekly_v3"] = dict(out["v3_sources"]), dict(sorted(out["weekly_v3"].items()))
    out["weeks_over_3"] = sum(1 for n in out["weekly_v3"].values() if n > 3)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("db")
    ap.add_argument("--days", type=int, default=90)
    ap.add_argument("--today", default=date.today().isoformat())
    a = ap.parse_args()
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / "copy.db"
        shutil.copy(a.db, tmp)
        conn = sqlite3.connect(tmp)
        print(json.dumps(run(conn, date.fromisoformat(a.today), a.days), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

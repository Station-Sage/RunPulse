"""G5 게이트 리포트 — 전 사용자 DB의 ui_events 를 읽기 전용으로 집계해 v1 복귀율을 출력한다."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.services.ui_events_service import PASS_RATE, summarize_all_users  # noqa: E402

LABELS = {"missing_feature": "기능 없음", "hard_to_use": "쓰기 어려움",
          "slow_or_error": "느림/오류", "just_looking": "그냥 둘러봄", "skipped": "건너뜀"}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--days", type=int, default=14)
    ap.add_argument("--since", help="YYYY-MM-DD 부터 오늘까지로 창을 잡는다 (--days 무시)")
    ap.add_argument("--users-root", default=str(ROOT / "data" / "users"))
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    days = a.days
    if a.since:
        days = (date.today() - date.fromisoformat(a.since)).days + 1
    r = summarize_all_users(a.users_root, days)
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return 0
    rate = "-" if r["rate"] is None else f"{r['rate']:.1%}"
    print(f"기간 {r['from']} ~ {r['to']} ({r['window_days']}일)")
    print(f"활성 사용자 {r['active_users']} / 복귀 사용자 {r['rolled_back_users']} / 복귀율 {rate}")
    print(f"판정: {r['verdict']} (기준 <{PASS_RATE:.0%})")
    if r["small_sample"]:
        print("경고: 활성 사용자 10명 미만 — 표본이 작아 참고용")
    if r["orphan_rollback_users"]:
        print(f"경고: v2 방문 기록 없이 복귀한 사용자 {r['orphan_rollback_users']}명")
    print("사유:", ", ".join(f"{LABELS[k]} {v}" for k, v in r["rollback_by_reason"].items()))
    for n in r["recent_notes"]:
        print(f"  [{n['day']}] {n['note']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

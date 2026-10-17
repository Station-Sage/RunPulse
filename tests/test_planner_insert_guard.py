"""planned_workouts INSERT 는 planner_store·replan undo 등 허용 모듈에서만 한다(goal_id 필수 불변식, S4-17/18)."""
from __future__ import annotations

import re
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
ALLOWED = {
    "training/planner_store.py", "training/plan_replace.py", "training/rematch.py",
    "services/plan_adjustment_service.py", "services/plan_replan_service.py",
    "db_schema.py", "db_setup.py",
    "sync/plan_ingest.py",  # 외부 계획 수집 — source 가 planner 가 아님
    "web/views_training_goal_crud.py", "web/views_training_crud.py",  # v1 수동 입력 — S5 4단계(v1 삭제)에서 제거 예정
}
PAT = re.compile(r"INSERT\s+(?:OR\s+\w+\s+)?INTO\s+planned_workouts", re.I)


def test_planned_workouts_inserts_only_in_allowed_modules():
    bad = []
    for p in SRC.rglob("*.py"):
        rel = p.relative_to(SRC).as_posix()
        if rel in ALLOWED or rel.startswith("db_"):
            continue
        if PAT.search(p.read_text(encoding="utf-8")):
            bad.append(rel)
    assert bad == [], f"허용 목록 밖 INSERT: {bad}"

"""settings.py 경로 상수 — QUEUE_PATH/STATE_DIR는 AUTOPILOT_HOST_DIR, DECISIONS_PATH는
WORKTREE_DIR 기준으로 고정돼 있는지. "어디서 스크립트를 실행했는지"(PROJECT_ROOT)와
무관해야 한다(AUD-dd4c72 등 18건이 이 경로 혼선으로 묻혔던 사고의 회귀 테스트).
"""
from __future__ import annotations

import subprocess
import sys

from scripts.autopilot import settings


def test_queue_is_under_autopilot_host_dir():
    # STATE_DIR/LEDGER_PATH는 conftest의 _isolate_autopilot_state가 테스트마다 임시
    # 경로로 덮어써서(실 원장 오염 방지) 여기서 host_dir 관계를 직접 확인할 수 없다 —
    # 그 관계는 격리되지 않은 서브프로세스(test_host_dir_env_override_changes_queue_path)로 확인한다.
    assert settings.QUEUE_PATH.is_relative_to(settings.AUTOPILOT_HOST_DIR)


def test_decisions_path_is_under_worktree_dir():
    """DECISIONS.md는 모델이 claude -p 세션에서 직접 커밋하는 파일이라 QUEUE_PATH와 달리
    WORKTREE_DIR 기준이어야 한다(run_unit.py가 실제로 보는 파일과 일치)."""
    assert settings.DECISIONS_PATH.parent == settings.WORKTREE_DIR / "v0.3" / "data" / "phase-7-ui-renewal"


def test_host_dir_env_override_changes_queue_path(tmp_path):
    """실행 위치(PROJECT_ROOT)가 아니라 환경변수로만 바뀌어야 한다 — 다른 체크아웃에서
    실행해도 같은 파일을 보장하려는 장치."""
    code = (
        "import os, sys; sys.path.insert(0, %r); "
        "from scripts.autopilot import settings; "
        "print(settings.QUEUE_PATH); print(settings.STATE_DIR)"
    ) % str(settings.PROJECT_ROOT)
    r = subprocess.run(
        [sys.executable, "-c", code],
        env={"RUNPULSE_AUTOPILOT_HOST": str(tmp_path), "PATH": "/usr/bin:/bin"},
        capture_output=True, text=True, check=True,
    )
    queue_line, state_line = r.stdout.strip().splitlines()
    assert queue_line == str(tmp_path / "v0.3" / "data" / "phase-7-ui-renewal" / "BACKLOG.md")
    assert state_line == str(tmp_path / ".claude" / "autopilot")

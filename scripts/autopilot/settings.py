"""자율 실행 설정값 — 예산 상한, 실행 시간대, 격리 브랜치, 허용 도구.

비밀값 없음(토큰은 ~/.claude/에서 직접 읽음) — 이 파일은 git 추적 대상.
값을 바꿀 때는 관측된 실측치(RUN-LOG, ledger)를 근거로 한다. 최초값은
2026-09-22 스파이크 실측(헤드리스 1회 고정비 ≈$0.03~0.04) 기준 보수적으로 설정.
"""
from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# ── 예산 (관측 모드 — 사람이 원장을 보고 올린다. 자동 상향 없음) ──
PER_RUN_MAX_USD = 0.5          # --max-budget-usd. 헤드리스 1회 고정비의 ~12배 여유
DAILY_MAX_USD = 1.5            # 하루 누적 상한 (ledger 기준)
WEEKLY_MAX_USD = 6.0           # 주 누적 상한 (seven_day 사용률을 직접 관측할 수 없어 자체 집계)

# ── 실행 시간대 (Asia/Seoul, KST) — 사용자가 접속하지 않는 시간대 기본값 ──
# 확정 아님: 실제 비활동 시간대 확인 후 조정. 새벽대는 보수적으로 안전한 기본값.
NIGHT_START_HOUR = 2
NIGHT_END_HOUR = 6

IDLE_MINUTES_REQUIRED = 30      # 이 세션 등 최근 활동이 있으면 양보
CIRCUIT_BREAKER_FAILS = 2       # 연속 실패 시 정지

# ── 격리 실행 위치 ──
AUTOPILOT_BRANCH = "autopilot/phase7"
WORKTREE_DIR = PROJECT_ROOT / ".claude" / "worktrees" / "autopilot-phase7"
STATE_DIR = PROJECT_ROOT / ".claude" / "autopilot"   # untracked (gitignore)
LEDGER_PATH = STATE_DIR / "ledger.jsonl"
LOCK_PATH = STATE_DIR / "run.lock"
STOP_PATH = STATE_DIR / "STOP"
PAUSE_PATH = STATE_DIR / "PAUSE"
RUN_LOG_DIR = STATE_DIR / "runs"

QUEUE_PATH = PROJECT_ROOT / "v0.3" / "data" / "phase-7-ui-renewal" / "BACKLOG.md"
DECISIONS_PATH = PROJECT_ROOT / "v0.3" / "data" / "phase-7-ui-renewal" / "DECISIONS.md"

MODEL = "sonnet"                # 자동 실행은 Sonnet만 (Opus 주간 버킷은 수동 작업용 보호)
RUN_TIMEOUT_SEC = 20 * 60

ALLOWED_TOOLS = [
    "Read", "Write", "Edit", "Grep", "Glob",
    "Bash(git status:*)", "Bash(git add:*)", "Bash(git commit:*)",
    "Bash(git diff:*)", "Bash(git log:*)", "Bash(git show:*)",
    "Bash(wc:*)", "Bash(ls:*)", "Bash(cat:*)",
]
DISALLOWED_TOOLS = [
    "WebFetch", "WebSearch", "Agent", "Workflow",
    "Artifact", "ArtifactComments", "ArtifactData",
]

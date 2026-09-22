"""자율 실행 설정값 — 예산 상한, 실행 시간대, 격리 브랜치, 허용 도구.

비밀값 없음(토큰은 ~/.claude/에서 직접 읽음) — 이 파일은 git 추적 대상.
값을 바꿀 때는 관측된 실측치(RUN-LOG, ledger)를 근거로 한다. 최초값은
2026-09-22 스파이크 실측(헤드리스 1회 고정비 ≈$0.03~0.04) 기준 보수적으로 설정.
"""
from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# ── 예산 (관측 모드 — 사람이 원장을 보고 올린다. 자동 상향 없음) ──
# PER_RUN_MAX_USD: 최초값 $0.5는 self-test(간단한 파일 1개 작업, 실측 $0.095)만
# 보고 잡은 값이었음 — 실제 문서 작업(68KB 파일 읽기 등)엔 부족해서 2026-09-22
# P7-AUTO-SPLIT-03가 탐색 단계(10턴, 쓰기 전)에서 예산 초과로 실패(실측 $0.510).
# $1.0로 상향 — 여전히 관측 모드, 더 큰 작업이 나오면 다시 근거를 보고 올린다.
PER_RUN_MAX_USD = 1.0          # --max-budget-usd
DAILY_MAX_USD = 2.0            # 하루 누적 상한 (ledger 기준)
WEEKLY_MAX_USD = 8.0           # 주 누적 상한 (seven_day 사용률을 직접 관측할 수 없어 자체 집계)

# ── 실행 시간대 (Asia/Seoul, KST) — 사용자가 접속하지 않는 시간대 기본값 ──
# 확정 아님: 실제 비활동 시간대 확인 후 조정. 새벽대는 보수적으로 안전한 기본값.
NIGHT_START_HOUR = 2
NIGHT_END_HOUR = 6

IDLE_MINUTES_REQUIRED = 30      # 이 세션 등 최근 활동이 있으면 양보
CIRCUIT_BREAKER_FAILS = 2       # 연속 실패 시 정지

# ── 격리 실행 위치 ──
BASE_BRANCH = "renew/data-architecture"   # 매 실행 전 이 브랜치 최신으로 rebase
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
    "Bash(git diff:*)", "Bash(git log:*)", "Bash(git show:*)", "Bash(git mv:*)",
    # 읽기·발췌 전용 — 큰 파일을 Read+Write로 왕복하는 대신 sed/awk로 바이트 그대로
    # 발췌하게 하면 "내용을 안 바꾸는" 기계적 작업의 비용이 훨씬 준다.
    "Bash(wc:*)", "Bash(ls:*)", "Bash(cat:*)", "Bash(grep:*)", "Bash(sed -n:*)", "Bash(head:*)", "Bash(tail:*)",
]
DISALLOWED_TOOLS = [
    "WebFetch", "WebSearch", "Agent", "Workflow",
    "Artifact", "ArtifactComments", "ArtifactData",
]

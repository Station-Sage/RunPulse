"""자율 실행 설정값 — 예산 상한, 실행 시간대, 격리 브랜치, 허용 도구.

비밀값 없음(토큰은 ~/.claude/에서 직접 읽음) — 이 파일은 git 추적 대상.
값을 바꿀 때는 관측된 실측치(RUN-LOG, ledger)를 근거로 한다. 최초값은
2026-09-22 스파이크 실측(헤드리스 1회 고정비 ≈$0.03~0.04) 기준 보수적으로 설정.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# ── 예산 (관측 모드 — 사람이 원장을 보고 올린다. 자동 상향 없음) ──
# PER_RUN_MAX_USD: 최초값 $0.5는 self-test(간단한 파일 1개 작업, 실측 $0.095)만
# 보고 잡은 값이었음 — 실제 문서 작업(68KB 파일 읽기 등)엔 부족해서 2026-09-22
# P7-AUTO-SPLIT-03가 탐색 단계(10턴, 쓰기 전)에서 예산 초과로 실패(실측 $0.510).
# $1.0로 상향 — 여전히 관측 모드, 더 큰 작업이 나오면 다시 근거를 보고 올린다.
PER_RUN_MAX_USD = 1.0          # --max-budget-usd (kind="docs")
# 일간 USD 상한은 폐지(2026-11-25) — 5시간·주간 사용률을 rate_limit 관측값으로 직접 쓴다(pacing.py).
WEEKLY_MAX_USD = 30.0          # 주 누적 상한 (seven_day 사용률을 직접 관측할 수 없어 자체 집계)

# ── 페이싱(pacing.py) — 실제 rate_limit 관측 기반. 게이트는 이것을 쓰고 주간 USD 상한은 보조 안전장치 ──
SESSION_CEILING = 0.8           # 5시간 세션 사용률이 이 이상이면 리셋까지 양보(사람 몫 20% 보존)
SESSION_PACING_ENABLED = 1      # 1=5시간 세션 게이트 사용, 0=건너뜀(주간·수동 보류는 유지)
WEEKLY_PACING_ENABLED = 1       # 1=주간 균등 사용 게이트 사용, 0=건너뜀(5시간 세션·수동 보류는 유지)
WEEK_CEILING = 0.85             # 주간 사용률 절대 상한
PACE_FLOOR = 0.15               # 주 시작 직후에도 허용하는 최소 목표선
PACE_SLACK = 0.70               # 목표선 = FLOOR + 경과비율 × SLACK (주말에 FLOOR+SLACK=0.85)
CYCLE_MIN_INTERVAL_MIN = 90     # 감사 사이클 최소 간격(분) — 페이싱 통과해도 이보다 자주 돌지 않는다

# kind="code" 전용 — 파일 읽기/쓰기 외에 테스트·빌드 왕복이 들어가 turn 수가 늘어난다.
# 실측치 없음(2026-09-22 최초 도입) — 관측 모드 원칙(위 주석)과 동일하게, 첫 실측 후
# ledger 근거로 재조정한다. docs 대비 2~3배로 보수적으로 잡음.
PER_RUN_MAX_USD_CODE = 2.5
RUN_TIMEOUT_SEC_CODE = 40 * 60  # docs(20분)보다 김 — npm install/pytest 왕복 포함

# ── 실행 시간대 (Asia/Seoul, KST) — 사용자가 접속하지 않는 시간대 기본값 ──
# 확정 아님: 실제 비활동 시간대 확인 후 조정. 새벽대는 보수적으로 안전한 기본값.
NIGHT_START_HOUR = 2
NIGHT_END_HOUR = 6

IDLE_MINUTES_REQUIRED = 30      # 이 세션 등 최근 활동이 있으면 양보
CIRCUIT_BREAKER_FAILS = 2       # 연속 실패 시 정지

# ── 격리 실행 위치 ──
BASE_BRANCH = "renew/data-architecture"   # 매 실행 전 이 브랜치 최신으로 merge
AUTOPILOT_BRANCH = "autopilot/phase7"
def _main_checkout() -> Path:
    """메인 체크아웃(git common dir 의 부모) — 어느 워크트리에서 실행해도 autopilot 워크트리는 한 곳에 둔다."""
    try:
        r = subprocess.run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], cwd=PROJECT_ROOT,
                           capture_output=True, text=True, timeout=10, check=True)
        return Path(r.stdout.strip()).parent
    except (OSError, subprocess.SubprocessError):
        return PROJECT_ROOT


WORKTREE_DIR = _main_checkout() / ".claude" / "worktrees" / "autopilot-phase7"

# 큐(BACKLOG.md)·원장·락은 "지금 스크립트를 실행 중인 체크아웃"(PROJECT_ROOT)이 아니라
# 이 고정 경로(오케스트레이터·관제 콘솔 전용 호스트) 기준으로 둔다 — 전에는 PROJECT_ROOT
# 기준이라 어디서 실행하느냐에 따라 다른 BACKLOG.md를 읽고 써서, stage 전이가 쓰여도
# 콘솔이 보는 복사본에는 반영되지 않는 사고가 실제로 있었다(AUD-dd4c72 등 18건).
AUTOPILOT_HOST_DIR = Path(os.environ.get("RUNPULSE_AUTOPILOT_HOST", "/home/ubuntu/projects/RunPulse-p0"))
STATE_DIR = AUTOPILOT_HOST_DIR / ".claude" / "autopilot"   # untracked (gitignore)
LEDGER_PATH = STATE_DIR / "ledger.jsonl"
LOCK_PATH = STATE_DIR / "run.lock"
STOP_PATH = STATE_DIR / "STOP"
PAUSE_PATH = STATE_DIR / "PAUSE"
RUN_LOG_DIR = STATE_DIR / "runs"

QUEUE_PATH = AUTOPILOT_HOST_DIR / "v0.3" / "data" / "phase-7-ui-renewal" / "BACKLOG.md"
# DECISIONS.md는 모델이 claude -p 세션 중 직접 쓰고 커밋하는 파일이라 WORKTREE_DIR 기준이
# 맞다(run_unit.py._decisions_changed/_asked_outcome가 실제로 보는 파일과 일치시킴) —
# 전에는 이 상수만 AUTOPILOT_HOST_DIR 기준이라 status.py 표시용이 실제 판정과 다른 파일을
# 가리켰다.
DECISIONS_PATH = WORKTREE_DIR / "v0.3" / "data" / "phase-7-ui-renewal" / "DECISIONS.md"

MODEL = "sonnet"                # 자동 실행은 Sonnet 기본 — Opus 는 큰 설계·릴리스 감사에만 scripts/audit/budget.py 한도 안에서
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

# kind="code" 전용 — 위 ALLOWED_TOOLS에 테스트·문서검증·프론트엔드 빌드 왕복을 더한다.
# 여전히 DB(data/)·CLAUDE.md·.claude/·다른 브랜치는 프롬프트(run_unit.py) 레벨에서
# 범위 밖으로 명시한다 — 도구 허용만으로 범위를 강제하지 않는다(worktree 격리 +
# _post_verify()가 실제 안전판, ALLOWED_TOOLS는 1차 방어선).
CODE_ALLOWED_TOOLS = ALLOWED_TOOLS + [
    "Bash(python3 -m pytest:*)",
    "Bash(python3 scripts/check_docs.py:*)",
    "Bash(cd:*)",
    "Bash(npm install:*)", "Bash(npm ci:*)",
    "Bash(npm run build:*)", "Bash(npm run check:*)", "Bash(npm run test:unit:*)", "Bash(node --test:*)",
]

# ── 감사 발견(discover) — 도구를 쓰는 감사 호출은 비싸므로 라운드당 상한을 둔다. 관제 콘솔이 STATE_DIR/tunables.json 으로 덮어쓴다 ──
AUDIT_TOOL_CALLS_PER_ROUND = 8


def tunable(name: str, default=None):
    """STATE_DIR/tunables.json 의 덮어쓰기 값 → 없으면 이 모듈의 상수 → default. 관제에서 재시작 없이 조정."""
    import json
    try:
        data = json.loads((STATE_DIR / "tunables.json").read_text(encoding="utf-8"))
        if name in data:
            return data[name]
    except (OSError, ValueError):
        pass
    return globals().get(name, default)

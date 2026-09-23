"""자율 실행 러너 — 큐에서 작업 1건을 골라 claude -p로 실행하고 결과를 기록한다.

용법:
    python3 -m scripts.autopilot.run_unit                # 게이트 통과 시 1건 실행
    python3 -m scripts.autopilot.run_unit --dry-run       # 무엇을 할지만 출력, LLM 호출 없음
    python3 -m scripts.autopilot.run_unit --ignore-night  # 시간대 게이트 무시 (수동 검증용)

게이트(gate.py)를 통과해야 실행하며, 실행은 격리된 git worktree(worktree.py)
안에서만 이루어진다. 완료 후 성공이라도 stage는 "review"로 남는다 — 자동 병합은
하지 않는다(사람이 검토·병합). 결과는 ledger.py에 기록하고 notify.py로 통지한다.

동시 실행 방지: settings.LOCK_PATH 존재 시 즉시 종료(같은 실행 중이라고 가정).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from . import gate, ledger, notify, queue, settings, worktree

_PROMPT_TEMPLATE_DOCS = """\
당신은 RunPulse 프로젝트의 Phase 7 UI 재설계 설계 문서 작업을 무인(사람 없이)으로 수행합니다.

규칙 (반드시 지킬 것):
- 작업 범위는 v0.3/data/phase-7-ui-renewal/ 안의 설계 문서로 한정합니다. 이 범위 밖
  (app 코드, DB, CLAUDE.md, .claude/, 다른 브랜치 등)은 절대 건드리지 않습니다.
- 먼저 CLAUDE.md와 v0.3/data/phase-7-ui-renewal/BACKLOG.md를 읽고 그 규칙을 따릅니다.
- 이미 확정된 결정(00 문서의 분기점 A~D, 01의 8원칙)을 바꾸는 판단, 또는 비전·방향성
  트레이드오프가 필요한 갈림길을 만나면 임의로 결정하지 마세요. 대신
  v0.3/data/phase-7-ui-renewal/DECISIONS.md 맨 끝에 "## [{item_id}] <제목>" 섹션으로
  질문·선택지 2~3개·당신의 권고 1개를 append하고, 그 갈림길 이전까지 한 작업만 커밋한
  뒤 종료합니다. 이번 실행은 그것으로 완료된 것으로 간주합니다.
- 작업을 마치면 (부분 완료라도) 반드시 git commit 하나 이상으로 마무리합니다. 커밋
  메시지는 conventional commits(docs:/feat: 등), 무엇을 끝냈고 무엇이 남았는지 명시.
- push는 하지 않습니다. 이 브랜치({branch})는 검토 후 사람이 병합합니다.
- 확신 없는 사실(DB 값, 기존 코드 동작)은 추측하지 말고, 확인할 수 없으면 문서에
  "TODO: 확인 필요"로 남기세요.

이번 작업 [{item_id}]:
{item_text}
"""

_PROMPT_TEMPLATE_CODE = """\
당신은 RunPulse 프로젝트의 코드 구현 작업을 무인(사람 없이)으로 수행합니다.

규칙 (반드시 지킬 것):
- 이번 작업이 건드려도 되는 범위는 다음으로 한정합니다:
{scope}
  이 범위 밖의 파일(다른 기능 영역, CLAUDE.md, .claude/, 다른 브랜치 등)은 절대 건드리지
  않습니다. data/ 아래 실제 사용자 DB(running.db 등)는 존재해도 절대 열지 않습니다 —
  테스트는 기존 conftest.py의 db_conn 픽스처(임시 DB) 또는 tmp_path로만 검증합니다.
- 먼저 CLAUDE.md, .claude/rules/coding-rules.md, .claude/rules/workflow-rules.md를
  읽고 그 규칙을 따릅니다(파일 300줄 이하, Calculator는 CalcContext API만 사용하고
  raw SQL 금지, 새 함수엔 테스트 최소 1개, conventional commits).
- 작업을 마치기 전 반드시 아래 검증 커맨드를 전부 실행해 통과를 확인합니다:
{verify}
  하나라도 실패하면 완료로 간주하지 말고 원인을 고친 뒤 다시 검증합니다. 이 커맨드들은
  당신의 실행이 끝난 뒤 run_unit.py가 독립적으로 다시 돌려 재확인합니다 — 여기서
  통과했다고 보고해도 실제로 안 통과하면 이번 실행은 "review"가 아니라 "blocked"로
  남고, 이는 이번 실행의 실패로 기록됩니다.
- 이미 확정된 설계 결정을 바꾸는 판단, 또는 여러 타당한 구현 방식 중 하나를 골라야
  하는 갈림길(예: 새 스키마 필드 추가, API 응답 형태 변경)을 만나면 임의로 결정하지
  마세요. 대신 v0.3/data/phase-7-ui-renewal/DECISIONS.md 맨 끝에
  "## [{item_id}] <제목>" 섹션으로 질문·선택지 2~3개·당신의 권고 1개를 append하고,
  그 갈림길 이전까지 한 작업만 커밋한 뒤 종료합니다.
- 아래 "이번 작업" 항목에 함수 시그니처·SQL·의사코드가 적혀 있으면 그것이 구현 명세입니다 —
  참고용이 아니라 그대로 따라야 합니다. 원본 설계 문서(03c-library.md 등)의 목업·예시 행을
  직접 다시 읽더라도 그 예시를 근거로 명세와 다른 구조(그룹 기준·집계 방식·재사용 대상·
  타입/컴포넌트)를 택하지 마세요. 명세가 틀렸다고 판단되면 임의로 대체하지 말고 위의
  "갈림길" 규칙대로 DECISIONS.md에 기록하고 멈춥니다. 명세가 "기존 함수/컴포넌트를 재사용"
  하라고 하면 새로 만들지 말고 import해서 쓰세요. 작업 항목의 파일 목록(scope)에 있는데
  건드리지 않은 파일이 있으면 완료 전에 이유를 커밋 메시지에 적으세요.
- BACKLOG.md에서 이번 작업 [{item_id}] 외의 다른 항목(설명 문구·체크박스·
  `<!-- autopilot: ... -->` 메타 주석 어느 것도)은 절대 건드리지 마세요. 다른 항목이
  이번 작업과 관련 있어 보여도 먼저 구현하거나 대신 끝내지 마세요 — 큐는 한 번에
  한 항목만 실행하도록 설계돼 있고, 다른 항목의 `stage`는 오직 run_unit.py가 그
  항목을 직접 집어 verify 커맨드를 독립 재실행한 뒤에만 바뀝니다. **[{item_id}] 자신의
  메타 주석도 당신이 편집하지 마세요** — "review"로의 전환은 이 실행이 끝난 뒤
  run_unit.py가 verify 결과를 보고 판단합니다. workflow-rules.md의 "완료 체크리스트 1.
  BACKLOG.md 항목 상태 업데이트"는 이 무인 실행에는 적용되지 않습니다(그 규칙은
  사람이 진행하는 일반 세션 몫입니다) — 대신 이번 실행에서는 코드 커밋만 하고 큐
  파일은 전혀 수정하지 않는 것이 완료 조건입니다.
- 작업을 마치면 (부분 완료라도) 반드시 git commit 하나 이상으로 마무리합니다. 커밋
  메시지는 conventional commits(feat:/fix:/test: 등), 무엇을 끝냈고 무엇이 남았는지 명시.
- push는 하지 않습니다. 이 브랜치({branch})는 검토 후 사람이 병합합니다.

이번 작업 [{item_id}]:
{item_text}
"""


def _format_list(items: list[str], empty: str) -> str:
    if not items:
        return f"  {empty}"
    return "\n".join(f"  - {x}" for x in items)


def _build_prompt(item: queue.QueueItem) -> str:
    if item.kind == "code":
        return _PROMPT_TEMPLATE_CODE.format(
            item_id=item.item_id, item_text=item.text, branch=settings.AUTOPILOT_BRANCH,
            scope=_format_list(item.scope, "(scope 미지정 — 위험하니 큐 등록 시 채울 것. 지금은 item 설명 텍스트만 근거로 최대한 보수적으로 판단)"),
            verify=_format_list(item.verify, "python3 -m pytest tests/ -q"),
        )
    return _PROMPT_TEMPLATE_DOCS.format(
        item_id=item.item_id, item_text=item.text, branch=settings.AUTOPILOT_BRANCH,
    )


def _build_cmd(prompt: str, kind: str) -> list[str]:
    allowed = settings.CODE_ALLOWED_TOOLS if kind == "code" else settings.ALLOWED_TOOLS
    budget = settings.PER_RUN_MAX_USD_CODE if kind == "code" else settings.PER_RUN_MAX_USD
    return [
        "claude", "-p", prompt,
        "--model", settings.MODEL,
        "--output-format", "stream-json",
        "--verbose",
        "--no-session-persistence",
        "--permission-mode", "acceptEdits",
        "--allowed-tools", ",".join(allowed),
        "--disallowed-tools", ",".join(settings.DISALLOWED_TOOLS),
        "--max-budget-usd", str(budget),
    ]


def _parse_stream(raw: str) -> dict:
    rate_limit_info = None
    result = None
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        if d.get("type") == "rate_limit_event":
            rate_limit_info = d.get("rate_limit_info")
        elif d.get("type") == "result":
            result = d
    return {"rate_limit_info": rate_limit_info, "result": result}


def _run_claude(item: queue.QueueItem) -> dict:
    prompt = _build_prompt(item)
    cmd = _build_cmd(prompt, item.kind)
    timeout = settings.RUN_TIMEOUT_SEC_CODE if item.kind == "code" else settings.RUN_TIMEOUT_SEC
    started = time.time()
    try:
        proc = subprocess.run(
            cmd, cwd=settings.WORKTREE_DIR, capture_output=True, text=True,
            timeout=timeout, stdin=subprocess.DEVNULL,
        )
        timed_out = False
        stdout, returncode = proc.stdout, proc.returncode
    except subprocess.TimeoutExpired as e:
        timed_out = True
        stdout = (e.stdout or b"").decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
        returncode = -1
    duration = time.time() - started
    parsed = _parse_stream(stdout)

    settings.RUN_LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = settings.RUN_LOG_DIR / f"{int(started)}_{item.item_id}.jsonl"
    log_path.write_text(stdout, encoding="utf-8")

    result = parsed["result"] or {}
    if timed_out:
        outcome = "timeout"
    elif result.get("subtype") == "success" and not result.get("is_error"):
        outcome = "success"
    else:
        outcome = "error"

    return {
        "outcome": outcome,
        "cost_usd": result.get("total_cost_usd"),
        "num_turns": result.get("num_turns"),
        "duration_s": round(duration, 1),
        "rate_limit": parsed["rate_limit_info"],
        "returncode": returncode,
        "log_path": str(log_path),
        "result_subtype": result.get("subtype"),
    }


def _decisions_changed() -> bool:
    r = subprocess.run(
        ["git", "status", "--porcelain", "--", "DECISIONS.md"],
        cwd=settings.WORKTREE_DIR / "v0.3" / "data" / "phase-7-ui-renewal",
        capture_output=True, text=True,
    )
    return bool(r.stdout.strip())


def _post_verify(item: queue.QueueItem) -> tuple[bool, str]:
    """claude -p의 "성공" 자체 보고를 신뢰하지 않고, 워크트리에서 검증 커맨드를
    직접(독립적으로) 다시 돌려 통과를 확인한다. docs 항목은 검증 대상이 아니다 —
    문서 편집은 사람이 diff로 리뷰하는 게 원래 안전판이었다(설계 변경이라).
    code 항목은 실제 테스트/빌드가 통과해야만 review로 넘어가게 하는 게 그 역할을
    대신한다.
    """
    if item.kind != "code":
        return True, ""
    cmds = item.verify or ["python3 -m pytest tests/ -q"]
    for cmd_str in cmds:
        r = subprocess.run(
            cmd_str, shell=True, cwd=settings.WORKTREE_DIR,
            capture_output=True, text=True, timeout=600,
        )
        if r.returncode != 0:
            tail = (r.stdout[-1500:] + "\n" + r.stderr[-1500:]).strip()
            return False, f"`{cmd_str}` 종료코드 {r.returncode}\n{tail}"
    return True, ""


def run_once(
    *, dry_run: bool = False, ignore_night: bool = False, ignore_idle: bool = False,
    ignore_budget: bool = False,
) -> int:
    """1건 실행 시도. 반환값: 0=실행함/스킵함(정상), 1=게이트 차단, 2=오류."""
    gr = gate.check(ignore_night_window=ignore_night, ignore_idle=ignore_idle,
                     ignore_budget=ignore_budget)
    if not gr.allowed:
        print(f"[gate] 차단: {gr.reason}")
        return 1

    items = queue.parse(settings.QUEUE_PATH)
    item = queue.next_runnable(items)
    if item is None:
        print("[queue] 실행할 항목 없음")
        return 0

    print(f"[queue] 다음 항목: [{item.item_id}] {item.text[:60]}")
    if dry_run:
        print("[dry-run] 여기서 중단 — LLM 호출 없음")
        return 0

    settings.STATE_DIR.mkdir(parents=True, exist_ok=True)
    if settings.LOCK_PATH.exists():
        print("[lock] 이미 실행 중으로 보임 — 종료")
        return 1
    settings.LOCK_PATH.write_text(str(os.getpid()))
    try:
        worktree.ensure()
        sync_blocked = worktree.sync()
        if sync_blocked:
            queue.update_item(settings.QUEUE_PATH, item.item_id, stage="blocked")
            notify.send(f"[autopilot] {item.item_id} 차단: {sync_blocked}")
            print(f"[worktree] 차단: {sync_blocked}")
            return 2

        queue.update_item(settings.QUEUE_PATH, item.item_id, stage="in_progress",
                          attempts=item.attempts + 1)

        outcome = _run_claude(item)
        ledger.append({"unit_id": item.item_id, **outcome})

        verify_note = ""
        if outcome["outcome"] == "success":
            if _decisions_changed():
                new_stage = "blocked"
            else:
                verified, verify_note = _post_verify(item)
                new_stage = "review" if verified else "blocked"
        elif item.attempts + 1 >= 2:
            new_stage = "blocked"
        else:
            new_stage = "queued"  # 재시도 허용
        queue.update_item(settings.QUEUE_PATH, item.item_id, stage=new_stage)

        cost = outcome.get("cost_usd")
        cost_str = f"${cost:.3f}" if cost is not None else "N/A"
        notify.send(
            f"[autopilot] {item.item_id} → {outcome['outcome']} (stage={new_stage}, "
            f"cost={cost_str}, {outcome['duration_s']:.0f}s)"
            + (f"\n검증 실패: {verify_note[:500]}" if verify_note else "")
        )
        print(f"[done] {item.item_id}: outcome={outcome['outcome']} stage={new_stage} cost={cost_str}")
        if verify_note:
            print(f"[verify] {verify_note[:1000]}")
        return 0
    finally:
        settings.LOCK_PATH.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--ignore-night", action="store_true",
                        help="시간대 게이트 무시 (수동 검증용)")
    parser.add_argument("--ignore-idle", action="store_true",
                        help="유휴 게이트 무시 (수동 검증용 — 스케줄 실행에서 쓰지 말 것)")
    parser.add_argument("--ignore-budget", action="store_true",
                        help="예산(일간/주간) 게이트 무시 (사람이 명시적으로 승인한 1회성 초과 실행용 — 스케줄 실행에서 쓰지 말 것)")
    args = parser.parse_args()
    sys.exit(run_once(dry_run=args.dry_run, ignore_night=args.ignore_night,
                      ignore_idle=args.ignore_idle, ignore_budget=args.ignore_budget))


if __name__ == "__main__":
    main()

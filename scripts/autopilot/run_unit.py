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

from .prompts import build_cmd as _build_cmd, build_prompt as _build_prompt
from . import gate, ledger, leftovers, notify, queue, settings, size_followup, trailers, worktree


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
            queue.update_item(settings.QUEUE_PATH, item.item_id, stage="failed")
            notify.send(f"[autopilot] {item.item_id} 차단: {sync_blocked}")
            print(f"[worktree] 차단: {sync_blocked}")
            return 2

        queue.update_item(settings.QUEUE_PATH, item.item_id, stage="in_progress",
                          attempts=item.attempts + 1)

        pre_head = worktree._run(["git", "rev-parse", "HEAD"], cwd=settings.WORKTREE_DIR).stdout.strip()
        outcome = _run_claude(item)
        if pre_head:
            trailers.scrub_range(settings.WORKTREE_DIR, pre_head)
        ledger.append({"unit_id": item.item_id, **outcome})

        verify_note = ""
        if outcome["outcome"] == "success":
            if _decisions_changed():
                new_stage = "failed"
            else:
                verified, verify_note = _post_verify(item)
                new_stage = "review" if verified else "failed"
                if verified and item.kind == "code":
                    verify_note = leftovers.commit_leftovers(item, settings.WORKTREE_DIR)
                    added = size_followup.append_followups(item, settings.WORKTREE_DIR, settings.QUEUE_PATH)
                    if added:
                        verify_note += f" 300줄 초과 후속 등록: {', '.join(added)}"
        elif item.attempts + 1 >= 2:
            new_stage = "failed"
        else:
            new_stage = "queued"  # 재시도 허용
        queue.update_item(settings.QUEUE_PATH, item.item_id, stage=new_stage)

        cost = outcome.get("cost_usd")
        cost_str = f"${cost:.3f}" if cost is not None else "N/A"
        notify.send(
            f"[autopilot] {item.item_id} → {outcome['outcome']} (stage={new_stage}, "
            f"cost={cost_str}, {outcome['duration_s']:.0f}s)"
            + (f"\n{'검증 실패' if new_stage == 'failed' else '노트'}: {verify_note[:500]}" if verify_note else "")
        )
        print(f"[done] {item.item_id}: outcome={outcome['outcome']} stage={new_stage} cost={cost_str}")
        if verify_note:
            print(f"[{'verify' if new_stage == 'failed' else 'note'}] {verify_note[:1000]}")
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

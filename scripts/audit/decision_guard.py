"""결정-상태 불변식 검증 — DECISIONS.md 에 적힌 "사용자 결정 대기"가 BACKLOG.md
stage 에 제대로 반영됐는지 교차 확인한다.

배경(AUD-dd4c72 류): 모델이 결정이 필요해 DECISIONS.md 에 메모를 쓰고 그 자리에서
커밋까지 해버리면, run_unit.py._decisions_changed 가 한때 `git status`(미커밋분만)만
봐서 이를 놓쳤다. 그 결과 stage 는 needs_decision 으로 못 넘어가고 queued/done 에
남아, 관제 콘솔(결정 필요 탭은 stage==needs_decision 만 봄)에서 영원히 안 보였다.
run_unit.py 는 pre_head 기준 커밋 여부와 무관하게 비교하도록 고쳤지만(2026-11-28),
BACKLOG.md 는 사람이 직접 stage 를 적어 넣을 수도 있는 평문이라 같은 불일치가
다시 생길 수 있다 — 이 모듈은 그 불일치를 사후에도 잡아내는 안전망이다.
"""
from __future__ import annotations

import re
from pathlib import Path

from scripts.autopilot import queue

_HEAD = re.compile(r"^##\s*\[([^\]]+)\]")
_STATUS = re.compile(r"\*\*상태\*\*:\s*(.+)")
_PENDING_MARK = "대기"
_NO_CODE_MARK = re.compile(r"코드 변경 없음|scope 파일 전부 미수정")


def latest_statuses(decisions_md: str) -> dict[str, str]:
    """ID → DECISIONS.md 에서 가장 마지막(최신) "**상태**:" 줄. 한 섹션이 여러 ID를 묶으면 전부에 적용."""
    out: dict[str, str] = {}
    cur_ids: list[str] = []
    for ln in decisions_md.splitlines():
        m = _HEAD.match(ln)
        if m:
            cur_ids = [x for x in re.split(r"[,\s]+", m.group(1)) if x.startswith("AUD-")]
            continue
        m = _STATUS.search(ln)
        if m and cur_ids:
            for iid in cur_ids:
                out[iid] = m.group(1).strip()
    return out


def find_mismatches(backlog_path: Path, decisions_path: Path) -> list[str]:
    """stage 가 DECISIONS.md 가 말하는 결정 상태와 안 맞는 항목들을 사람이 읽을 설명으로 반환."""
    items = {it.item_id: it for it in queue.parse(backlog_path)}
    text = decisions_path.read_text(encoding="utf-8") if decisions_path.exists() else ""
    problems = []
    for iid, status in latest_statuses(text).items():
        it = items.get(iid)
        if it is None:
            continue
        if _PENDING_MARK in status and it.stage != "needs_decision":
            problems.append(f"{iid}: DECISIONS.md=\"{status[:60]}\" 인데 stage={it.stage} (needs_decision 이어야 함)")
        elif _NO_CODE_MARK.search(status) and it.stage == "done":
            problems.append(f"{iid}: DECISIONS.md=\"{status[:60]}\" (코드 없음) 인데 stage=done")
    return problems

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

_HEAD = re.compile(r"^#{2,3}\s*\[([^\]]+)\]\s*(.*)$")
_STATUS = re.compile(r"\*\*상태\*\*:\s*(.+)")
# "**상태**: ... 대기" 같은 정형 포맷뿐 아니라, 자유 서술("항목이 (판단 필요) 이고
# ... 코드는 건드리지 않았다", "재확인: 코드 변경 없음", "결정 전이라 미수정")도 잡는다 —
# 모델이 매번 다른 문장으로 "아직 결정 안 났다"를 적어서 고정 포맷만 보면 놓친다
# (AUD-0eeb77·10007c 는 같은 미해결 결정을 각각 9·5번 반복해 재시도만 하다 끝났다).
_PENDING = re.compile(
    r"사용자 (결정|확인|선택).{0,8}(대기|후 진행)"
    r"|코드는? (건드리지 않았다|변경 없음)"
    r"|scope 파일.{0,6}미수정"
    r"|결정 전이라 미수정"
    r"|결정이? (아직 없다|여전히 없다|안 났다)"
)
# 같은 ID를 다시 언급하며 실제로 결정이 확정됐다고 적은 경우 — 이게 섹션 중 가장 나중에
# 나오면 그 이전 섹션들의 PENDING 여부는 무시한다(사람이 이미 답했다는 뜻).
_RESOLVED = re.compile(r"사용자 확정|결정 확정|사용자가 (A|B|C|\d)안|승인됨")


def _sections(decisions_md: str) -> list[tuple[list[str], str]]:
    """## 또는 ### [ID, ID...] 제목 단위로 쪼갠다. 본문은 다음 헤더 전까지."""
    out: list[tuple[list[str], str]] = []
    cur_ids: list[str] = []
    cur_lines: list[str] = []
    for ln in decisions_md.splitlines():
        m = _HEAD.match(ln)
        if m:
            if cur_ids:
                out.append((cur_ids, "\n".join(cur_lines)))
            cur_ids = [x for x in re.split(r"[,\s]+", m.group(1)) if x.startswith("AUD-")]
            cur_lines = [ln]
        else:
            cur_lines.append(ln)
    if cur_ids:
        out.append((cur_ids, "\n".join(cur_lines)))
    return out


def latest_statuses(decisions_md: str) -> dict[str, str]:
    """ID → 가장 마지막(최신) "**상태**:" 줄 (정형 포맷 전용, 레거시 호환용으로 유지)."""
    out: dict[str, str] = {}
    for ids, body in _sections(decisions_md):
        for ln in body.splitlines():
            m = _STATUS.search(ln)
            if m:
                for iid in ids:
                    out[iid] = m.group(1).strip()
    return out


def pending_ids(decisions_md: str) -> dict[str, str]:
    """ID → 아직 결정 안 난 걸로 보이는 마지막 섹션의 앞부분(사람이 읽을 근거).
    섹션을 순서대로 보며, PENDING 이면 미결로 표시하고 RESOLVED 가 나오면 지운다."""
    out: dict[str, str] = {}
    for ids, body in _sections(decisions_md):
        if _RESOLVED.search(body):
            for iid in ids:
                out.pop(iid, None)
            continue
        if _PENDING.search(body):
            snippet = next((ln for ln in body.splitlines() if _PENDING.search(ln)), body.splitlines()[0] if body else "")
            for iid in ids:
                out[iid] = snippet.strip()[:80]
    return out


def find_mismatches(backlog_path: Path, decisions_path: Path) -> list[str]:
    """stage 가 DECISIONS.md 가 말하는 결정 상태와 안 맞는 항목들을 사람이 읽을 설명으로 반환."""
    items = {it.item_id: it for it in queue.parse(backlog_path)}
    text = decisions_path.read_text(encoding="utf-8") if decisions_path.exists() else ""
    problems = []
    for iid, snippet in pending_ids(text).items():
        it = items.get(iid)
        if it is None or it.stage == "needs_decision":
            continue
        problems.append(f"{iid}: DECISIONS.md=\"{snippet}\" 인데 stage={it.stage} (needs_decision 이어야 함)")
    return problems

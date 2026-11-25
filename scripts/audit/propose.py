"""후보 → BACKLOG 제안 — 확인된 후보를 자체 승인(queued)/사용자 결정(needs_decision)으로 나눠 큐에 추가한다(설계 단계의 쓰기부)."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from scripts.audit import agents, decisions, triage
from scripts.autopilot import queue

PENDING_PATH = Path(".claude/autopilot/pending_decisions.md")


def propose(findings: list[dict], path: Path, decide=None, tiers: dict | None = None, limit: int | None = None) -> list[str]:
    """확인된 후보를 BACKLOG 끝에 제안한다(이미 있으면 건너뜀). 새 항목 ID 목록 반환.

    decide(finding)→triage 결과가 auto 면 stage=queued(scope·verify 채움, 자체 승인), 아니면 needs_decision(사람 결정)
    + 결정 보고서를 PENDING_PATH 에 추가. decide 가 없으면 전부 needs_decision. tiers 에 {id: tier} 를 채운다.
    항목마다 즉시 기록(중간에 끊겨도 재진입 시 이어짐), limit 이면 새 항목을 그 수까지만 처리한다.
    열린 단위의 텍스트에 "(커버: kind)" 가 있으면 같은 kind 후보는 중복으로 보고 제안하지 않는다.
    """
    items = queue.parse(path)
    have = {it.item_id for it in items}
    covered = {m for it in items if it.stage not in ("done", "needs_decision", "failed") for m in re.findall(r"\(커버: ([\w,\- ]+)\)", it.text)
               for m in re.split(r"[, ]+", m) if m}
    new = []
    for f in findings:
        if limit is not None and len(new) >= limit:
            break
        if f["kind"] in covered:
            continue
        ln = agents.backlog_lines([f])[0]
        iid = "AUD-" + hashlib.sha1(ln.encode()).hexdigest()[:6]
        if iid in have:
            continue
        reports, recs = [], []
        d = decide(f) if decide else {"tier": "user", "why": "등급 분류 미사용", "design": {}}
        meta = {"stage": "queued" if d["tier"] == "auto" else "needs_decision", "mode": "auto", "attempts": 0, "deps": [],
                "kind": "code"}
        if f.get("critical"):
            meta["critical"] = True
        if d["tier"] == "auto":
            meta.update(scope=d["design"]["scope"], verify=d["design"]["verify"], summary=d["design"].get("summary", ""), auto_approved=True)
        else:
            reports.append(f"## {iid}\n" + triage.report(f, d))
            recs.append(decisions.build(iid, f, d))
        new.append(iid)
        if tiers is not None:
            tiers[iid] = d["tier"]
        with path.open("a", encoding="utf-8") as fh:
            fh.write("\n" + f"- **[{iid}]** {ln[2:]}\n  <!-- autopilot: {json.dumps(meta, ensure_ascii=False)} -->" + "\n")
        decisions.append(recs)
        if reports:
            PENDING_PATH.parent.mkdir(parents=True, exist_ok=True)
            with PENDING_PATH.open("a", encoding="utf-8") as fh:
                fh.write("\n".join(reports) + "\n")
    return new

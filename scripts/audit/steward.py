"""비전 청지기(S5) — 버전 계획 직전에 VISION.md 개정을 '제안'만 한다. 쓰는 곳은 vision-proposals/<버전>.md 와 결정 레코드(VIS-<버전>) 뿐.

반영은 사용자가 결정 A(채택)를 고를 때만 — VISION.md 를 새 본문으로 교체하고 이전 본문은 vision-proposals/<버전>.prev.md 로 보존한다.
루프는 이 결정을 기다리지 않는다(비차단). 제안 없음("변경 없음")이면 아무것도 쓰지 않는다.
"""
from __future__ import annotations

from pathlib import Path

from scripts.audit import agents, decisions, docs_ctx, planner, release_plan, versioning
from scripts.audit.triage import _json

_PROMPT = """너는 비전 청지기다. 아래 VISION 과 직전 버전 회고를 읽고, 개정이 정말 필요할 때만 제안하라. 코드·다른 문서는 건드리지 마라.
변경이 필요 없으면 {"change":false}. 필요하면 {"change":true,"reason":"왜 바꾸나(증거 포함)","new_vision":"개정된 VISION 본문 전체(헤더 제외)"}
JSON 한 개만 출력."""
_MIN = 80


def proposal_path(ver: str, root: Path | None = None) -> Path:
    return (root or docs_ctx.RELEASES) / "vision-proposals" / f"{ver}.md"


def parse(text: str) -> dict | None:
    d = _json(text)
    body = str(d.get("new_vision", "")).strip()
    if d.get("change") is not True or len(body) < _MIN or not str(d.get("reason", "")).strip():
        return None
    return {"reason": str(d["reason"]).strip(), "new_vision": body}


def step(*, ask=agents.ask, root: Path | None = None, dpath: Path | None = None, plan_path: Path | None = None) -> str:
    """제안 한 건 생성(버전당 1회). 결과 한 줄."""
    ver = planner.next_version(release_plan.current(release_plan.load(plan_path)))
    pp = proposal_path(ver, root)
    if pp.exists() or any(r["id"] == f"VIS-{ver}" for r in decisions.load(dpath)):
        return f"{ver} 비전 제안 이미 있음"
    prop = parse(ask(docs_ctx.augment(_PROMPT, "steward"), "opus", "Read,Grep,Glob"))
    if prop is None:
        return f"{ver} 비전 변경 없음"
    pp.parent.mkdir(parents=True, exist_ok=True)
    pp.write_text(f"---\nstatus: proposed\n---\n# {ver} 비전 개정 제안\n\n## 사유\n{prop['reason']}\n\n## 새 본문\n{prop['new_vision']}\n", encoding="utf-8")
    d = {"design": {"summary": f"{ver} 비전 개정 제안 — {prop['reason'][:80]}", "recommendation": "A — 검토 후 채택",
                    "options": [{"name": "채택", "pros": "VISION.md 갱신(이전본 보존)", "cons": "이후 감사·기획이 새 비전을 따른다"},
                                {"name": "기각", "pros": "현행 비전 유지", "cons": "-"}]},
         "why": prop["reason"]}
    rec = decisions.build(f"VIS-{ver}", {"kind": "vision", "impact": "VISION.md"}, d)
    rec["scope"] = [str(pp.relative_to(docs_ctx.ROOT)) if docs_ctx.ROOT in pp.parents else str(pp)]
    decisions.append([rec], dpath)
    return f"{ver} 비전 개정 제안 — 결정 대기(비차단)"


def _supersede_planned(*, dpath: Path | None, plan_path: Path | None, root: Path | None) -> list[str]:
    """새 비전 이전에 제안된 미승인(planned) 버전과 그 승인 대기 결정(VER-*)을 걷어낸다 — plan 단계가 새 비전으로 다시 제안한다. 진행 중 버전은 건드리지 않는다."""
    plan = release_plan.load(plan_path)
    gone = [v for v, x in plan["versions"].items() if x.get("status") == "planned"]
    if not gone:
        return []
    for v in gone:
        del plan["versions"][v]
        versioning.set_doc_status((root or docs_ctx.RELEASES) / v / "PLAN.md", "superseded")
    release_plan.save(plan, plan_path)
    ids = {f"VER-{v}" for v in gone}
    decisions.save([r for r in decisions.load(dpath) if r["id"] not in ids], dpath)
    return gone


def apply_choice(rec: dict, *, dpath: Path | None = None, root: Path | None = None, plan_path: Path | None = None) -> str:
    """kind=vision 결정 반영 — A 면 VISION.md 교체(이전본 보존)·미승인 버전 제안 폐기(재기획), 아니면 기각. 레코드는 applied."""
    ver = rec["id"].removeprefix("VIS-")
    data = decisions.load(dpath)
    for r in data:
        if r["id"] == rec["id"]:
            r["status"] = "applied"
    decisions.save(data, dpath)
    if rec.get("choice") != "A":
        return f"{ver} 비전 제안 기각"
    pp, vp = proposal_path(ver, root), (root or docs_ctx.RELEASES) / "VISION.md"
    try:
        body = pp.read_text(encoding="utf-8").split("## 새 본문\n", 1)[1].strip()
        old = vp.read_text(encoding="utf-8")
    except (OSError, IndexError):
        return f"{ver} 비전 제안 문서 없음 — 반영 못함"
    head = "\n".join(ln for ln in old.splitlines() if ln.startswith(("#", ">")))
    pp.with_suffix(".prev.md").write_text(old, encoding="utf-8")
    vp.write_text(head + "\n\n" + body + "\n", encoding="utf-8")
    docs = pp.read_text(encoding="utf-8").replace("status: proposed", "status: applied", 1)
    pp.write_text(docs, encoding="utf-8")
    gone = _supersede_planned(dpath=dpath, plan_path=plan_path, root=root)
    return f"{ver} 비전 개정 반영(이전본 보존)" + (f" — 옛 비전 기준 제안 {', '.join(gone)} 폐기, 다음 계획 단계에서 재제안" if gone else "")

"""이니셔티브 설계자(S4) — 승인된 vN 이니셔티브마다 DESIGN.md 를 쓰고 개발 항목을 BACKLOG 에 추가·연결한다.

가드: 항목은 scope(저장소 안 경로)와 실행 가능한 verify 를 가져야 한다. 설계자는 DESIGN.md 와 BACKLOG 항목만 쓴다(코드·VISION 금지).
이니셔티브 status: approved → designed. 설계할 이니셔티브가 없으면 phase=audit 으로 돌아가 일반 감사 루프(개발·결함 감사)로 이어진다.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.audit import agents, docs_ctx, release_plan
from scripts.audit.triage import _json
from scripts.audit.vision import VISION
from scripts.autopilot import queue, settings

ROOT = Path(__file__).resolve().parents[2]
MAX_ITEMS = 6
_PROMPT = VISION + """

너는 설계자다. 이니셔티브 %s(%s) 를 개발 항목으로 나눠라. 코드는 쓰지 말고 JSON 한 개만 출력.
항목 하나는 한 번의 개발 단위(파일 몇 개)로 끝나야 하고, scope 는 건드릴 파일 경로, verify 는 성공 판정 셸 커맨드다.
{"design":"설계 본문(마크다운, 접근·대안·위험)","items":[{"text":"항목 설명","scope":["src/x.py"],"verify":["pytest tests/test_x.py"]}]}"""


def valid_item(it: dict, root: Path = ROOT) -> bool:
    scope = [s for s in it.get("scope", []) if isinstance(s, str) and s]
    ok_scope = scope and all(".." not in Path(s).parts and not Path(s).is_absolute() for s in scope)
    return bool(it.get("text") and ok_scope and [v for v in it.get("verify", []) if isinstance(v, str) and v.strip()])


def parse(text: str) -> tuple[str, list[dict]]:
    d = _json(text)
    items = [i for i in d.get("items", []) if isinstance(i, dict) and valid_item(i)] if isinstance(d.get("items"), list) else []
    return str(d.get("design", "")).strip(), items[:MAX_ITEMS]


def undesigned(plan: dict) -> list[str]:
    return [i for i, ini in release_plan.initiatives(plan).items() if ini.get("status") == "approved" and i != release_plan.MAINT]


def write_design(ver: str, ini_id: str, ini: dict, body: str, releases: Path | None = None) -> Path:
    doc = (releases or docs_ctx.RELEASES) / ver / "initiatives" / ini_id / "DESIGN.md"
    doc.parent.mkdir(parents=True, exist_ok=True)
    head = f"---\nstatus: designed\n---\n# {ini_id} — {ini.get('title', '')}\n\n- 목표: {ini.get('goal', '')}\n"
    doc.write_text(head + "- 완료 기준: " + " ; ".join(f"`{v}`" for v in ini.get("verify", [])) + "\n\n" + body + "\n", encoding="utf-8")
    return doc


def add_items(ini_id: str, items: list[dict], plan: dict, qpath: Path) -> list[str]:
    """BACKLOG 에 queued·auto 항목으로 추가하고 이니셔티브에 연결. 새 ID 목록."""
    have = {i.item_id for i in queue.parse(qpath)}
    out = []
    for it in items:
        iid = "INI-" + hashlib.sha1(f"{ini_id}|{it['text']}".encode()).hexdigest()[:6]
        if iid in have:
            continue
        meta = {"stage": "queued", "mode": "auto", "attempts": 0, "deps": [], "kind": "code",
                "scope": it["scope"], "verify": it["verify"], "auto_approved": True}
        with qpath.open("a", encoding="utf-8") as fh:
            fh.write(f"\n- **[{iid}]** [{ini_id}] {it['text']}\n  <!-- autopilot: {json.dumps(meta, ensure_ascii=False)} -->\n")
        release_plan.link(plan, ini_id, iid)
        out.append(iid)
    return out


def design_step(st: dict, *, ask=agents.ask, plan_path: Path | None = None, qpath: Path | None = None,
                releases: Path | None = None) -> str:
    """idesign 단계 한 칸 — 이니셔티브 하나를 설계. 남은 게 없으면 감사 단계로."""
    plan = release_plan.load(plan_path)
    todo = undesigned(plan)
    if not todo:
        st.update(phase="audit", fails=0)
        return "설계할 이니셔티브 없음 — 감사 루프로"
    ver, ini_id = release_plan.current(plan), todo[0]
    ini = release_plan.initiatives(plan)[ini_id]
    body, items = parse(ask(docs_ctx.augment(_PROMPT % (ini_id, ini.get("goal", "")), "designer", ini_id), "opus", "Read,Grep,Glob"))
    if not items:
        from scripts.audit import loop
        return loop._fail(st, f"{ini_id} 설계 실패 — 가드 통과 항목 0건")
    write_design(ver, ini_id, ini, body, releases)
    new = add_items(ini_id, items, plan, qpath or settings.QUEUE_PATH)
    ini["status"] = "designed"
    release_plan.save(plan, plan_path)
    st["fails"] = 0
    return f"{ini_id} 설계 완료 — 개발 항목 {len(new)}건 추가"

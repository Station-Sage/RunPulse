"""버전 기획자(S3) — 안정화 게이트 통과 후 다음 버전(vN+1)의 이니셔티브 제안을 만들고 사용자 결정(kind=initiative)을 요청한다.

가드: 이니셔티브는 ① 원칙 번호 ② 증거(path:line + 그 줄에 실제 존재하는 인용) ③ 금칙어 없는 목표 ④ 실행 가능한 완료 기준(verify)을 모두 가져야 통과한다.
산출: v0.3/data/releases/vN+1/PLAN.md(status: proposed) + release_plan.json(vN+1 planned, 이니셔티브 proposed) + 결정함 레코드 `VER-vN+1`.
기획자는 코드·VISION 을 쓰지 않는다. 호출 뒤 AWAIT_DECISION 으로 멈추고, 승인 반영은 consume 이 한다.
"""
from __future__ import annotations

import re
from pathlib import Path

from scripts.audit import agents, decisions, docs_ctx, release_plan, stopreason
from scripts.audit.triage import _json
from scripts.audit.vision import VISION

ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN = ("전반적", "다양한", "고도화", "최적화", "개선 필요", "사용성 향상", "품질 향상")
_SLUG = re.compile(r"^INI-[a-z0-9][a-z0-9-]*$")
_EVID = re.compile(r"^(?P<p>[^:\s]+):(?P<n>\d+)$")
_PROMPT = VISION + """

너는 버전 기획자다. 안정화된 현재 버전 다음(%s)에 할 이니셔티브를 3~5개 제안하라. 코드는 쓰지 말고 JSON 한 개만 출력.
각 이니셔티브는 '러너가 지금 앱에서 답을 못 얻는 질문' 하나를 해결해야 하고, 기존 이니셔티브를 확장(extend)하는지 신규(new)인지 밝혀라.
evidence 는 실제 코드의 path:line 과 그 줄에 있는 문자열 일부(quote)여야 한다. 막연한 표현(전반적·다양한·고도화·최적화)은 금지.
verify 는 단독 실행 가능한 명령(존재하는 스크립트·인자 불필요)만, 부재 검사는 `! grep -rn 좁은패턴 경로` 로 쓴다.
{"title":"버전 제목","initiatives":[{"id":"INI-slug","title":"","kind":"extend|new","principle":1,"question":"러너가 못 얻는 답",
 "goal":"한 줄 목표","evidence":[{"path":"src/x.py:12","quote":"그 줄의 일부"}],"verify":["완료 기준 셸 커맨드"]}],
 "goal":"이 버전의 제품 목표 한 줄","phases":[{"id":"단계 식별자(예: P1 또는 로마숫자, 자유)","title":"그 단계가 이루는 것","initiatives":["INI-slug"]}],
 "gaps":"이 제안이 다루지 못하는 영역(누락 검토)"}
phases 는 이니셔티브를 진행 순서대로, 이 버전의 성격에 맞는 개수·이름의 단계로 묶는다(개수·식별자는 정해진 것이 없고, 이니셔티브가 적으면 1단계도 가능). 모든 이니셔티브는 정확히 한 단계에 속해야 한다."""


def next_version(cur: str) -> str:
    m = re.fullmatch(r"v(\d+)", cur)
    return f"v{int(m.group(1)) + 1}" if m else f"{cur}-next"


def evidence_ok(ev: dict, root: Path = ROOT) -> bool:
    """path:line 의 그 줄에 quote 가 실제로 있어야 한다(저장소 밖 경로 금지)."""
    m = _EVID.match(str(ev.get("path", "")))
    quote = str(ev.get("quote", "")).strip()
    if not m or not quote:
        return False
    p = (root / m["p"]).resolve()
    if root.resolve() not in p.parents:
        return False
    try:
        lines = p.read_text(encoding="utf-8").splitlines()
    except OSError:
        return False
    n = int(m["n"])
    return 1 <= n <= len(lines) and quote in lines[n - 1]


def valid_initiative(ini: dict, root: Path = ROOT) -> str | None:
    """가드 위반 사유(통과면 None)."""
    if not _SLUG.match(str(ini.get("id", ""))):
        return "id 형식"
    if ini.get("principle") not in range(1, 9):
        return "원칙 번호"
    text = f"{ini.get('goal', '')} {ini.get('question', '')} {ini.get('title', '')}"
    if not ini.get("question") or not ini.get("goal") or any(w in text for w in FORBIDDEN):
        return "목표·질문 누락 또는 금칙어"
    if not any(evidence_ok(e, root) for e in ini.get("evidence", []) if isinstance(e, dict)):
        return "증거 불일치"
    if not [v for v in ini.get("verify", []) if isinstance(v, str) and v.strip()]:
        return "완료 기준 없음"
    return None


def parse(text: str, root: Path = ROOT) -> tuple[dict, list[str]]:
    """응답 → ({title, initiatives(통과분), gaps}, 탈락 사유 목록)."""
    d = _json(text)
    ok, dropped = [], []
    for ini in d.get("initiatives", []) if isinstance(d.get("initiatives"), list) else []:
        if not isinstance(ini, dict):
            continue
        why = valid_initiative(ini, root)
        if why:
            dropped.append(f"{ini.get('id', '?')}: {why}")
        else:
            ok.append(ini)
    return {"title": str(d.get("title", ""))[:80], "initiatives": ok, "gaps": str(d.get("gaps", ""))[:300],
            "goal": str(d.get("goal", ""))[:200], "phases": _phases(d.get("phases"), {i["id"] for i in ok})}, dropped


def _phases(raw, ids: set[str]) -> list[dict]:
    """통과한 이니셔티브만 남긴 단계 목록 — 어느 단계에도 없는 이니셔티브는 마지막 단계(없으면 새 단계 하나)에 붙인다."""
    out = []
    for p in raw if isinstance(raw, list) else []:
        if isinstance(p, dict) and p.get("title"):
            mine = [i for i in p.get("initiatives", []) if i in ids and not any(i in q["initiatives"] for q in out)]
            out.append({"id": str(p.get("id") or len(out) + 1)[:6], "title": str(p["title"])[:60], "initiatives": mine})
    rest = [i for i in sorted(ids) if not any(i in q["initiatives"] for q in out)]
    if rest:
        if out:
            out[-1]["initiatives"] += rest
        else:
            out = [{"id": "1", "title": "전체", "initiatives": rest}]
    return [q for q in out if q["initiatives"]]


def render_plan(ver: str, prop: dict) -> str:
    out = ["---", "status: proposed", "---", f"# {ver} — {prop['title'] or '제안'}", ""]
    if prop.get("goal"):
        out += ["## 제품 목표", prop["goal"], ""]
    if prop.get("phases"):
        out += ["## 단계"] + [f"- {p['id']}. {p['title']}: " + ", ".join(p["initiatives"]) for p in prop["phases"]] + [""]
    out += ["## 이니셔티브"]
    for i in prop["initiatives"]:
        ev = ", ".join(f"`{e['path']}` “{e['quote']}”" for e in i["evidence"] if isinstance(e, dict))
        out += [f"### {i['id']} — {i.get('title', '')} ({i.get('kind', 'new')}, 원칙 {i['principle']})",
                f"- 질문: {i['question']}", f"- 목표: {i['goal']}", f"- 증거: {ev}",
                "- 완료 기준: " + " ; ".join(f"`{v}`" for v in i["verify"]), ""]
    out += ["## 범위 밖·누락 검토", prop["gaps"] or "-", ""]
    return "\n".join(out)


def apply_proposal(ver: str, prop: dict, plan_path: Path | None = None, root: Path | None = None) -> Path:
    """PLAN.md 초안과 release_plan.json 의 vN+1(planned, 이니셔티브 proposed)을 쓴다."""
    doc = (root or docs_ctx.RELEASES) / ver / "PLAN.md"
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_text(render_plan(ver, prop), encoding="utf-8")
    plan = release_plan.load(plan_path)
    plan["versions"][ver] = {"title": prop["title"] or ver, "status": "planned", "goal": prop.get("goal", ""),
                             "phases": prop.get("phases", []), "initiatives": {
        i["id"]: {"title": i.get("title", i["id"]), "status": "proposed", "items": [], "goal": i["goal"], "verify": i["verify"]}
        for i in prop["initiatives"]}}
    release_plan.save(plan, plan_path)
    return doc


def decision_record(ver: str, prop: dict) -> dict:
    names = ", ".join(i["id"] for i in prop["initiatives"])
    d = {"design": {"summary": f"{ver} 이니셔티브 제안: {names}" + (f" — 목표: {prop['goal']}" if prop.get("goal") else "") + "".join(f" / {p['id']}. {p['title']}" for p in prop.get("phases", [])), "recommendation": "A — 제안 범위 그대로 승인",
                    "options": [{"name": "승인", "pros": "다음 버전 설계·개발 착수", "cons": "범위가 고정된다"},
                                {"name": "보류", "pros": "추가 감사·논의 가능", "cons": "버전 진행이 멈춘다"}]},
         "why": f"안정화 게이트 통과 — 누락 검토: {prop['gaps'] or '-'}"}
    rec = decisions.build(f"VER-{ver}", {"kind": "initiative", "impact": prop["title"]}, d)
    rec["scope"] = [f"v0.3/data/releases/{ver}/PLAN.md"]
    return rec


def plan(st: dict, *, ask=agents.ask, root: Path = ROOT, dpath: Path | None = None, plan_path: Path | None = None) -> str:
    """plan 단계 한 칸 — 제안 생성 → 가드 → 문서·결정 레코드 → AWAIT_DECISION. 이미 같은 버전 결정이 열려 있으면 다시 묻지 않는다."""
    ver = next_version(release_plan.current(release_plan.load(plan_path)))
    if any(r["id"] == f"VER-{ver}" and r["status"] in ("open", "chosen") for r in decisions.load(dpath)):
        stopreason.stop(st, stopreason.AWAIT_DECISION)
        return f"{ver} 제안 결정 대기 중"
    prop, dropped = parse(ask(docs_ctx.augment(_PROMPT % ver, "planner"), "opus", "Read,Grep,Glob"), root)
    if not prop["initiatives"]:
        stopreason.stop(st, stopreason.AWAIT_DECISION)
        return f"{ver} 제안 실패 — 가드 통과 이니셔티브 0건({'; '.join(dropped) or '응답 파싱 실패'}). 직접 지시 필요"
    apply_proposal(ver, prop, plan_path, root / "v0.3" / "data" / "releases" if root != ROOT else None)
    decisions.append([decision_record(ver, prop)], dpath)
    stopreason.stop(st, stopreason.AWAIT_DECISION)
    return f"{ver} 이니셔티브 {len(prop['initiatives'])}건 제안(탈락 {len(dropped)}) — 사용자 결정 대기"

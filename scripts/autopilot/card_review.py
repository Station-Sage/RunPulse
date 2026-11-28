"""결정 카드(split_decision·verify_decision) 에이전트 검토 — 카드를 처음 열 때 한 번만 읽기 전용 에이전트가 검토안·안별 검토·추천을 쓴다.

실패(타임아웃·파싱 불가·키 불일치)면 규칙 기반 값을 그대로 두고 review_source=rule(규칙 기반 추정), 성공이면 agent.
페이싱·예산 대기(PacingHold)는 표시만 남기고 다음 기회에 다시 시도한다. 추천은 제안일 뿐 자동 적용하지 않는다.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

KINDS = ("split_decision", "verify_decision")
MODEL = "sonnet"

_OUT = ('JSON 한 개만 출력한다(설명·코드펜스 금지): {"review": "카드 전체 검토 2~4문장", "options": {"<key>": "그 안의 근거 1~2문장"}, '
        '"recommendation": "<추천 key>", "recommend_why": "추천 이유 1~2문장"%s}')


def _prompt(rec: dict) -> str:
    opts = "\n".join(f"- {o['key']}. {o['name']} (+{o.get('pros', '')} / -{o.get('cons', '')})" for o in rec.get("options", []))
    if rec["kind"] == "split_decision":
        path = rec.get("path", "")
        return (f"RunPulse 저장소의 {path} 파일({rec.get('lines', '?')}줄)이 300줄 상한을 넘었다. 파일을 Read 로 읽고 분리가 실제로 이득인지 판단하라.\n"
                "기준: 책임이 섞였는가, 응집된 덩어리로 나눌 경계가 있는가, 계속 커지는 중인가, 분리 시 회귀 위험은 어떤가. 초과폭만으로 판단하지 말 것.\n"
                f"선택지:\n{opts}\n" + _OUT % ', "split_plan": "분리를 추천할 때만: 어떤 함수·블록을 어떤 새 파일로 옮길지 구체적으로(3~6줄), 아니면 빈 문자열"')
    return ("RunPulse 자동 개발 항목의 verify 단계가 실패했다. 실패 맥락을 읽고 원인과 가장 근본적인 해결 선택지를 판단하라(필요하면 Read/Grep 으로 파일 확인).\n"
            f"항목: {rec.get('finding', {}).get('impact', '')}\n진단: {rec.get('diag', '')}\n실패 출력:\n{rec.get('why', '')}\n"
            f"선택지:\n{opts}\n" + _OUT % "")


def parse(text: str, keys: list[str]) -> dict | None:
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except ValueError:
        return None
    if not isinstance(d, dict) or d.get("recommendation") not in keys or not str(d.get("review", "")).strip():
        return None
    opts = d.get("options") if isinstance(d.get("options"), dict) else {}
    return {"review": str(d["review"]).strip()[:800], "options": {k: str(v).strip()[:400] for k, v in opts.items() if k in keys},
            "recommendation": d["recommendation"], "recommend_why": str(d.get("recommend_why", "")).strip()[:400],
            "split_plan": str(d.get("split_plan", "")).strip()[:1200]}


def review(rec: dict, ask=None, root: Path | None = None) -> dict:
    """rec 를 제자리에서 갱신한다. 이미 review_source 가 있으면 건드리지 않는다. 반환: {"source": agent|rule|pending}."""
    from scripts.audit import agents
    if rec.get("kind") not in KINDS:
        return {"source": "none"}
    if rec.get("review_source"):
        return {"source": rec["review_source"]}
    ask = ask or agents.ask
    try:
        out = ask(_prompt(rec), MODEL, "Read,Grep")
    except agents.PacingHold:
        return {"source": "pending"}
    except Exception:
        out = ""
    res = parse(out, [o["key"] for o in rec.get("options", [])])
    if res is None:
        rec["review_source"] = "rule"
        return {"source": "rule"}
    rec.update(review=res["review"], recommendation=res["recommendation"], recommend_why=res["recommend_why"], review_source="agent")
    for o in rec["options"]:
        if res["options"].get(o["key"]):
            o["review"] = res["options"][o["key"]]
    if res["split_plan"]:
        rec["split_plan"] = res["split_plan"]
    return {"source": "agent"}

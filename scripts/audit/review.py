"""독립 검토 게이트(P5) — 관점 에이전트가 real 로 본 후보를 다른 모델이 반증 시도로 재검토한다.

작성자(관점 모델)와 다른 모델을 쓰고(REVIEW_MODEL), 증거(셀 노트)만 주어 'confirm'/'reject' 를 받는다.
confirm 만 BACKLOG 후보((판단 필요))가 된다. 응답 파싱 실패는 reject 가 아닌 unsure — 후보에서는 빠지되 기록은 남긴다.
"""
from __future__ import annotations

import json
import re

from scripts.audit.agents import ask
from scripts.audit.vision import VISION

REVIEW_MODEL = "sonnet"     # 작성자가 sonnet 이면 haiku 로 교차 — pick_model 참고
_PROMPT = VISION + """

너는 감사 결과의 독립 검토자다. 아래 후보가 실제 결함인지 반증을 시도하라(합성 DB·테스트 환경 산물이면 reject).
후보: kind=%s / 영향: %s / 제안: %s
증거(셀: 노트):
%s
JSON 한 개만 출력: {"verdict": "confirm|reject|unsure", "reason": "한 줄"}"""


def pick_model(perspective: str) -> str:
    from scripts.audit.perspectives import AUDIT_MODELS
    return "haiku" if AUDIT_MODELS.get(perspective) == "sonnet" else REVIEW_MODEL


def parse_verdict(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.S)
    try:
        d = json.loads(m.group(0)) if m else {}
    except json.JSONDecodeError:
        d = {}
    return {"verdict": d["verdict"] if d.get("verdict") in ("confirm", "reject", "unsure") else "unsure",
            "reason": str(d.get("reason", ""))[:200]}


def review(findings: list[dict], groups: dict[str, list[dict]]) -> list[dict]:
    """real 후보마다 검토 결과(review 필드)를 붙여 돌려준다. real 이 아닌 항목은 그대로."""
    out = []
    for f in findings:
        if f.get("verdict") != "real":
            out.append(f)
            continue
        ev = "\n".join(f"{g['cell']}: {g['note'][:120]}" for g in groups.get(f["kind"], [])[:6]) or "(증거 없음)"
        text = ask(_PROMPT % (f["kind"], f.get("impact", ""), f.get("fix", ""), ev), pick_model(f.get("perspective", "")))
        out.append({**f, "review": parse_verdict(text)})
    return out


def confirmed(findings: list[dict]) -> list[dict]:
    return [f for f in findings if f.get("verdict") == "real" and f.get("review", {}).get("verdict") == "confirm"]

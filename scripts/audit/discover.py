"""발견 감사 — 도구(Read/Grep/Glob)로 코드·화면을 직접 보고 비전 기준의 새 개선 후보를 찾는다(기계 감지가 못 보는 결함).

도구를 쓰는 호출은 비싸서 라운드당 상한(settings.AUDIT_TOOL_CALLS_PER_ROUND, tunables.json 으로 조정)을 둔다.
이미 보고된 이슈(known.render)를 프롬프트에 넣어 같은 지적을 반복하지 않게 한다. 결과는 기존 findings 형식과 같다.
"""
from __future__ import annotations

import json
from pathlib import Path

from scripts.audit import agents, docs_ctx, inventory, known
from scripts.audit.vision import VISION
from scripts.autopilot import settings

BUDGET_PATH = inventory.LEDGER_PATH.parent / "discover_budget.json"
TOOLS = "Read,Grep,Glob"
THEMES = {
    "evidence": "결론·수치마다 근거(출처·계산식)가 화면에서 드러나는지, 드릴다운 경로가 끊긴 곳.",
    "flow": "러너가 '오늘 무엇을 해야 하나'에 도달하는 흐름에서 막히거나 중복·모호한 지점.",
    "gaps": "비전 원칙(Provider Transparency·Quiet Data·State-Bound Plan) 대비 비어 있는 기능·화면.",
}

_PROMPT = """{vision}

너는 RunPulse 의 발견 감사자다. 저장소(프런트 src/, 백엔드 src/web)를 Read/Grep/Glob 으로 직접 읽고 아래 주제로 '새' 개선 후보를 찾는다.
주제: {theme}

이미 보고된 이슈(반복 금지):
{known}

규칙: 근거 파일·라인을 확인한 것만 보고한다. 장식·소셜·라이브 추적류 제안 금지. 최대 5건. critical=true 는 데이터 손실·보안·핵심 기능 불능·잘못된 건강/훈련 수치 노출만(드물게).
출력은 JSON 배열만: [{{"kind":"...","verdict":"real","impact":"사용자 영향 한 줄","fix":"수정 방향 한 줄","critical":false,"cells":["파일:라인",...]}}]
"""


def calls_used(round_no: int, path: Path | None = None) -> int:
    try:
        d = json.loads((path or BUDGET_PATH).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return 0
    return d.get("used", 0) if d.get("round") == round_no else 0


def remaining(round_no: int, path: Path | None = None) -> int:
    return max(0, int(settings.tunable("AUDIT_TOOL_CALLS_PER_ROUND", 8)) - calls_used(round_no, path))


def _spend(round_no: int, path: Path | None = None) -> None:
    p = path or BUDGET_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"round": round_no, "used": calls_used(round_no, p) + 1}), encoding="utf-8")


def run(round_no: int, model: str = "sonnet", path: Path | None = None, known_path: Path | None = None) -> list[dict]:
    """주제별로 1회씩 호출(상한까지). 반복 지적은 filter_new 로 제거. PacingHold 는 호출자로 전파."""
    seen = known.load(known_path)
    out: list[dict] = []
    for name, theme in THEMES.items():
        if remaining(round_no, path) <= 0:
            break
        _spend(round_no, path)
        prompt = docs_ctx.augment(_PROMPT.format(vision=VISION, theme=theme, known=known.render(seen)), "auditor")
        out += [{**f, "perspective": f"discover:{name}"} for f in agents.parse_findings(agents.ask(prompt, model, tools=TOOLS))]
    return known.filter_new(out, seen)

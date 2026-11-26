"""develop 단계 실패 처리 — failed 사유 분류·결정 요청(asked) 카드 변환·답변 반영 지시문.

모델이 DECISIONS.md 에 새 질문을 쓴 것은 실패가 아니라 사용자 질문이다 → 카드(pending_decisions)로 올린다.
설계: v0.3/data/phase-7-ui-renewal/DESIGN-AUDIT-FAILED-HANDLING.md
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

from scripts.audit import decisions

ASK_LIMIT = 2
DEFAULT_VERIFY = ".venv/bin/python -m pytest tests/ -q"
DECISIONS_DIR = Path("v0.3") / "data" / "phase-7-ui-renewal"
SYSTEM_OPTIONS = (
    {"action": "already_done", "name": "이미 구현됨 → 완료 처리", "pros": "개발 없이 항목을 닫는다", "cons": "실제로 구현돼 있지 않으면 누락된다"},
    {"action": "dropped", "name": "폐기", "pros": "큐에서 영구히 내린다", "cons": "해당 작업은 하지 않는다"},
    {"action": "redefine", "name": "항목 재정의 후 진행", "pros": "의견 텍스트가 새 지시(scope)가 된다", "cons": "의견이 모호하면 다시 질문될 수 있다"},
)
_HEAD = re.compile(r"^##\s*\[([^\]]+)\]\s*(.*)$")
_OPT = re.compile(r"^\s+(\d+)[.)]\s+(.*\S)")
_FIELD = re.compile(r"^-\s*\*\*([^*]+)\*\*\s*:?\s*(.*)$")


def classify_verify(rc: int | None, output: str) -> str:
    """verify 실패 출력 → 'env'(명령/pytest 부재) 또는 'verify'."""
    if rc == 127 or "No module named pytest" in output or "command not found" in output:
        return "env"
    return "verify"


def added_text(worktree: Path) -> str:
    """DECISIONS.md 의 미커밋 추가분(+ 줄)만 이어 붙인다."""
    r = subprocess.run(["git", "diff", "-U0", "--", "DECISIONS.md"], cwd=worktree / DECISIONS_DIR,
                       capture_output=True, text=True)
    return "\n".join(ln[1:] for ln in r.stdout.splitlines() if ln.startswith("+") and not ln.startswith("+++"))


def parse_sections(text: str) -> list[dict]:
    """`## [id] 제목` 섹션 → {id,title,background,question,options[],recommendation}."""
    out: list[dict] = []
    cur: dict | None = None
    in_opts = False
    for ln in text.splitlines():
        m = _HEAD.match(ln)
        if m:
            cur = {"id": m.group(1).strip(), "title": m.group(2).strip(), "background": "", "question": "",
                   "options": [], "recommendation": ""}
            out.append(cur)
            in_opts = False
            continue
        if cur is None:
            continue
        f = _FIELD.match(ln)
        if f:
            label, val = f.group(1).strip(), f.group(2).strip()
            in_opts = label.startswith("선택지")
            if label.startswith("배경"):
                cur["background"] = val
            elif label.startswith("질문"):
                cur["question"] = val
            elif label.startswith("권고"):
                cur["recommendation"] = val
            continue
        o = _OPT.match(ln)
        if o and in_opts:
            cur["options"].append(o.group(2).strip())
    return out


def pick_section(sections: list[dict], item_id: str) -> dict | None:
    """항목 id 와 일치하는 섹션 우선, 없으면 마지막(모델이 앞 섹션을 건드린 경우 대비)."""
    return next((s for s in sections if s["id"] == item_id), sections[-1] if sections else None)


def _model_options(sec: dict | None) -> list[dict]:
    names = sec["options"] if sec and sec["options"] else []
    return [{"name": n, "pros": "", "cons": "", "action": "scope"} for n in names]


def build_asked_card(item_id: str, sec: dict | None, item_text: str, asks: int) -> dict:
    """질문 카드 — 모델 선택지 + 시스템 공통 선택지. 권고는 '권고: N번' 의 번호를 옵션 key 로 옮긴다."""
    opts = _model_options(sec) + [dict(o) for o in SYSTEM_OPTIONS]
    for i, o in enumerate(opts):
        o["key"] = chr(65 + i)
    rec_n = re.search(r"\d+", sec["recommendation"]) if sec else None
    rec = chr(64 + int(rec_n.group())) if rec_n and 0 < int(rec_n.group()) <= len(_model_options(sec)) else ""
    title = sec["title"] if sec and sec["title"] else item_text[:80]
    why = " ".join(x for x in ((sec or {}).get("background", ""), (sec or {}).get("question", "")) if x)
    rec_d = decisions.build(item_id, {"kind": "asked", "impact": item_text[:120], "fix": ""},
                            {"why": why[:600], "design": {"summary": f"{item_id} 개발 중 결정 요청 — {title}"[:200]}})
    rec_d.update(options=opts, recommendation=rec, rounds=asks)
    return rec_d


def build_failed_card(item_id: str, kind: str, reason: str, item_text: str) -> dict:
    """failed 항목용 카드 — 종류별 선택지(3.4). sync 는 재시도 선택지가 없어 카드를 만들지 않는다."""
    table = {
        "verify": [("retry_verify", "verify 커맨드 수정 후 재시도", "의견란에 새 커맨드를 적는다"),
                   ("retry_scope", "실패 출력을 지시에 첨부하고 재시도", "모델이 실패 원인을 보고 고친다"),
                   ("dropped", "폐기", "큐에서 내린다")],
        "env": [("retry_env", f"verify 를 `{DEFAULT_VERIFY}` 로 바꿔 재시도", "시스템 python 에 pytest 가 없다(ENV-1)"),
                ("dropped", "폐기", "큐에서 내린다")],
        "exec": [("retry_exec", "재시도 (시도 횟수 초기화)", "claude 실행이 2회 연속 실패했다"),
                 ("dropped", "폐기", "큐에서 내린다")],
        "asked_loop": [("redefine", "항목 재정의 후 진행", "의견 텍스트가 새 지시가 된다"),
                       ("dropped", "폐기", "큐에서 내린다")],
    }
    rows = table.get(kind, [("dropped", "폐기", "큐에서 내린다")])
    opts = [{"key": chr(65 + i), "name": n, "pros": p, "cons": "", "action": a} for i, (a, n, p) in enumerate(rows)]
    rec = decisions.build(item_id, {"kind": f"failed_{kind}", "impact": item_text[:120], "fix": ""},
                          {"why": reason[:600], "design": {"summary": f"{item_id} 개발 실패({kind})"}})
    rec["options"] = opts
    return rec


def answered_note(item) -> str:
    """답변 완료된 결정을 프롬프트에 알린다 — 같은 질문 재작성 방지."""
    if not getattr(item, "answered", None):
        return ""
    return "\n".join(f"- 결정 [{a}] 는 답변 완료(위 지시 범위에 반영). 같은 질문을 DECISIONS.md 에 다시 쓰지 말 것." for a in item.answered)

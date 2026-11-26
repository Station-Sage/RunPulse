"""판단 등급 분류(P6) — 확인된 후보를 '자체 승인'과 '사용자 결정'으로 나눈다.

자체 승인(auto)은 네 조건을 모두 만족할 때만: ① 위험 키워드 없음 ② 설계 작성 모델이 auto 등급·범위(scope)·검증(verify)을 제시
③ scope 가 ALLOWED_SCOPE 안 ④ 작성자와 다른 모델의 교차 검토가 agree. 하나라도 어긋나면 user — 설명·선택지 장단점·추천안을
담은 결정 보고서를 만들어 사람에게 넘긴다. 응답 파싱 실패는 항상 user 쪽으로 기운다(보수적).
큰 설계(is_large: 파일 4개 이상·공용 컴포넌트·여러 라우트·설계자가 user 로 분류)는 Sonnet 초안을 Opus 가 다시 설계한다
(budget.opus_allowed 한도 안에서만 — 아니면 Sonnet 그대로). 교차 검토는 항상 작성자와 다른 모델이다.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from scripts.audit import docs_ctx
from scripts.audit.agents import ask
from scripts.audit.vision import VISION
from scripts.autopilot import verify_doctor

ROOT = Path(__file__).resolve().parents[2]

ALLOWED_SCOPE = ("frontend/src/", "frontend/tests/", "tests/", "docs/", "scripts/audit/")
RISK = re.compile(r"스키마|schema|DDL|migrat|마이그레이션|삭제|delete|drop|auth|인증|권한|결제|config|ADR|decisions|"
                  r"알고리즘|calculator|메트릭 정의|예측|개인정보|배포|deploy|API 계약|breaking", re.I)
_DESIGN = VISION + """

너는 설계자다. 아래 결함을 '증상 땜질'이 아니라 근본원인 제거 방식으로 설계하라(공통 계약·헬퍼·정적 가드로 재발 방지). 코드는 쓰지 말고 JSON 한 개만 출력.
결함: kind=%s / 영향: %s / 제안: %s
{"grade":"auto|user","summary":"한 줄 설계","scope":["수정할 파일의 순수 경로만(설명·괄호 금지)"],"verify":["검증 셸 커맨드(독립 실행 가능해야 함)"],
 "options":[{"name":"","pros":"","cons":""}],"recommendation":"추천 선택지와 이유","reason":"등급 근거"}
summary·options(name·pros·cons)·recommendation·reason 은 모두 한국어로 쓴다(코드 식별자·파일 경로만 원문 유지).
선택지가 갈려도 스스로 근거를 들어 추천안 하나를 정해 그 설계를 summary·scope 에 담아라(선택 자체는 user 사유가 아니다).
auto = frontend/src·tests 안에서 끝나고 되돌리기 쉬우며 데이터·권한·알고리즘·제품 정책을 바꾸지 않는 수정.
UI 문구·마크업·접근성·컴포넌트 구조처럼 기존 디자인 시스템 안의 판단은 auto 다.
verify 규칙: ① 인자·환경 없이 단독 실행되는 명령만(스크립트는 이미 존재하고 인자 없이 도는 것) ② verify 에 쓰는 테스트 파일은 반드시 scope 에 포함(없으면 개발자가 만든다) ③ 부재 검사는 `! grep -rn 패턴 경로` 형태이고 패턴이 정상 코드와 겹치지 않게 좁힌다.
user = 스키마·데이터·인증·예측 알고리즘·되돌릴 수 없는 제품 정책을 바꿔야만 해결되는 경우로 한정."""
_CHECK = VISION + """

너는 독립 교차 검토자다. 아래 설계를 자체 승인(사람 확인 없이 개발)해도 되는지 반증을 시도하라.
결함: %s
설계: %s
범위: %s / 검증: %s
JSON 한 개만: {"verdict":"agree|disagree|unsure","reason":"한 줄"}"""


def _json(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.S)
    try:
        d = json.loads(m.group(0)) if m else {}
    except json.JSONDecodeError:
        return {}
    return d if isinstance(d, dict) else {}


def normalize_verify(cmd: str) -> str:
    """프론트 테스트는 cwd=frontend 기준 상대경로(src/…)를 읽는다 — 루트 실행 커맨드를 frontend 기준으로 바꾼다."""
    if cmd.startswith("node --test ") and "frontend/" in cmd:
        return "cd frontend && " + cmd.replace("frontend/", "")
    return cmd


def parse_design(text: str) -> dict:
    d = _json(text)
    return {"grade": d.get("grade") if d.get("grade") in ("auto", "user") else "user",
            "summary": str(d.get("summary", ""))[:300],
            "scope": [s for s in d.get("scope", []) if isinstance(s, str)] if isinstance(d.get("scope"), list) else [],
            "verify": [normalize_verify(s) for s in d.get("verify", []) if isinstance(s, str)] if isinstance(d.get("verify"), list) else [],
            "options": [o for o in d.get("options", []) if isinstance(o, dict)] if isinstance(d.get("options"), list) else [],
            "recommendation": str(d.get("recommendation", ""))[:300], "reason": str(d.get("reason", ""))[:300]}


def parse_check(text: str) -> dict:
    d = _json(text)
    return {"verdict": d["verdict"] if d.get("verdict") in ("agree", "disagree", "unsure") else "unsure",
            "reason": str(d.get("reason", ""))[:200]}


def is_large(design: dict) -> bool:
    sc = design["scope"]
    routes = {s.split("/")[3] for s in sc if s.startswith("frontend/src/routes/") and s.count("/") >= 4}
    return (len(sc) >= 4 or any("lib/components" in s for s in sc) or len(routes) >= 2
            or design["grade"] == "user")


def _reviewer(author: str) -> str:
    return "haiku" if author == "sonnet" else "sonnet"


def decide(finding: dict, author: str = "sonnet", ask_fn=ask, opus_ok=None) -> dict:
    """후보 1건의 등급 결정 — {tier: auto|user, why, design, check, author}. 외부 호출은 ask_fn, Opus 허용은 opus_ok 로 주입."""
    if opus_ok is None:
        from scripts.audit import budget
        opus_ok = lambda: budget.opus_allowed()[0]  # noqa: E731
    what = f"{finding['kind']} / {finding.get('impact', '')} / {finding.get('fix', '')}"
    if RISK.search(what):
        return {"tier": "user", "why": "위험 키워드(스키마·권한·알고리즘 등) — 사람 결정 필요", "design": {}, "check": {}}
    prompt = docs_ctx.augment(_DESIGN % (finding["kind"], finding.get("impact", ""), finding.get("fix", "")), "designer")
    design = parse_design(ask_fn(prompt, author))
    if not design["summary"]:  # 파싱 실패는 1회 재시도 후에도 비면 user
        design = parse_design(ask_fn(prompt, author))
    if author != "opus" and is_large(design) and opus_ok():
        big = parse_design(ask_fn(prompt, "opus"))
        if big["summary"]:
            author, design = "opus", big
    reviewer = _reviewer(author)
    out = {"tier": "user", "why": "", "design": design, "check": {}, "author": author}
    if design["grade"] != "auto":
        out["why"] = f"설계자가 사용자 결정으로 분류: {design['reason']}"
    elif not design["scope"] or not design["verify"]:
        out["why"] = "범위(scope) 또는 검증(verify)이 비어 있음"
    elif not all(s.startswith(ALLOWED_SCOPE) for s in design["scope"]):
        out["why"] = f"허용 범위 밖 경로 포함: {design['scope']}"
    elif (bad := verify_doctor.lint(design["verify"], design["scope"], ROOT)):
        out["why"] = "verify 실행 불가: " + "; ".join(bad)
    else:
        cprompt = docs_ctx.augment(_CHECK % (what, design["summary"], design["scope"], design["verify"]), "designer")
        out["check"] = parse_check(ask_fn(cprompt, reviewer))
        if out["check"]["verdict"] == "unsure":  # 1회 재질의, disagree 는 그대로 사람에게
            out["check"] = parse_check(ask_fn(cprompt, reviewer))
        if out["check"]["verdict"] == "agree":
            out.update(tier="auto", why=f"교차 검토 통과({reviewer}): {out['check']['reason']}")
        else:
            out["why"] = f"교차 검토 {out['check']['verdict']}({reviewer}): {out['check']['reason']}"
    return out


def report(finding: dict, d: dict) -> str:
    """사용자 결정 보고서(마크다운) — 무엇이 문제인지, 선택지 장단점, 추천안, 왜 자체 승인되지 않았는지."""
    dz = d.get("design", {})
    opts = "\n".join(f"  - **{o.get('name', '?')}** — 장점: {o.get('pros', '')} / 단점: {o.get('cons', '')}"
                     for o in dz.get("options", [])) or "  - (설계자가 선택지를 내지 못함)"
    return (f"### {finding['kind']}\n- 문제: {finding.get('impact', '')}\n- 제안: {finding.get('fix', '')}\n"
            f"- 설계안: {dz.get('summary', '(없음)')}\n- 선택지:\n{opts}\n- 추천: {dz.get('recommendation', '(없음)')}\n"
            f"- 사람 결정이 필요한 이유: {d['why']}\n")

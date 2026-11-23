"""관점별 감사 에이전트 러너 — 원장의 이슈 셀을 묶어 관점별 claude -p 로 트리아지하고 결과를 저장한다(P3).

사용: python3 -m scripts.audit.agents [--perspectives ui,ux,...] [--dry-run] [--backlog]
자동 수정 없음 — real 판정은 audit_findings.json 에 저장하고, --backlog 면 BACKLOG 후보 문구를 출력한다((판단 필요)).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from scripts.audit import inventory
from scripts.audit import budget
from scripts.audit.perspectives import AUDIT_MODELS, RELEASE_MODELS, build_prompt

FINDINGS_PATH = inventory.LEDGER_PATH.parent / "audit_findings.json"
TIMEOUT_SEC = 300
_KINDS = (("tap-target", r"tap"), ("error-state-missing", r"error-state"), ("no-h1", r"h1"),
          ("http", r"http \d"), ("console", r"console:"), ("pageerror", r"pageerror"),
          ("overflow", r"overflow"), ("blank", r"blank"), ("text-leak", r"leak|undefined|NaN"),
          ("broken-image", r"image"))


def group_issues(ledger: dict[str, dict]) -> dict[str, list[dict]]:
    """이슈 셀을 노트의 키워드로 kind 별로 묶는다(한 셀이 여러 kind 에 속할 수 있음)."""
    groups: dict[str, list[dict]] = {}
    for cell, rec in ledger.items():
        if rec.get("status") != "이슈":
            continue
        note = rec.get("note", "")
        hit = [k for k, pat in _KINDS if re.search(pat, note, re.I)] or ["other"]
        for k in hit:
            groups.setdefault(k, []).append({"cell": cell, "note": note})
    return groups


def parse_findings(text: str) -> list[dict]:
    """에이전트 출력에서 JSON 배열을 추출. 파싱 실패 시 빈 리스트(graceful)."""
    m = re.search(r"\[.*\]", text, re.S)
    if not m:
        return []
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return []
    ok = {"real", "noise", "unsure"}
    return [d for d in data if isinstance(d, dict) and d.get("verdict") in ok and d.get("kind")]


def ask(prompt: str, model: str) -> str:
    """읽기 전용(도구 없음) claude -p 1회 호출 — 실패·타임아웃은 빈 문자열. opus 는 budget 허용 시만(아니면 sonnet)."""
    if model == "opus":
        model = "opus" if budget.opus_allowed()[0] else "sonnet"
        if model == "opus":
            budget.record_call()
    cmd = ["claude", "-p", prompt, "--model", model, "--output-format", "json",
           "--no-session-persistence", "--allowed-tools", "", "--permission-mode", "default"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT_SEC, stdin=subprocess.DEVNULL)
        return json.loads(r.stdout).get("result", "") if r.returncode == 0 else ""
    except (subprocess.TimeoutExpired, json.JSONDecodeError):
        return ""


def run_perspective(name: str, groups: dict[str, list[dict]], models: dict[str, str] | None = None) -> list[dict]:
    models = models or AUDIT_MODELS
    return [{**f, "perspective": name} for f in parse_findings(ask(build_prompt(name, groups), models[name]))]


def backlog_lines(findings: list[dict]) -> list[str]:
    seen, out = set(), []
    for f in findings:
        if f["verdict"] != "real" or f["kind"] in seen:
            continue
        seen.add(f["kind"])
        out.append(f"- (판단 필요) [{f['perspective']}] {f['kind']}: {f.get('impact', '')} → {f.get('fix', '')}")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--perspectives", default=",".join(AUDIT_MODELS))
    ap.add_argument("--dry-run", action="store_true", help="프롬프트만 출력")
    ap.add_argument("--backlog", action="store_true", help="real 판정을 BACKLOG 후보 문구로 출력")
    ap.add_argument("--review", action="store_true", help="real 후보를 다른 모델이 독립 검토(P5)")
    ap.add_argument("--release", action="store_true", help="버전업 감사 — 전 관점 Opus(budget 한도 안에서)")
    args = ap.parse_args(argv)
    groups = group_issues(inventory.load_ledger())
    names = [n for n in args.perspectives.split(",") if n in AUDIT_MODELS]
    if args.dry_run:
        for n in names:
            print(f"=== {n} ({AUDIT_MODELS[n]}) ===\n{build_prompt(n, groups)}")
        return 0
    findings = [f for n in names for f in run_perspective(n, groups, RELEASE_MODELS if args.release else None)]
    if args.review:
        from scripts.audit import review
        findings = review.review(findings, groups)
    FINDINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    FINDINGS_PATH.write_text(json.dumps(findings, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"findings {len(findings)} → {FINDINGS_PATH}")
    if args.backlog:
        if args.review:
            from scripts.audit import review
            findings = review.confirmed(findings)
        print("\n".join(backlog_lines(findings)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

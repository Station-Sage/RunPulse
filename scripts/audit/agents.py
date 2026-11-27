"""관점별 감사 에이전트 러너 — 원장의 이슈 셀을 묶어 관점별 claude -p 로 트리아지하고 결과를 저장한다(P3).

사용: python3 -m scripts.audit.agents [--perspectives ui,ux,...] [--dry-run] [--backlog]
자동 수정 없음 — real 판정은 audit_findings.json 에 저장하고, --backlog 면 BACKLOG 후보 문구를 출력한다((판단 필요)).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from scripts.audit import inventory
from scripts.audit import budget, progress
from scripts.autopilot import ledger, pacing, stream
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


class PacingHold(Exception):
    """사용량 페이싱이 막아 claude 호출을 하지 않음 — 루프는 상태를 바꾸지 않고 대기로 끝낸다."""


def _parse_stream(raw: str) -> tuple[str, dict | None, float | None]:
    text, rl, cost = "", None, None
    for line in raw.splitlines():
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(d, dict):
            continue
        if d.get("type") == "rate_limit_event":
            rl = d.get("rate_limit_info")
        elif d.get("type") == "result":
            text, cost = d.get("result", ""), d.get("total_cost_usd")
    return text, rl, cost


def ask(prompt: str, model: str, tools: str = "") -> str:
    """읽기 전용 claude -p 1회 호출(tools 는 읽기 도구만, 기본 없음) — 실패·타임아웃은 빈 문자열. opus 는 budget 허용 시만(아니면 sonnet).

    호출 전 페이싱 검사(막히면 PacingHold), 호출 후 rate_limit 관측을 원장에 기록해 다음 검사의 입력이 되게 한다."""
    p = pacing.check()
    if not p.allowed:
        raise PacingHold(p.reason)
    if model == "opus":
        model = "opus" if budget.opus_allowed()[0] else "sonnet"
    cmd = ["claude", "-p", prompt, "--model", model, "--output-format", "stream-json", "--verbose",
           "--no-session-persistence", "--allowed-tools", tools, "--permission-mode", "default"]
    stdout, returncode, timed_out = stream.run(cmd, TIMEOUT_SEC, unit_id=f"audit-ask:{model}")
    if timed_out:
        return ""
    text, rl, cost = _parse_stream(stdout)
    ledger.append({"unit_id": f"audit-ask:{model}", "outcome": "success" if returncode == 0 else "error",
                   "cost_usd": cost, "rate_limit": rl})
    return text if returncode == 0 else ""


def run_perspective(name: str, groups: dict[str, list[dict]], models: dict[str, str] | None = None) -> list[dict]:
    models = models or AUDIT_MODELS
    progress.mark(f"[감사] 관점 {name} 시작 ({models[name]})")
    out = [{**f, "perspective": name} for f in parse_findings(ask(build_prompt(name, groups), models[name]))]
    progress.mark(f"[감사] 관점 {name} 완료 — 후보 {len(out)}건")
    return out


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
    ap.add_argument("--discover", action="store_true", help="도구 사용 발견 감사 추가(라운드당 상한 settings.AUDIT_TOOL_CALLS_PER_ROUND)")
    ap.add_argument("--release", action="store_true", help="버전업 감사 — 전 관점 Opus(budget 한도 안에서)")
    args = ap.parse_args(argv)
    groups = group_issues(inventory.load_ledger())
    names = [n for n in args.perspectives.split(",") if n in AUDIT_MODELS]
    if args.dry_run:
        for n in names:
            print(f"=== {n} ({AUDIT_MODELS[n]}) ===\n{build_prompt(n, groups)}")
        return 0
    findings = [f for n in names for f in run_perspective(n, groups, RELEASE_MODELS if args.release else None)]
    from scripts.audit import discover, known
    kn, rnd = known.load(), known.current_round()
    if args.discover:
        progress.mark(f"[감사] 발견 감사 시작 — 잔여 호출 {discover.remaining(rnd)}")
        findings += discover.run(rnd)
    findings = known.filter_new(findings, kn)
    if args.review:
        from scripts.audit import review
        progress.mark(f"[감사] 독립 검토 시작 — {len(findings)}건")
        progress.event("sub", step="review", state="start", n=len(findings))
        findings = review.review(findings, groups)
    known.record([f for f in findings if f.get("verdict") == "real"], rnd)
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

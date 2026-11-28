"""개발 항목 목록·상세 — 큐(auto)를 단계별로 묶고, 항목별로 결정 이력·개발 기록(원장·실행 보고)·검토 정보를 모은다."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from scripts.audit import decisions, progress
from scripts.autopilot import ledger, queue, settings, verify_doctor

ORDER = ("in_progress", "queued", "needs_decision", "failed", "review", "done")
REPORT_MAX = 4000
STEPS = ("design", "develop", "test", "commit", "deploy")
STEP_LABEL = {"design": "설계", "develop": "개발", "test": "테스트", "commit": "커밋", "deploy": "운영반영"}
_ID_IN_SUBJECT = re.compile(r"\(([A-Za-z0-9._-]+(?:, ?[A-Za-z0-9._-]+)*)\)")


def _git(args: list[str]) -> str:
    try:
        return subprocess.run(["git", "-C", str(settings.WORKTREE_DIR), *args], capture_output=True, text=True, timeout=20).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def git_facts(git=_git) -> tuple[dict[str, str], set[str]]:
    """(항목 ID → 단위 브랜치의 최신 커밋 해시, 운영 브랜치에 들어간 커밋 해시 집합)."""
    commits: dict[str, str] = {}
    for ln in git(["log", settings.AUTOPILOT_BRANCH, "-n", "1500", "--format=%H%x09%s"]).splitlines():
        h, _, subj = ln.partition("\t")
        for m in _ID_IN_SUBJECT.finditer(subj):
            for iid in re.split(r",\s*", m.group(1)):
                commits.setdefault(iid, h)
    base = set(git(["rev-list", settings.BASE_BRANCH, "-n", "6000"]).split())
    return commits, base


def commit_times(git=_git) -> dict[str, int]:
    """항목 ID → 단위 브랜치 최신 커밋 시각(epoch) — 개발완료 순서 정렬용."""
    out: dict[str, int] = {}
    for ln in git(["log", settings.AUTOPILOT_BRANCH, "-n", "1500", "--format=%ct%x09%s"]).splitlines():
        t, _, subj = ln.partition("\t")
        for m in _ID_IN_SUBJECT.finditer(subj):
            for iid in re.split(r",\s*", m.group(1)):
                if t.isdigit():
                    out.setdefault(iid, int(t))
    return out


def pipeline(items: list[queue.QueueItem], entries: list[dict], cycle: dict, facts: tuple[dict[str, str], set[str]]) -> dict[str, dict]:
    """항목별 5단계(설계·개발·테스트·커밋·운영반영) 완료 여부 + 진행중 — 큐 단계·원장·git 사실에서만 도출한다."""
    commits, base = facts
    ran_ok = {e.get("unit_id") for e in entries if e.get("outcome") == "success"}
    running = cycle.get("unit") if cycle.get("phase") in ("develop", "test") and cycle.get("stop_reason") is None else None
    testing = _verify_unit()
    out = {}
    for it in items:
        h = commits.get(it.item_id)
        done = it.stage == "done"
        steps = {"design": it.stage != "needs_decision" or bool(it.resolution),
                 "develop": it.item_id in ran_ok or done,
                 "test": it.stage in ("review", "done"),
                 "commit": bool(h) or done,
                 "deploy": bool(h and h in base) or done}
        run = it.stage == "in_progress" or it.item_id == running
        out[it.item_id] = {"steps": steps, "running": run, "running_step": ("test" if it.item_id == testing else "develop") if run else ""}
    return out


def _verify_unit() -> str:
    try:
        return json.loads((settings.STATE_DIR / "verify_state.json").read_text(encoding="utf-8")).get("unit", "")
    except (OSError, ValueError):
        return ""


def _cycle_state() -> dict:
    try:
        return json.loads((settings.STATE_DIR / "cycle_state.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _brief(it: queue.QueueItem) -> dict:
    return {"id": it.item_id, "text": it.text[:140], "stage": it.stage, "kind": it.kind, "attempts": it.attempts,
            "critical": it.critical, "resolution": it.resolution, "fail_kind": it.fail_kind}


def item_list(path: Path | None = None, entries: list[dict] | None = None, cycle: dict | None = None, facts=None, times: dict[str, int] | None = None) -> dict:
    items = [it for it in queue.parse(path or settings.QUEUE_PATH) if it.mode == "auto"]
    pipe = pipeline(items, ledger.read_all() if entries is None else entries, _cycle_state() if cycle is None else cycle, git_facts() if facts is None else facts)
    counts = {s: 0 for s in ORDER}
    for it in items:
        counts[it.stage] = counts.get(it.stage, 0) + 1
    rank = {s: i for i, s in enumerate(ORDER)}
    ents = ledger.read_all() if entries is None else entries
    done_at = dict(commit_times() if times is None else times)
    ledger_ts: dict[str, int] = {}
    for e in ents:   # 원장이 우선 — 단위 브랜치 커밋은 리플레이로 시각이 한꺼번에 덮일 수 있다
        if e.get("outcome") == "success" and e.get("unit_id") and e.get("ts"):
            done_at[e["unit_id"]] = max(int(e["ts"]), ledger_ts.get(e["unit_id"], 0))
            ledger_ts[e["unit_id"]] = done_at[e["unit_id"]]
    rows = sorted(({**_brief(it), **pipe[it.item_id], "done_at": done_at.get(it.item_id, 0) if it.stage == "done" else 0} for it in items),
                  key=lambda r: (rank.get(r["stage"], 99), -r["done_at"]))
    total = len(items)
    return {"total": total, "counts": counts, "done_pct": round(100 * counts["done"] / total) if total else 0, "items": rows}


def _run_report(iid: str, log_dir: Path) -> dict:
    """가장 최근 실행 로그 끝의 result 레코드(모델 최종 보고)."""
    logs = sorted(log_dir.glob(f"*_{iid}*.jsonl")) if log_dir.is_dir() else []
    if not logs:
        return {}
    try:
        for ln in reversed(logs[-1].read_text(encoding="utf-8", errors="replace").splitlines()):
            try:
                rec = json.loads(ln)
            except ValueError:
                continue
            if rec.get("type") == "result":
                return {"file": logs[-1].name, "is_error": bool(rec.get("is_error")), "report": str(rec.get("result") or "")[:REPORT_MAX]}
    except OSError:
        pass
    return {"file": logs[-1].name, "report": ""}


def _audit_trail(iid: str, state_dir: Path) -> list[dict]:
    out = []
    try:
        for ln in (state_dir / "console_audit.jsonl").read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(ln)
            except ValueError:
                continue
            if (r.get("detail") or {}).get("id") == iid:
                out.append({"ts": r["ts"], "action": r["action"], "detail": r["detail"]})
    except OSError:
        pass
    return out[-20:]


def _review(it: queue.QueueItem, run: dict, runs: list[dict]) -> dict:
    """검토 블록 — 저장된 사실에서만 도출한다(판정은 사람이 한다)."""
    last = runs[-1] if runs else None
    verify_ran = bool(last and last.get("outcome") == "success")
    todo = list(it.verify) or ["verify 명령 없음 — 변경 diff 를 직접 확인"]
    problems = []
    if it.fail_reason:
        problems.append(f"{it.fail_kind or 'failed'}: {it.fail_reason}")
    if run.get("is_error"):
        problems.append("마지막 실행이 오류로 끝남")
    if it.attempts > 1:
        problems.append(f"{it.attempts}회 시도 끝에 완료")
    if it.critical:
        problems.append("critical 항목 — 병합 전 사람 확인 필수")
    return {"what": it.text, "scope": it.scope, "verify_cmds": it.verify,
            "how": ("마지막 실행 성공 후 review 단계 — verify 결과는 아래 실행 보고 참조" if verify_ran else "실행 기록 없음 또는 성공 아님") if it.stage in ("review", "done") else "",
            "problems": problems, "remaining": todo + ["병합은 사용자가 한다(콘솔은 확인 완료만 표시)"]}


def _diagnosis(it) -> dict | None:
    """failed verify 항목의 진단(종류·원인 파일) — 콘솔이 '다시 시도하면 무엇이 달라지는지'를 보여 준다."""
    if it.stage != "failed" or it.fail_kind != "verify":
        return None
    kind, _, target = verify_doctor.failed_diagnosis(it.fail_reason, it.scope)
    return {"kind": kind or "real", "target": target}


def item_detail(iid: str, queue_path: Path | None = None, dpath: Path | None = None, log_dir: Path | None = None,
                entries: list[dict] | None = None, events: list[dict] | None = None, state_dir: Path | None = None) -> dict | None:
    it = next((x for x in queue.parse(queue_path or settings.QUEUE_PATH) if x.item_id == iid), None)
    if it is None:
        return None
    dec = next((d for d in decisions.load(dpath) if d["id"] == iid), None)
    es = ledger.read_all() if entries is None else entries
    runs = [{k: e.get(k) for k in ("ts", "outcome", "cost_usd", "num_turns", "duration_s")} for e in es if e.get("unit_id") == iid]
    evs = progress.read_events() if events is None else events
    timeline = [{"ts": e["ts"], "kind": e["kind"], "round": e.get("round"), "result": e.get("result")}
                for e in evs if e.get("unit") == iid and e.get("kind") in ("unit_start", "unit_end")][-20:]
    run = _run_report(iid, log_dir or settings.RUN_LOG_DIR)
    return {"item": {**_brief(it), "full_text": it.text, "scope": it.scope, "verify": it.verify, "deps": it.deps, "fail_reason": it.fail_reason, "diagnosis": _diagnosis(it)},
            "decision": dec, "runs": runs, "timeline": timeline, "report": run,
            "audit": _audit_trail(iid, state_dir or settings.STATE_DIR), "review": _review(it, run, runs)}

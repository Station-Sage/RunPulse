"""중첩 반복 오케스트레이터 — {감사 → 설계 → (개발 → 테스트(브라우저 스윕) → 버그수정) ↺ 작은 반복} ↺ 전체 반복.

사용: .venv/bin/python -m scripts.audit.loop [--force] [--reset] [--status]
호출 1회 = 멈춤 조건(pacing 대기·정지·감사 생략·MAX_STEPS)까지 단계를 연속 수행(--once 면 1개). 위치는 cycle_state.json + BACKLOG 항목 stage 로 복원하므로 언제 끊겨도 이어진다.
  audit  : 버전이 바뀌었으면 release.run(Opus 전 관점, 한도 내) 먼저, 아니면 cycle.run_cycle (스윕 필수 + 관점 감사 + 독립 검토) → design
  design : 확인된 후보를 BACKLOG 에 제안(자체 승인=queued, 사용자 결정=needs_decision) → develop
  (사용자 결정 대기 항목은 막지 않는다 — needs_decision 으로 남기고 state["pending_decisions"] 로만 노출, 나머지 단위는 계속 진행. 사람이 stage 를 queued 로 바꾸면 다음 develop 에서 집어간다)
  develop: run_unit.run_once 1건 → review 면 test, failed 면 알리고 다음 항목
  test   : 브라우저 스윕(안쪽 루프) 통과 → done, 실패 → queued(버그수정 재개발), 상한 초과 → failed
정지는 stopreason.py 의 사유(pacing·step_cap·failed·stop_flag)로 기록하고 타이머 발화 시 사유별로 자동 재개한다.
정지 조건: 같은 단계 연속 실패 FAIL_LIMIT, 항목당 테스트 재시도 FIX_LIMIT, 라운드당 단위 UNIT_CAP, 단계 직전 pacing.
열린 단위가 없으면(또는 단위 상한) 라운드가 끝나며 통과 단위가 있으면 운영 반영(deploy.py) 후 다음 감사(audit)로 돌아간다 — 고정 최소 간격(90분)은 없고 라운드 종료 즉시 시작(pacing 만 게이트). 이 프로세스는 대화 세션에 쓸 수 없어 알림은 텔레그램이다.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from pathlib import Path

from scripts.audit import agents, consume, cycle, decisions, deploy, inventory, progress, release, stopreason, triage
from scripts.autopilot import notify, pacing, queue, reconcile, settings

STATE_PATH = inventory.LEDGER_PATH.parent / "cycle_state.json"
FAIL_LIMIT, FIX_LIMIT, UNIT_CAP, MAX_STEPS = 3, 2, 5, 40
_INIT = {"phase": "audit", "unit": None, "round": 1, "units_done": 0, "fails": 0, "fix": {},
         "stop_reason": None, "pending_decisions": 0}


def load_state(path: Path | None = None) -> dict:
    try:
        return {**_INIT, **json.loads((path or STATE_PATH).read_text(encoding="utf-8"))}
    except (OSError, ValueError):
        return dict(_INIT)


def save_state(st: dict, path: Path | None = None) -> None:
    p = path or STATE_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")


PENDING_PATH = Path(".claude/autopilot/pending_decisions.md")


def propose(findings: list[dict], path: Path, decide=None, tiers: dict | None = None) -> list[str]:
    """확인된 후보를 BACKLOG 끝에 제안한다(이미 있으면 건너뜀). 새 항목 ID 목록 반환.

    decide(finding)→triage 결과가 auto 면 stage=queued(scope·verify 채움, 자체 승인), 아니면 needs_decision(사람 결정)
    + 결정 보고서를 PENDING_PATH 에 추가. decide 가 없으면 전부 needs_decision. tiers 에 {id: tier} 를 채운다.
    열린 단위의 텍스트에 "(커버: kind)" 가 있으면 같은 kind 후보는 중복으로 보고 제안하지 않는다.
    """
    from scripts.audit import triage
    items = queue.parse(path)
    have = {it.item_id for it in items}
    covered = {m for it in items if it.stage not in ("done", "needs_decision", "failed") for m in re.findall(r"\(커버: ([\w,\- ]+)\)", it.text)
               for m in re.split(r"[, ]+", m) if m}
    new, lines, reports, recs = [], [], [], []
    for f in findings:
        if f["kind"] in covered:
            continue
        ln = agents.backlog_lines([f])[0]
        iid = "AUD-" + hashlib.sha1(ln.encode()).hexdigest()[:6]
        if iid in have:
            continue
        d = decide(f) if decide else {"tier": "user", "why": "등급 분류 미사용", "design": {}}
        meta = {"stage": "queued" if d["tier"] == "auto" else "needs_decision", "mode": "auto", "attempts": 0, "deps": [],
                "kind": "code"}
        if d["tier"] == "auto":
            meta.update(scope=d["design"]["scope"], verify=d["design"]["verify"], auto_approved=True)
        else:
            reports.append(f"## {iid}\n" + triage.report(f, d))
            recs.append(decisions.build(iid, f, d))
        new.append(iid)
        if tiers is not None:
            tiers[iid] = d["tier"]
        lines += [f"- **[{iid}]** {ln[2:]}", f"  <!-- autopilot: {json.dumps(meta, ensure_ascii=False)} -->"]
    if lines:
        with path.open("a", encoding="utf-8") as fh:
            fh.write("\n" + "\n".join(lines) + "\n")
    decisions.append(recs)
    if reports:
        PENDING_PATH.parent.mkdir(parents=True, exist_ok=True)
        with PENDING_PATH.open("a", encoding="utf-8") as fh:
            fh.write("\n".join(reports) + "\n")
    return new


def _load_findings() -> list[dict]:
    try:
        return json.loads(agents.FINDINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []


def _stage(path: Path, iid: str) -> str | None:
    return next((i.stage for i in queue.parse(path) if i.item_id == iid), None)


def _fail(st: dict, why: str) -> str:
    st["fails"] += 1
    if st["fails"] >= FAIL_LIMIT:
        st["phase"] = "halted"
        stopreason.stop(st, stopreason.FAILED)
        notify.send(f"[루프] {FAIL_LIMIT}회 연속 실패로 정지 — {why} (--reset 으로 재개)" + notify.console_hint())
    return why


def STOP_FLAG() -> Path:
    return settings.STATE_DIR / "stop_after_round"


def _pending_decisions(path: Path) -> int:
    return sum(1 for it in queue.parse(path) if it.stage == "needs_decision")


def _should_stop(path: Path) -> bool:
    return STOP_FLAG().exists()


def _end_round(st: dict, ship, msg: str, path: Path | None = None) -> str:
    """안쪽 루프 종료 — 통과 단위가 있으면 운영 반영(실패해도 루프는 계속, 알림만) 후 다음 감사로."""
    progress.event("deploy_start", round=st["round"], units=st["units_done"])
    r = ship(st["units_done"])
    ok = r.get("outcome") == "done"
    progress.event("deploy_end", round=st["round"], ran=bool(r.get("ran")), ok=ok)
    if r.get("ran"):
        notify.send(f"[루프] 운영 반영 {'완료' if ok else '실패'} — {r.get('commits', 0)}커밋, {r.get('reason')}"
                    + ("" if ok else " (자동 반영 안 됨, 사람 확인 필요)"))
        msg += f" · 운영 반영 {'완료' if ok else '실패'}({r.get('reason')})"
    st.update(phase="audit", round=st["round"] + 1, units_done=0, unit=None)
    st["pending_decisions"] = _pending_decisions(path or settings.QUEUE_PATH)
    if _should_stop(path or settings.QUEUE_PATH):
        STOP_FLAG().unlink(missing_ok=True)
        st["phase"] = "stopped"
        stopreason.stop(st, stopreason.STOP_FLAG)
        notify.send(f"[루프] 라운드 {st['round'] - 1} 종료 — 단일 라운드 지정에 따라 정지(재개: --reset)")
        msg += " · 정지(단일 라운드)"
    return msg


def step(st: dict, *, path: Path | None = None, act: dict | None = None, force: bool = False) -> str:
    """상태를 한 칸 진행하고 한 줄 결과를 반환한다. act 로 외부 동작(감사·개발·스윕)을 주입할 수 있다."""
    path = path or settings.QUEUE_PATH
    act = act or {}
    audit = act.get("audit", lambda: cycle.run_cycle(force=True))  # pacing 은 위에서 검사, 90분 간격은 단독 cycle 용(여기선 라운드 종료가 곧 간격)
    rel = act.get("release", release.run)
    develop = act.get("develop", _develop)
    ship = act.get("deploy", deploy.run)
    sweep = act.get("sweep", lambda: cycle.browser_sweep())
    ph = st["phase"]
    progress.mark(f"[루프] 라운드 {st['round']} · {ph} 단계 시작")
    progress.event("phase", round=st["round"], phase=ph)
    if ph == "stopped":
        stopreason.stop(st, st.get("stop_reason") or stopreason.STOP_FLAG)
        return "정지 상태 — 단일 라운드 완료(재개: --reset)"
    if ph == "halted":
        stopreason.stop(st, stopreason.FAILED)
        return "정지 상태 — 원인 확인 후 --reset"
    if not force:
        p = pacing.check(time.time())
        if not p.allowed:
            stopreason.stop(st, stopreason.PACING)
            return f"pacing 대기: {p.reason}"
    if ph == "audit":
        e = rel() if release.due() else {"ran": False}
        if e.get("ran"):
            notify.send(f"[루프] 버전 {release.version()} 릴리스 감사(Opus) 실행")
        else:
            e = audit()
        if not e.get("ran"):
            stopreason.stop(st, stopreason.PACING)
            return f"감사 생략: {e.get('reason')}"
        if e.get("outcome") != "done":
            return _fail(st, f"감사 실패: {e.get('reason')}")
        st.update(phase="design", fails=0)
        return f"감사 완료 — 후보 {e.get('confirmed', 0)}건"
    if ph == "design":
        tiers: dict = {}
        new = propose(agents_confirmed(), path, act.get("decide", triage.decide), tiers)
        auto = [i for i in new if tiers[i] == "auto"]
        user = [i for i in new if tiers[i] == "user"]
        st.update(phase="develop" if new else "audit", fails=0)
        progress.event("design", round=st["round"], new=len(new), auto=len(auto), user=len(user))
        if new:
            notify.send(f"[루프] 설계 {len(new)}건 — 자체 승인(교차 검토 통과) {len(auto)}건 진행: {', '.join(auto) or '-'}"
                        f" / 사용자 결정 대기 {len(user)}건(장단점·추천은 {PENDING_PATH}): {', '.join(user) or '-'}."
                        " 승인은 콘솔 결정함 또는 BACKLOG stage 를 queued 로." + notify.console_hint())
            return f"설계 {len(new)}건 — 자체 승인 {len(auto)}, 사용자 결정 {len(user)}"
        st["round"] += 1
        if _should_stop(path):
            STOP_FLAG().unlink(missing_ok=True)
            st["phase"] = "stopped"
            stopreason.stop(st, stopreason.STOP_FLAG)
            notify.send("[루프] 새 후보 없음 — 단일 라운드 지정에 따라 정지")
            return "새 후보 없음 — 단일 라운드 종료(정지)"
        return "새 후보 없음 — 라운드 종료"
    if ph in ("await", "develop"):
        for m in consume.apply(path, act.get("decide", triage.decide)):
            progress.mark(f"[루프] 결정 반영: {m}")
        promoted = reconcile.promote_merged(path)
        if promoted:
            progress.mark(f"[루프] 병합 완료된 review 항목 done 승격: {', '.join(promoted)}")
        reconcile.prune_pending(path, PENDING_PATH)
        items = queue.parse(path)
        if queue.next_runnable(items) is None:
            from collections import Counter
            progress.mark(f"[루프] 실행 가능 단위 없음 — 항목 {len(items)}건, (단계,모드) 분포 {dict(Counter((i.stage, i.mode) for i in items))}")
            return _end_round(st, ship, "열린 단위 없음 — 다음 감사로", path)
        if st["units_done"] >= UNIT_CAP:
            return _end_round(st, ship, f"라운드 단위 상한 {UNIT_CAP} — 다음 감사로")
        nxt = queue.next_runnable(queue.parse(path))
        progress.event("unit_start", round=st["round"], unit=nxt.item_id)
        rc = develop()
        stage = _stage(path, nxt.item_id)
        if rc == 2 or stage == "failed":
            notify.send(f"[루프] {nxt.item_id} 개발 차단 — 사람 확인 필요")
            st.update(phase="develop", unit=None)
            return _fail(st, f"{nxt.item_id} 개발 차단")
        if stage == "review":
            st.update(phase="test", unit=nxt.item_id, fails=0)
            return f"{nxt.item_id} 개발 완료 → 테스트"
        st["phase"] = "develop"
        return f"{nxt.item_id} 개발 단계 유지(stage={stage}, rc={rc})"
    if ph == "test":
        iid = st["unit"]
        n, err = sweep()
        if not err:
            queue.update_item(path, iid, stage="done")
            progress.event("unit_end", round=st["round"], unit=iid, result="done")
            st.update(phase="develop", unit=None, units_done=st["units_done"] + 1, fails=0)
            return f"{iid} 테스트 통과({n}셀) → done"
        tries = st["fix"].get(iid, 0) + 1
        st["fix"][iid] = tries
        if tries > FIX_LIMIT:
            queue.update_item(path, iid, stage="failed")
            progress.event("unit_end", round=st["round"], unit=iid, result="failed")
            notify.send(f"[루프] {iid} 버그수정 {FIX_LIMIT}회 후에도 스윕 실패 — failed: {err}")
            st.update(phase="develop", unit=None)
            return f"{iid} 수정 상한 초과 → failed"
        queue.update_item(path, iid, stage="queued")
        st["phase"] = "develop"
        return f"{iid} 스윕 실패({err}) → 수정 재개발 {tries}/{FIX_LIMIT}"
    stopreason.stop(st, stopreason.FAILED)
    return f"알 수 없는 단계 {ph}"


def agents_confirmed() -> list[dict]:
    from scripts.audit import review
    return review.confirmed(_load_findings())


def _develop() -> int:
    from scripts.autopilot import run_unit
    return run_unit.run_once(ignore_night=True, ignore_idle=True, ignore_budget=True)


def run_until_stop(st: dict, *, force: bool = False, once: bool = False, act: dict | None = None,
                   path: Path | None = None, max_steps: int = MAX_STEPS) -> list[str]:
    """단계를 연속 수행한다. 멈춤: pacing 대기·halted·감사 생략·MAX_STEPS·(단계 상태 저장은 매 단계)."""
    out = []
    stopreason.resume(st) or out.append("정지 유지 — 자동 재개 불가 사유(" + str(st.get("stop_reason")) + ")")
    if stopreason.is_stopped(st):
        return out
    for i in range(1 if once else max_steps):
        try:
            r = step(st, act=act, path=path, force=force)
        except agents.PacingHold as e:
            r = f"pacing 대기: {e}"
            stopreason.stop(st, stopreason.PACING)
        except Exception as e:  # 한 단계의 예외가 상태 전환을 잃게 하지 않는다 — 실패 집계(FAIL_LIMIT 시 halted)
            progress.mark(f"[루프] 예외: {type(e).__name__}: {e}")
            r = _fail(st, f"예외 {type(e).__name__}: {e}")
        progress.mark("[루프] 결과: " + r)
        save_state(st) if path is None else None
        out.append(r)
        if stopreason.is_stopped(st) or st["phase"] in ("halted", "stopped"):
            break
        if not once and i == max_steps - 1:
            stopreason.stop(st, stopreason.STEP_CAP)
            save_state(st) if path is None else None
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--force", action="store_true", help="pacing·간격 무시(수동 점검용)")
    ap.add_argument("--reset", action="store_true", help="정지 상태 해제(감사부터 재개)")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--once", action="store_true", help="단계 1개만 수행(기본은 멈춤 조건까지 연속)")
    a = ap.parse_args(argv)
    st = load_state()
    if a.reset:
        st.update(phase="audit", fails=0, unit=None, stop_reason=None)
    if not a.status:
        run_until_stop(st, force=a.force, once=a.once)
    save_state(st)
    print(json.dumps(st, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

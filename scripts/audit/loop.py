"""중첩 반복 오케스트레이터 — {감사 → 설계 → (개발 → 테스트(브라우저 스윕) → 버그수정) ↺ 작은 반복} ↺ 전체 반복.

사용: .venv/bin/python -m scripts.audit.loop [--force] [--reset] [--status]
호출 1회 = 단계 1개만 수행하고 끝난다. 위치는 cycle_state.json + BACKLOG 항목 stage 로 복원하므로 언제 끊겨도 이어진다.
  audit  : 버전이 바뀌었으면 release.run(Opus 전 관점, 한도 내) 먼저, 아니면 cycle.run_cycle (스윕 필수 + 관점 감사 + 독립 검토) → design
  design : 확인된 후보를 BACKLOG 에 제안(자체 승인=queued, 사용자 결정=blocked) → develop
  (사용자 결정 대기 항목은 막지 않는다 — blocked 로 남기고 나머지 단위는 계속 진행. 사람이 stage 를 queued 로 바꾸면 다음 develop 에서 집어간다)
  develop: run_unit.run_once 1건 → review 면 test, blocked 면 알리고 다음 항목
  test   : 브라우저 스윕(안쪽 루프) 통과 → done, 실패 → queued(버그수정 재개발), 상한 초과 → blocked
정지 조건: 같은 단계 연속 실패 FAIL_LIMIT, 항목당 테스트 재시도 FIX_LIMIT, 라운드당 단위 UNIT_CAP, 단계 직전 pacing.
열린 단위가 없으면 라운드가 끝나고 다음 감사(audit)로 돌아간다. 이 프로세스는 대화 세션에 쓸 수 없어 알림은 텔레그램이다.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

from scripts.audit import agents, cycle, inventory, release, triage
from scripts.autopilot import notify, pacing, queue, settings

STATE_PATH = inventory.LEDGER_PATH.parent / "cycle_state.json"
FAIL_LIMIT, FIX_LIMIT, UNIT_CAP = 3, 2, 5
_INIT = {"phase": "audit", "unit": None, "round": 1, "units_done": 0, "fails": 0, "fix": {}}


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

    decide(finding)→triage 결과가 auto 면 stage=queued(scope·verify 채움, 자체 승인), 아니면 blocked(사람 결정)
    + 결정 보고서를 PENDING_PATH 에 추가. decide 가 없으면 전부 blocked. tiers 에 {id: tier} 를 채운다.
    """
    from scripts.audit import triage
    have = {it.item_id for it in queue.parse(path)}
    new, lines, reports = [], [], []
    for f in findings:
        ln = agents.backlog_lines([f])[0]
        iid = "AUD-" + hashlib.sha1(ln.encode()).hexdigest()[:6]
        if iid in have:
            continue
        d = decide(f) if decide else {"tier": "user", "why": "등급 분류 미사용", "design": {}}
        meta = {"stage": "queued" if d["tier"] == "auto" else "blocked", "mode": "auto", "attempts": 0, "deps": [],
                "kind": "code"}
        if d["tier"] == "auto":
            meta.update(scope=d["design"]["scope"], verify=d["design"]["verify"])
        else:
            reports.append(f"## {iid}\n" + triage.report(f, d))
        new.append(iid)
        if tiers is not None:
            tiers[iid] = d["tier"]
        lines += [f"- **[{iid}]** {ln[2:]}", f"  <!-- autopilot: {json.dumps(meta, ensure_ascii=False)} -->"]
    if lines:
        with path.open("a", encoding="utf-8") as fh:
            fh.write("\n" + "\n".join(lines) + "\n")
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
        notify.send(f"[루프] {FAIL_LIMIT}회 연속 실패로 정지 — {why} (--reset 으로 재개)")
    return why


def step(st: dict, *, path: Path | None = None, act: dict | None = None, force: bool = False) -> str:
    """상태를 한 칸 진행하고 한 줄 결과를 반환한다. act 로 외부 동작(감사·개발·스윕)을 주입할 수 있다."""
    path = path or settings.QUEUE_PATH
    act = act or {}
    audit = act.get("audit", lambda: cycle.run_cycle(force=force))
    rel = act.get("release", release.run)
    develop = act.get("develop", _develop)
    sweep = act.get("sweep", lambda: cycle.browser_sweep())
    ph = st["phase"]
    if ph == "halted":
        return "정지 상태 — 원인 확인 후 --reset"
    if not force:
        p = pacing.check(time.time())
        if not p.allowed:
            return f"pacing 대기: {p.reason}"
    if ph == "audit":
        e = rel() if release.due() else {"ran": False}
        if e.get("ran"):
            notify.send(f"[루프] 버전 {release.version()} 릴리스 감사(Opus) 실행")
        else:
            e = audit()
        if not e.get("ran"):
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
        if new:
            notify.send(f"[루프] 설계 {len(new)}건 — 자체 승인(교차 검토 통과) {len(auto)}건 진행: {', '.join(auto) or '-'}"
                        f" / 사용자 결정 대기 {len(user)}건(장단점·추천은 {PENDING_PATH}): {', '.join(user) or '-'}."
                        " 승인은 BACKLOG stage 를 queued 로.")
            return f"설계 {len(new)}건 — 자체 승인 {len(auto)}, 사용자 결정 {len(user)}"
        st["round"] += 1
        return "새 후보 없음 — 라운드 종료"
    if ph in ("await", "develop"):
        if queue.next_runnable(queue.parse(path)) is None:
            st.update(phase="audit", round=st["round"] + 1, units_done=0, unit=None)
            return "열린 단위 없음 — 다음 감사로"
        if st["units_done"] >= UNIT_CAP:
            st.update(phase="audit", round=st["round"] + 1, units_done=0, unit=None)
            return f"라운드 단위 상한 {UNIT_CAP} — 다음 감사로"
        nxt = queue.next_runnable(queue.parse(path))
        rc = develop()
        stage = _stage(path, nxt.item_id)
        if rc == 2 or stage == "blocked":
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
            st.update(phase="develop", unit=None, units_done=st["units_done"] + 1, fails=0)
            return f"{iid} 테스트 통과({n}셀) → done"
        tries = st["fix"].get(iid, 0) + 1
        st["fix"][iid] = tries
        if tries > FIX_LIMIT:
            queue.update_item(path, iid, stage="blocked")
            notify.send(f"[루프] {iid} 버그수정 {FIX_LIMIT}회 후에도 스윕 실패 — blocked: {err}")
            st.update(phase="develop", unit=None)
            return f"{iid} 수정 상한 초과 → blocked"
        queue.update_item(path, iid, stage="queued")
        st["phase"] = "develop"
        return f"{iid} 스윕 실패({err}) → 수정 재개발 {tries}/{FIX_LIMIT}"
    return f"알 수 없는 단계 {ph}"


def agents_confirmed() -> list[dict]:
    from scripts.audit import review
    return review.confirmed(_load_findings())


def _develop() -> int:
    from scripts.autopilot import run_unit
    return run_unit.run_once(ignore_night=True, ignore_idle=True, ignore_budget=True)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--force", action="store_true", help="pacing·간격 무시(수동 점검용)")
    ap.add_argument("--reset", action="store_true", help="정지 상태 해제(감사부터 재개)")
    ap.add_argument("--status", action="store_true")
    a = ap.parse_args(argv)
    st = load_state()
    if a.reset:
        st.update(phase="audit", fails=0, unit=None)
    if not a.status:
        print(step(st, force=a.force))
    save_state(st)
    print(json.dumps(st, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""운영 반영 실패 보류 — 반영이 실패하면 라운드를 넘기지 않고 결정 카드(DEPLOY-R<n>)를 올린 뒤 답이 올 때까지 멈춘다.

hold: 카드 생성 + phase=deploy_hold(stop_reason 은 쓰지 않는다 — 정지는 step 도달 전에 run_until_stop 을 끝낸다). release: 사용자가 고른 선택지(action)를 적용한다.
action: retry_now(반영 재시도)|fix_unit(수정 단위 큐 투입 후 개발)|retry_later(다음 라운드 끝에 재시도)|hold(halted, 사람 처리 후 재개).
"""
from __future__ import annotations

import json
from pathlib import Path

from scripts.audit import decisions, progress
from scripts.autopilot import notify, settings
from scripts.autopilot.deploy_card import build_deploy_card

FIX_KINDS = ("tests", "build")


def hold(st: dict, r: dict, dpath: Path | None = None) -> str:
    kind, reason = r.get("kind", "merge"), str(r.get("reason", ""))
    card = build_deploy_card(st["round"], kind, reason, units=st["units_done"], commits=r.get("commits", 0))
    card["reason_full"] = reason[:2500]
    decisions.append([card], dpath or decisions.DECISIONS_PATH, fresh=True)
    st.update(phase="deploy_hold", deploy_fail={"kind": kind, "reason": reason[:2500]})
    progress.event("deploy_hold", round=st["round"], fail=kind)
    notify.send(f"[루프] 운영 반영 실패({kind}) — 라운드 {st['round']} 를 넘기지 않고 결정 대기: {reason[:150]}" + notify.console_hint())
    return f"운영 반영 실패({kind}) — 결정 카드 {card['id']} 대기(라운드 유지)"


def _queue_fix(path: Path, st: dict, kind: str, reason: str) -> str:
    iid = f"DEPLOY-FIX-R{st['round']}"
    from scripts.autopilot import queue
    if any(it.item_id == iid for it in queue.parse(path)):
        return iid
    scope = ["frontend/src/" if kind == "build" else "src/ tests/", f"운영 반영 실패({kind}) 원인 수정: {reason[:500]}"]
    verify = "cd frontend && npm run build" if kind == "build" else ".venv/bin/python -m pytest tests/ -x -q"
    meta = {"stage": "queued", "mode": "auto", "attempts": 0, "deps": [], "kind": "code", "critical": True, "scope": scope, "verify": [verify], "auto_approved": True}
    with path.open("a", encoding="utf-8") as fh:
        fh.write("\n" + f"- **[{iid}]** 라운드 {st['round']} 운영 반영 실패({kind}) 수정\n  <!-- autopilot: {json.dumps(meta, ensure_ascii=False)} -->\n")
    return iid


def release(st: dict, path: Path | None = None, dpath: Path | None = None) -> str | None:
    """phase=deploy_hold 이고 카드가 chosen 이면 선택을 적용하고 정지를 푼다. 적용 설명을 돌려주고, 대기 중이면 None."""
    if st.get("phase") != "deploy_hold":
        return None
    dp = dpath or decisions.DECISIONS_PATH
    rec = next((r for r in decisions.load(dp) if r["id"] == f"DEPLOY-R{st['round']}"), None)
    if not rec or rec["status"] != "chosen":
        return None
    opt = next((o for o in rec["options"] if o["key"] == rec.get("choice")), None)
    action = opt["action"] if opt else "hold"
    fail = st.get("deploy_fail", {})
    st["stop_reason"] = None
    st.pop("resume_at", None)
    msg = f"결정 {rec.get('choice')}({action})"
    if action == "fix_unit" and fail.get("kind") in FIX_KINDS:
        fid = _queue_fix(path or settings.QUEUE_PATH, st, fail["kind"], fail.get("reason", ""))
        st.update(phase="develop", unit=None)
        msg += f" — 수정 단위 {fid} 개발 후 재시도"
    elif action == "retry_later":
        st.update(phase="audit", round=st["round"] + 1, unit=None)
        msg += " — 다음 라운드 끝에 재시도"
    elif action == "retry_now":
        st["phase"] = "deploy_retry"
    else:
        st.update(phase="halted", stop_cause="운영 반영 보류 — 사람 처리 후 재개")
        msg += " — 보류"
    rec["status"] = "applied"
    decisions.save([rec if r["id"] == rec["id"] else r for r in decisions.load(dp)], dp)
    return msg


def retry(st: dict, ship, dpath: Path | None = None) -> str:
    """retry_now 선택 후 반영을 다시 시도 — 성공하면 라운드를 넘기고, 실패하면 다시 결정 대기."""
    r = ship(st["units_done"])
    if r.get("ran") and r.get("outcome") != "done":
        return hold(st, r, dpath)
    st.update(phase="audit", round=st["round"] + 1, units_done=0, unit=None)
    return "운영 반영 재시도 완료" if r.get("ran") else f"운영 반영 재시도 — 반영할 것 없음({r.get('reason')})"

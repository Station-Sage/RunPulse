"""라운드 끝 전체 브라우저 스윕 관문 — 실패하면 수정 단위(SWEEP-*)를 큐에 올려 개발로 되돌리고, 상한 초과 시 반영 보류로 바꾼다."""
from __future__ import annotations

import json
from pathlib import Path

from scripts.audit import progress
from scripts.autopilot import notify, queue


def queue_fix(path: Path, st: dict, err: str) -> str:
    """스윕 실패 사유를 담은 수정 단위를 큐 끝에 추가(자동·code). 같은 라운드·시도 번호면 ID 가 같아 중복 추가되지 않는다."""
    iid = f"SWEEP-R{st['round']}-{st.get('sweep_fix', 1)}"
    if any(it.item_id == iid for it in queue.parse(path)):
        return iid
    fails = getattr(err, "failures", [])
    states = ",".join(dict.fromkeys(f["state"] for f in fails))
    vps = ",".join(dict.fromkeys(f["viewport"] for f in fails))
    scope = ["frontend/src/", f"이번 라운드 전체 브라우저 스윕 실패 사유: {err[:500]}"] + [f"실패 조합: {f['state']}|{f['viewport']} — {f['error']}" for f in fails]
    verify = "python3 -m scripts.audit.sweep" + (f" --states {states} --viewports {vps}" if fails else "") + " 로 실패한 조합이 통과하는지 확인"
    meta = {"stage": "queued", "mode": "auto", "attempts": 0, "deps": [], "kind": "code", "critical": True,
            "scope": scope, "verify": [verify], "auto_approved": True}
    with path.open("a", encoding="utf-8") as fh:
        fh.write("\n" + f"- **[{iid}]** 라운드 {st['round']} 전체 스윕 실패 수정 — {err[:200]}\n  <!-- autopilot: {json.dumps(meta, ensure_ascii=False)} -->\n")
    return iid


def gate(st: dict, path: Path, ship, msg: str, full_sweep, limit: int):
    """(조기 종료 메시지|"", ship, msg) — 조기 종료면 라운드를 넘기지 않고 develop 로 되돌아간 것이다."""
    n, err = full_sweep()
    if err and st.get("sweep_fix", 0) < limit:  # 실패 → 수정 단위를 큐에 올리고 개발로 되돌아간다(반영·라운드 증가 없음). 단위가 끝나면 다시 여기서 재스윕
        st["sweep_fix"] = st.get("sweep_fix", 0) + 1
        fid = queue_fix(path, st, err)
        st.update(phase="develop", unit=None)
        notify.send(f"[루프] 라운드 {st['round']} 전체 스윕 실패 — 수정 단위 {fid} 추가({st['sweep_fix']}/{limit}), 통과 후 반영: {err[:200]}" + notify.console_hint())
        targets = [f"{f['state']}|{f['viewport']}" for f in getattr(err, "failures", [])]
        progress.event("sweep_fix", round=st["round"], item=fid, attempt=st["sweep_fix"], limit=limit, targets=targets)
        return f"전체 스윕 실패 — 수정 단위 {fid} 로 개발 재진입({st['sweep_fix']}/{limit})", ship, msg
    if err:
        notify.send(f"[루프] 라운드 {st['round']} 전체 스윕 수정 {limit}회 후에도 실패 — 운영 반영 보류: {err}" + notify.console_hint())
        ship, msg = (lambda _n: {"ran": False}), msg + f" · 스윕 수정 {limit}회 후에도 실패로 반영 보류({err[:80]})"
    else:
        msg += f" · 전체 스윕 {n}셀 통과"
    return "", ship, msg

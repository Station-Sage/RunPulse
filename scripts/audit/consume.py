"""결정함 소비(C1) — 사용자가 고른 결정(chosen)은 BACKLOG 항목을 queued 로 승격하고, 다른 제안 요청(redo)은 설계를 다시 받는다.

관제 콘솔·CLI 가 pending_decisions.json 에 쓴 status 를 루프가 develop 단계 시작 때 읽어 반영한다. 반영된 레코드는 applied(승격) 또는 open(재제안)이 된다.
"""
from __future__ import annotations

from pathlib import Path

from scripts.audit import decisions
from scripts.autopilot import queue

REDO_LIMIT = 3
_UNDO_FIELDS = ("stage", "scope", "verify", "attempts", "fail_kind", "fail_reason", "asks", "answered", "resolution")
_REOPEN_OK_RESOLUTIONS = ("already_done", "dropped")


def _item(path: Path, iid: str):
    return next((i for i in queue.parse(path) if i.item_id == iid), None)


def _promote(rec: dict, path: Path) -> str:
    opt = next((o for o in rec["options"] if o["key"] == rec["choice"]), None)
    act = (opt or {}).get("action", "")
    text = (rec.get("text") or "").strip()
    item = _item(path, rec["id"])
    fields: dict = {"stage": "queued"}
    if act in ("already_done", "dropped"):
        fields = {"stage": "done", "resolution": act}
    elif act == "redefine":
        fields["scope"] = [text] if text else (item.scope if item else [])
        fields["asks"] = 0
    elif act == "scope":
        fields["scope"] = list(item.scope if item else []) + [opt["name"] + (f" — {text}" if text else "")]
        fields["answered"] = list(item.answered if item else []) + [rec["id"]]
    elif act == "retry_verify":
        if text:
            fields["verify"] = [text]
        fields.update(attempts=0, fail_kind="", fail_reason="")
    elif act == "retry_scope":
        fields["scope"] = list(item.scope if item else []) + [f"이전 verify 실패 출력: {rec.get('why', '')[:500]}"]
        fields.update(attempts=0, fail_kind="", fail_reason="")
    elif act == "retry_note":
        note = f"사용자 지시: {text}" if text else f"이전 verify 실패 출력: {rec.get('why', '')[:500]}"
        fields["scope"] = list(item.scope if item else []) + [note]
        fields.update(attempts=0, fail_kind="", fail_reason="")
    elif act == "add_target":
        sc = list(item.scope if item else [])
        if rec.get("target") and rec["target"] not in sc:
            sc.append(rec["target"])
        fields.update(scope=sc, attempts=0, fail_kind="", fail_reason="")
    elif act == "install_dep":
        from scripts.autopilot import dep_install
        dep = rec.get("dep") or {}
        ok, msg = dep_install.install(dep.get("eco", ""), dep.get("name", ""))
        if not ok:
            queue.update_item(path, rec["id"], stage="failed", fail_kind="env", fail_reason=f"[env] 의존성 설치 실패: {msg}"[:600])
            rec["status"] = "applied"
            return f"{rec['id']} 의존성 설치 실패 → failed: {msg[:120]}"
        fields.update(attempts=0, fail_kind="", fail_reason="")
    elif act == "retry_env":
        from scripts.autopilot.fail_handling import DEFAULT_VERIFY
        fields.update(verify=[DEFAULT_VERIFY], attempts=0, fail_kind="", fail_reason="")
    elif act == "retry_exec":
        fields.update(attempts=0, fail_kind="", fail_reason="")
    elif rec.get("scope") and rec.get("verify"):
        fields.update(scope=rec["scope"], verify=rec["verify"])
    if item:
        rec["undo"] = {k: getattr(item, k) for k in _UNDO_FIELDS}  # 선택 변경(reopen)용 — 적용 직전 항목 상태
    queue.update_item(path, rec["id"], **fields)
    rec["status"] = "applied"
    return f"{rec['id']} 선택 {rec['choice']}({opt['name'] if opt else '-'}) → {fields['stage']}"


def reopen(rec: dict, path: Path) -> str | None:
    """applied 결정을 되돌려 선택을 다시 받을 수 있게 한다. 불가하면 사유 문자열, 성공이면 None.

    항목이 이미 개발 중·완료(구현 결과 있음)면 되돌릴 수 없다 — queued 이거나, 사용자가 닫은 done(already_done/dropped)만 허용.
    """
    undo = rec.get("undo")
    item = _item(path, rec["id"])
    if not undo or item is None:
        return "되돌릴 수 없음(적용 전 상태 기록 없음)"
    closed = item.stage == "done" and item.resolution in _REOPEN_OK_RESOLUTIONS
    if item.stage != "queued" and not closed:
        return f"이미 진행됨(항목 단계 {item.stage}) — 선택을 바꿀 수 없음"
    queue.update_item(path, rec["id"], **undo)
    rec["status"] = "open"
    rec.pop("undo", None)
    return None


def _redo(rec: dict, path: Path, decide) -> str:
    if rec.get("rounds", 1) >= REDO_LIMIT:
        rec["status"] = "open"
        rec["why"] = f"재제안 {REDO_LIMIT}회 소진 — 직접 지시 필요. " + rec.get("why", "")
        return f"{rec['id']} 재제안 상한({REDO_LIMIT}) — 사용자 직접 결정 대기"
    f = dict(rec.get("finding") or {"kind": rec["kind"]})
    f["fix"] = f"{f.get('fix', '')} (이전 제안 '{rec['summary'][:80]}' 은 거절됨 — 다른 접근으로 설계)"
    d = decide(f)
    dz = d.get("design", {}) or {}
    new = decisions.build(rec["id"], rec.get("finding") or f, {**d, "design": dz})
    new.update(rounds=rec.get("rounds", 1) + 1, created=rec["created"])
    new["finding"] = rec.get("finding") or new["finding"]
    rec.clear()
    rec.update(new)
    return f"{rec['id']} 다른 제안 {rec['rounds']}차 수신 — 결정 대기"


def apply(path: Path, decide, dpath: Path | None = None) -> list[str]:
    """chosen/redo 레코드를 반영하고 한 줄 결과 목록을 돌려준다. 항목이 needs_decision 이 아니면 레코드만 applied 로 닫는다."""
    data = decisions.load(dpath)
    stages = {i.item_id: i.stage for i in queue.parse(path)}
    out = []
    for rec in data:
        if rec.get("kind") in ("initiative", "vision", "deploy_failed"):
            continue  # 버전 전환·비전 개정은 versioning/steward.apply_choice, 반영 실패는 deploy_hold.release 가 처리
        if rec["status"] == "chosen":
            if stages.get(rec["id"]) in ("needs_decision", "failed"):
                out.append(_promote(rec, path))
            else:
                rec["status"] = "applied"
        elif rec["status"] == "redo":
            out.append(_redo(rec, path, decide))
    pruned = decisions.prune(data)
    if out or len(pruned) != len(data) or any(r["status"] == "applied" for r in data):
        decisions.save(pruned, dpath)
    return out

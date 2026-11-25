"""버전 전환 — 이니셔티브 제안 결정(VER-vN)의 선택을 반영한다.

A 승인 → vN 이니셔티브 approved·버전 active(이전 버전 closed)·PLAN.md status approved, 안정화 게이트 초기화, 루프는 설계 단계(idesign)로.
B 보류 → 레코드만 applied 로 닫고 정지 유지(직접 지시 대기). redo → 레코드를 지우고 plan 단계부터 다시 제안.
"""
from __future__ import annotations

import re
from pathlib import Path

from scripts.audit import decisions, docs_ctx, release_plan, stopreason

_STATUS = re.compile(r"^status:.*$", re.M)


def set_doc_status(doc: Path, status: str) -> None:
    """PLAN/DESIGN front-matter 의 status 줄만 바꾼다. 문서가 없으면 무시."""
    try:
        txt = doc.read_text(encoding="utf-8")
    except OSError:
        return
    doc.write_text(_STATUS.sub(f"status: {status}", txt, count=1), encoding="utf-8")


def approve(ver: str, plan: dict, releases: Path | None = None) -> list[str]:
    """plan(dict)을 제자리 갱신 — 승인된 이니셔티브 ID 목록."""
    for k, v in plan["versions"].items():
        if v.get("status") == "active" and k != ver:
            v["status"] = "closed"
    v = plan["versions"][ver]
    v["status"] = "active"
    plan["current"] = ver
    ids = [i for i, ini in v.get("initiatives", {}).items() if ini.get("status") == "proposed"]
    for i in ids:
        v["initiatives"][i]["status"] = "approved"
    set_doc_status((releases or docs_ctx.RELEASES) / ver / "PLAN.md", "approved")
    return ids


def apply_choice(rec: dict, st: dict, *, dpath: Path | None = None, plan_path: Path | None = None, releases: Path | None = None) -> str:
    """kind=initiative 결정 레코드의 선택을 상태 st 와 계획·문서에 반영. 한 줄 결과."""
    ver = rec["id"].removeprefix("VER-")
    data = decisions.load(dpath)
    if rec["status"] == "redo":
        decisions.save([r for r in data if r["id"] != rec["id"]], dpath)
        st.update(phase="plan", stop_reason=None)
        return f"{ver} 재제안 요청 — 계획 단계부터 다시"
    for r in data:
        if r["id"] == rec["id"]:
            r["status"] = "applied"
    decisions.save(data, dpath)
    if rec.get("choice") != "A":
        return f"{ver} 보류 — 직접 지시 대기"
    plan = release_plan.load(plan_path)
    ids = approve(ver, plan, releases)
    release_plan.save(plan, plan_path)
    st.update(phase="idesign", stop_reason=None, fails=0, gate={"clean_rounds": 0, "version_rounds": 0})
    return f"{ver} 승인 — 이니셔티브 {len(ids)}건 설계 착수"


def pending_stop(st: dict) -> bool:
    return st.get("stop_reason") == stopreason.AWAIT_DECISION

"""알고리즘 변경 이력(algo_changelog) → 추세 차트 ◆ 이벤트·재계산 캡션. 상위 지표 변경 전파와 불연속 감지 이벤트 병합 포함."""
from __future__ import annotations

import sqlite3
from typing import Any

from src.metrics.algo_changelog import CHANGELOG, AlgoChange
from src.services.metric_display import display_name
from src.services.metrics_version_events import _ver, recompute_note, version_change_events
from src.utils.db_helpers import get_metric_history


def _calcs() -> list[Any]:
    from src.metrics.engine import ALL_CALCULATORS

    return list(ALL_CALCULATORS)


def _upstream(slug: str, calcs: list[Any]) -> dict[str, str | None]:
    """slug를 만드는 Calculator와 그 상위(requires 역추적) Calculator → via(직접이면 None, 전파면 가장 가까운 입력 지표)."""
    found: dict[str, str | None] = {}
    frontier = [(c, None) for c in calcs if slug in c.produces]
    while frontier:
        c, via = frontier.pop()
        if c.name in found:
            continue
        found[c.name] = via
        for req in c.requires:
            frontier += [(p, via or req) for p in calcs if req in p.produces and p.name not in found]
    return found


def _label(metric: str) -> str:
    return display_name(metric, metric)[0]


def changelog_events(conn: sqlite3.Connection, slug: str, d0: str, d1: str) -> list[dict[str, Any]]:
    """기간 안 changelog 변경(◆). 대표 시계열이 변경일 이후 RunPulse 값일 때만, 같은 날짜는 1건으로 합친다."""
    related = _upstream(slug, _calcs())
    hits: list[tuple[AlgoChange, str | None]] = [
        (c, related[c.calculator]) for c in CHANGELOG if c.calculator in related and c.prev is not None and d0 <= c.date <= d1
    ]
    if not hits:
        return []
    try:
        rows = get_metric_history(conn, slug, scope_type="daily", date_from=d0, date_to=d1)
    except sqlite3.Error:
        return []
    out: list[dict[str, Any]] = []
    for day in sorted({c.date for c, _ in hits}):
        after = next((r for r in rows if r["scope_id"] >= day), None)
        if not after or not str(after.get("provider") or "").startswith("runpulse"):
            continue
        day_hits = [(c, via) for c, via in hits if c.date == day]
        direct = [c for c, via in day_hits if via is None]
        parts = [c.reason if via is None else f"입력 지표({_label(via)}) 변경 · {c.reason}" for c, via in day_hits]
        ev: dict[str, Any] = {"date": day, "kind": "version_change", "source": "changelog", "recomputed": True,
                              "reason": "; ".join(dict.fromkeys(parts))}
        if len(direct) == 1 and len(day_hits) == 1:
            ev.update({"from": direct[0].prev, "to": direct[0].version,
                       "label": f"계산 방식 변경: {_ver(direct[0].prev)}→{_ver(direct[0].version)}"})
        else:
            ev["label"] = "계산 방식 변경"
            if direct:
                ev["to"] = direct[-1].version
        adr = next((c.adr for c, _ in day_hits if c.adr), None)
        if adr:
            ev["adr"] = adr
        via0 = next((via for _, via in day_hits if via), None)
        if via0 and not direct:
            ev["via"] = via0
        out.append(ev)
    return out


def version_events(conn: sqlite3.Connection, slug: str, d0: str, d1: str) -> list[dict[str, Any]]:
    """불연속 감지(data)와 changelog 이벤트 병합 — 같은 버전이면 날짜는 data, 사유는 changelog."""
    data = version_change_events(conn, slug, d0, d1)
    logged = changelog_events(conn, slug, d0, d1)
    versions = {c.version: c for c in CHANGELOG}
    out: list[dict[str, Any]] = []
    used: set[str] = set()
    for e in data:
        e = {**e, "source": "data"}
        match = next((x for x in logged if x["date"] not in used and x.get("to") == e.get("to")), None) if e.get("to") in versions else None
        if match:
            used.add(match["date"])
            e["reason"] = match["reason"]
            e["recomputed"] = False
            if "adr" in match:
                e["adr"] = match["adr"]
        out.append(e)
    return out + [x for x in logged if x["date"] not in used]


def recompute_caption(conn: sqlite3.Connection, slug: str, d0: str, d1: str) -> dict[str, Any] | None:
    """전 기간 재계산 캡션 — changelog 최신 항목(사유 포함) 우선, 없으면 milestones 폴백. 불연속이 있으면 None."""
    if version_change_events(conn, slug, d0, d1):
        return None
    logged = changelog_events(conn, slug, d0, d1)
    if not logged:
        return recompute_note(conn, slug, d0, d1)
    last = logged[-1]
    md = f"{int(last['date'][5:7])}/{int(last['date'][8:10])}"
    ver = f"계산 {_ver(last['to'])}" if last.get("to") else "계산 방식 변경"
    return {"date": last["date"], "to": last.get("to"),
            "text": f"{md}부터 {ver} · 과거 값도 모두 다시 계산됐어요 — {last['reason']}"}

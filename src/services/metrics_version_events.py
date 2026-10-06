"""추세 차트의 계산 버전 마커(◆) — 대표 시계열에서 (provider, algorithm_version)이 바뀐 첫 날 + 전 기간 재계산 캡션."""
from __future__ import annotations

import sqlite3
from typing import Any

from src.utils.db_helpers import get_metric_history

_PROV = {"intervals": "Intervals", "garmin": "Garmin", "strava": "Strava"}


def _prov_label(p: str | None) -> str:
    p = p or ""
    return "RunPulse" if p.startswith("runpulse") else _PROV.get(p, p)


def _ver(v: Any) -> str:
    return f"v{v}" if v else "v1.0"


def version_change_events(conn: sqlite3.Connection, slug: str, d0: str, d1: str) -> list[dict[str, Any]]:
    """기간 내 대표 시계열의 계산 방식·출처 변경일(◆). 불연속이 없으면 빈 리스트."""
    try:
        rows = get_metric_history(conn, slug, scope_type="daily", date_from=d0, date_to=d1)
    except sqlite3.Error:
        return []
    out: list[dict[str, Any]] = []
    prev = None
    for r in rows:
        cur = (r.get("provider"), r.get("algorithm_version"))
        if prev is not None and cur != prev:
            if cur[0] != prev[0]:
                label = f"출처 변경: {_prov_label(prev[0])}→{_prov_label(cur[0])}"
            else:
                label = f"계산 방식 변경: {_ver(prev[1])}→{_ver(cur[1])}"
            out.append({"date": r["scope_id"], "kind": "version_change", "from": prev[1], "to": cur[1], "label": label})
        prev = cur
    return out


def recompute_note(conn: sqlite3.Connection, slug: str, d0: str, d1: str) -> dict[str, Any] | None:
    """시계열 안 불연속이 없을 때 쓰는 '전 기간 다시 계산됨' 캡션. 재계산 기록이 없거나 기간 안에 불연속이 있으면 None."""
    if version_change_events(conn, slug, d0, d1):
        return None
    try:
        m = conn.execute(
            "SELECT date FROM milestones WHERE type='algo_recompute' AND metric_name=? ORDER BY date DESC, id DESC LIMIT 1",
            (slug,),
        ).fetchone()
        if not m:
            return None
        last = get_metric_history(conn, slug, scope_type="daily", date_from=d0, date_to=d1)
    except sqlite3.Error:
        return None
    if not last:
        return None
    ver = _ver(last[-1].get("algorithm_version"))
    day = m[0]
    md = f"{int(day[5:7])}/{int(day[8:10])}"
    return {"date": day, "to": last[-1].get("algorithm_version"), "text": f"{md}부터 계산 {ver} · 과거 값도 모두 다시 계산됐어요"}

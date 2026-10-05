"""예측 추세의 기준 대회 교체 이벤트(◇) — race_pred_vdot json 의 anchor.activity_id 가 전날과 달라진 첫 날."""
from __future__ import annotations

import json
import sqlite3
from typing import Any

from src.utils.db_helpers import get_metric_history

PRED_SLUGS = frozenset({"race_pred_5k_sec", "race_pred_10k_sec", "race_pred_half_sec", "race_pred_marathon_sec"})


def load_json(row: dict | None) -> dict:
    """metric_store 행의 json_value 를 dict 로. 비었거나 깨졌으면 {}."""
    raw = (row or {}).get("json_value")
    try:
        return json.loads(raw) if raw else {}
    except (TypeError, ValueError):
        return {}


def _dist_label(distance_m: float | None) -> str:
    if not distance_m:
        return ""
    km = distance_m / 1000
    if km >= 40:
        return "마라톤 "
    if km >= 20:
        return "하프 "
    if km >= 8:
        return "10K "
    if km >= 4:
        return "5K "
    return f"{km:.1f}km "


def basis_change_events(conn: sqlite3.Connection, slug: str, d0: str, d1: str) -> list[dict[str, Any]]:
    """기간 내 기준 대회 교체일 목록. 예측 slug 가 아니거나 anchor 키가 없으면 빈 리스트."""
    if slug not in PRED_SLUGS:
        return []
    try:
        rows = get_metric_history(conn, "race_pred_vdot", scope_type="daily", date_from=d0, date_to=d1)
    except sqlite3.Error:
        return []
    changes: list[tuple[str, int, str | None]] = []
    prev = None
    for r in rows:
        a = load_json(r).get("anchor") or {}
        aid = a.get("activity_id")
        if aid is None:
            continue
        if prev is not None and aid != prev:
            changes.append((r["scope_id"], aid, a.get("date")))
        prev = aid
    if not changes:
        return []
    ids = [c[1] for c in changes]
    try:
        dist = dict(conn.execute(
            f"SELECT id, distance_m FROM v_canonical_activities WHERE id IN ({','.join('?' * len(ids))})", ids
        ).fetchall())
    except sqlite3.Error:
        dist = {}
    return [
        {"date": day, "kind": "basis_change", "activity_id": aid,
         "label": f"기준 대회 변경: {_dist_label(dist.get(aid))}{adate or ''}".rstrip()}
        for day, aid, adate in changes
    ]

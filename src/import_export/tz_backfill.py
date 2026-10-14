"""Strava 시간대 백필·되돌리기 (TZ T4, ADR-052 TZ-9) — 기본 dry-run, 적용은 apply=True 일 때만.

대상: tz_source 가 추정 등급(fallback·neighbor·peer_derived)인 Strava 행. Strava API(`api_fetch`)와
교차 소스 피어로 재해석해 순위가 같거나 높을 때만 start_time 을 갱신하고, 변경은 payload `tz_history`
에 run_id 와 함께 남긴다. `revert_run` 은 그 기록으로 복원하고 `tz_pinned` 로 자동 재교정에서 제외한다.
dry-run 은 SAVEPOINT 안에서 실제 경로를 그대로 실행한 뒤 롤백한다(예상 그룹 변화 포함).
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime

from src.import_export.strava_tz import (
    CONFIRMED, StravaTzLookup, rank_of, resolve_strava_start,
)
from src.import_export.strava_tz_apply import (
    _PAYLOAD_TYPES, apply_to_existing, reeval_group,
)
from src.utils.tz_peers import PeerTime, PeerTzIndex

_ESTIMATED = ("fallback", "neighbor", "peer_derived")


def _rows(conn: sqlite3.Connection) -> list[tuple[str, str, dict]]:
    out = []
    for et in _PAYLOAD_TYPES:
        for sid, payload in conn.execute(
                "SELECT entity_id, payload FROM source_payloads WHERE source='strava' AND entity_type=?", (et,)):
            try:
                out.append((str(sid), et, json.loads(payload)))
            except (ValueError, TypeError):
                continue
    return out


def _utc(p: dict) -> datetime | None:
    try:
        return datetime.fromisoformat(p["start_date_utc"][:19])
    except (KeyError, TypeError, ValueError):
        return None


def run_backfill(conn: sqlite3.Connection, config: dict | None = None, *, apply: bool = False,
                 limit: int | None = None, lookup: StravaTzLookup | None = None,
                 run_id: str | None = None) -> dict:
    """추정 등급 Strava 행을 재해석. dry-run 이면 DB 를 바꾸지 않는다."""
    run_id = run_id or uuid.uuid4().hex[:8]
    lookup = lookup or StravaTzLookup(config)
    peers = PeerTzIndex.build(conn)
    rows = _rows(conn)
    for sid, _, p in rows:
        if p.get("tz_source", "").split(":")[0] in CONFIRMED and (u := _utc(p)) and p.get("start_time"):
            try:
                peers.add_confirmed(PeerTime("strava", sid, u, datetime.fromisoformat(p["start_time"][:19]),
                                             None, "direct"))
            except ValueError:
                pass
    targets = [(s, e, p) for s, e, p in rows
               if p.get("tz_source", "").split(":")[0] in _ESTIMATED and not p.get("tz_pinned") and _utc(p)]
    targets.sort(key=lambda t: t[2].get("start_date_utc", ""))
    res = {"run_id": run_id, "applied": apply, "checked": 0, "changed": 0, "date_changed": 0,
           "group_changed": 0, "api_calls": 0, "rows": []}
    conn.execute("SAVEPOINT tz_backfill")
    for sid, _, p in targets[:limit]:
        res["checked"] += 1
        utc = _utc(p)
        dist = (p.get("distance_km") or 0) * 1000
        old = conn.execute("SELECT id, start_time FROM activity_summaries WHERE source='strava' AND source_id=?",
                           (sid,)).fetchone()
        if not old:
            continue
        local, src, peer = resolve_strava_start(conn, sid, utc, dist, peers=peers)
        if rank_of(src) < 5 and lookup.available:
            res["api_calls"] += 1
            api = lookup.fetch(sid)
            if api:
                local, src, peer = resolve_strava_start(conn, sid, utc, dist, api=api, peers=peers)
                if src == "api_payload":
                    src = "api_fetch"
        if not apply_to_existing(conn, sid, local, src, peer, run_id=run_id, regroup=True):
            continue
        hist = _history(conn, sid)[-1]
        res["changed"] += 1
        res["date_changed"] += hist["from"][:10] != hist["to"][:10]
        res["group_changed"] += hist.get("prev_group_id") != hist.get("new_group_id")
        res["rows"].append({"source_id": sid, "id": old[0], **hist})
    conn.execute("RELEASE tz_backfill" if apply else "ROLLBACK TO tz_backfill")
    if not apply:
        conn.execute("RELEASE tz_backfill")
    else:
        conn.commit()
    return res


def _history(conn: sqlite3.Connection, sid: str) -> list[dict]:
    for s, _, p in _rows_for(conn, sid):
        return list(p.get("tz_history") or [])
    return []


def _rows_for(conn: sqlite3.Connection, sid: str):
    for et in _PAYLOAD_TYPES:
        r = conn.execute("SELECT payload FROM source_payloads WHERE source='strava' AND entity_type=?"
                         " AND entity_id=?", (et, sid)).fetchone()
        if r:
            yield sid, et, json.loads(r[0])


def list_run(conn: sqlite3.Connection, run_id: str) -> list[dict]:
    """run_id 로 변경된 행의 이력 항목 목록."""
    out = []
    for sid, _, p in _rows(conn):
        for h in p.get("tz_history") or []:
            if h.get("run_id") == run_id:
                out.append({"source_id": sid, **h})
    return out


def revert_run(conn: sqlite3.Connection, run_id: str, *, apply: bool = False) -> dict:
    """run_id 변경을 되돌린다(이전 start_time·tz_source 복원, 그룹 재평가, tz_pinned 표시)."""
    res = {"run_id": run_id, "applied": apply, "reverted": 0, "rows": []}
    conn.execute("SAVEPOINT tz_revert")
    for sid, et, p in _rows(conn):
        hist = p.get("tz_history") or []
        hit = next((h for h in reversed(hist) if h.get("run_id") == run_id), None)
        if hit is None:
            continue
        row = conn.execute("SELECT id FROM activity_summaries WHERE source='strava' AND source_id=?",
                           (sid,)).fetchone()
        if not row:
            continue
        conn.execute("UPDATE activity_summaries SET start_time=? WHERE id=?", (hit["from"], row[0]))
        reeval_group(conn, row[0])
        p.update({"start_time": hit["from"], "tz_source": hit["from_source"], "tz_pinned": True,
                  "tz_history": [h for h in hist if h is not hit]})
        conn.execute("UPDATE source_payloads SET payload=? WHERE source='strava' AND entity_type=?"
                     " AND entity_id=?", (json.dumps(p, ensure_ascii=False), et, sid))
        res["reverted"] += 1
        res["rows"].append({"source_id": sid, "restored": hit["from"], "tz_source": hit["from_source"]})
    if apply:
        conn.execute("RELEASE tz_revert")
        conn.commit()
    else:
        conn.execute("ROLLBACK TO tz_revert")
        conn.execute("RELEASE tz_revert")
    return res

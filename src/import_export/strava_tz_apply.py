"""Strava 가져오기에 시간대 체인을 적용하는 컨텍스트 (TZ T2/T3, ADR-052).

배치 시작 시 1회 피어 색인을 만들고, 행마다 `resolve` 로 현지 시각·tz_source 를 얻는다.
기존 행은 새 해석의 순위 ≥ 기존 순위일 때만 start_time 을 갱신한다 (`tz_pinned`·수동 보정 행은 보호).
"""
from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone

from src.import_export.strava_tz import (
    CONFIRMED, StravaTzLookup, may_overwrite, resolve_strava_start,
)
from src.utils.tz_peers import PeerTime, PeerTzIndex

logger = logging.getLogger(__name__)

_PAYLOAD_TYPES = ("csv_export", "archive_import")
_HISTORY_MAX = 5


def _parse_local(s: str) -> datetime | None:
    try:
        return datetime.fromisoformat(s[:19])
    except ValueError:
        return None


class TzContext:
    def __init__(self, conn: sqlite3.Connection, config: dict | None = None):
        self.conn = conn
        self.peers = PeerTzIndex.build(conn)
        self.lookup = StravaTzLookup(config)
        self.counts: dict[str, int] = {}
        self.conflicts = 0

    def resolve(self, source_id: str, utc_naive: datetime, distance_m: float | None,
                fit_local: datetime | None = None) -> tuple[str, str, dict | None]:
        local, tz_source, peer = resolve_strava_start(
            self.conn, source_id, utc_naive, distance_m, fit_local=fit_local, peers=self.peers)
        kind = tz_source.split(":")[0]
        self.counts[kind] = self.counts.get(kind, 0) + 1
        if peer and peer.get("conflicts"):
            self.conflicts += 1
        if kind in CONFIRMED and (lt := _parse_local(local)):
            self.peers.add_confirmed(PeerTime("strava", str(source_id), utc_naive, lt, distance_m, "direct"))
        return local, tz_source, peer

    def summary(self) -> dict:
        return {
            "tz_resolved": dict(self.counts),
            "tz_lookup_status": self.lookup.status,
            "tz_peer_conflicts": self.conflicts,
            "tz_backfill_pending": self.counts.get("neighbor", 0) + self.counts.get("fallback", 0)
            + self.counts.get("peer_derived", 0),
        }

    def log_line(self) -> str:
        c = self.counts
        cross = c.get("peer_direct", 0) + c.get("peer_derived", 0)
        return (f"[strava_csv] 시간대 교차소스 {cross}건·차용 {c.get('neighbor', 0)}건·"
                f"폴백 {c.get('fallback', 0)}건 (Strava 연결: {self.lookup.status})")


def tz_payload_fields(utc_naive: datetime | None, tz_source: str, peer: dict | None) -> dict:
    out: dict = {"tz_source": tz_source}
    if utc_naive is not None:
        out["start_date_utc"] = utc_naive.isoformat()
    if peer:
        out["tz_peer"] = peer
    return out


def _load_payload(conn: sqlite3.Connection, source_id: str) -> tuple[str, dict] | None:
    for et in _PAYLOAD_TYPES:
        row = conn.execute(
            "SELECT payload FROM source_payloads WHERE source='strava' AND entity_type=? AND entity_id=?",
            (et, str(source_id))).fetchone()
        if row:
            try:
                return et, json.loads(row[0])
            except (ValueError, TypeError):
                return None
    return None


def apply_to_existing(conn: sqlite3.Connection, source_id: str, new_start: str, new_tz_source: str,
                      peer: dict | None) -> bool:
    """기존 Strava 행의 start_time 을 순위 규칙으로 갱신. 갱신했으면 True."""
    loaded = _load_payload(conn, source_id)
    if loaded is None:
        return False
    et, payload = loaded
    old_src = payload.get("tz_source")
    if payload.get("tz_pinned") or not old_src or not may_overwrite(new_tz_source, old_src):
        return False
    row = conn.execute("SELECT id, start_time FROM activity_summaries WHERE source='strava' AND source_id=?",
                       (str(source_id),)).fetchone()
    if not row or (row[1] == new_start and old_src == new_tz_source):
        return False
    hist = list(payload.get("tz_history") or [])
    hist.append({"from": row[1], "from_source": old_src, "to": new_start, "to_source": new_tz_source,
                 "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")})
    payload.update({"start_time": new_start, "tz_source": new_tz_source, "tz_history": hist[-_HISTORY_MAX:]})
    if peer:
        payload["tz_peer"] = peer
    else:
        payload.pop("tz_peer", None)
    conn.execute("UPDATE activity_summaries SET start_time=? WHERE id=?", (new_start, row[0]))
    conn.execute("UPDATE source_payloads SET payload=? WHERE source='strava' AND entity_type=? AND entity_id=?",
                 (json.dumps(payload, ensure_ascii=False), et, str(source_id)))
    return True

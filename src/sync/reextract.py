"""제자리 재추출 — 기존 activity_summaries id 를 유지한 채 source_payloads 에서 랩·스트림·활동 메트릭을 다시 뽑는다(P7-PRED-13).

reprocess_all 은 activity_summaries 를 지우고 다시 만들어 id 가 전부 바뀌고(참조 테이블 파손),
payload 없는 활동이 사라지며, detail/streams payload 의 옛 activity_id 로 랩·스트림을 붙인다(BUG, REVIEW-08 §R3).
이 모듈은 API 호출 없이 (source, source_id) → 기존 id 로 매핑해 랩(UPSERT)·스트림(DELETE+INSERT)·활동 메트릭(UPSERT)만 갱신한다.
"""
from __future__ import annotations

import json
import logging
import sqlite3

from src.sync._helpers import save_laps, save_metrics, save_streams
from src.sync.extractors import get_extractor

log = logging.getLogger(__name__)

_PAYLOAD_SQL = ("SELECT payload FROM source_payloads WHERE source = ? AND entity_type = ? AND entity_id = ? "
                "ORDER BY id DESC LIMIT 1")


def orphan_activity_count(conn: sqlite3.Connection, source: str | None = None) -> int:
    """activity_summary payload 가 없는 활동 수 — reprocess_all(clear_first=True) 시 영구 삭제될 행."""
    q = ("SELECT count(*) FROM activity_summaries a WHERE NOT EXISTS (SELECT 1 FROM source_payloads p "
         "WHERE p.source = a.source AND p.entity_type = 'activity_summary' AND p.entity_id = a.source_id)")
    return conn.execute(q + (" AND a.source = ?" if source else ""), (source,) if source else ()).fetchone()[0]


def reextract_laps_streams(conn: sqlite3.Connection, source: str = "garmin", dry_run: bool = False) -> dict:
    """반환 {"activities", "laps", "streams", "metrics", "missing_payload", "errors"}. dry_run 이면 쓰기 없이 집계만.
    활동 메트릭(예: gap)도 summary/detail payload 에서 다시 뽑아 UPSERT 한다(provider = source)."""
    stats = {"activities": 0, "laps": 0, "streams": 0, "metrics": 0, "missing_payload": 0, "errors": 0}
    ex = get_extractor(source)
    rows = conn.execute("SELECT id, source_id FROM activity_summaries WHERE source = ? ORDER BY id", (source,)).fetchall()
    for aid, sid in rows:
        try:
            splits = (conn.execute(_PAYLOAD_SQL, (source, "activity_splits", str(sid))).fetchone()
                      or conn.execute(_PAYLOAD_SQL, (source, "activity_detail", str(sid))).fetchone())
            streams = conn.execute(_PAYLOAD_SQL, (source, "activity_streams", str(sid))).fetchone()
            if not splits and not streams:
                stats["missing_payload"] += 1
                continue
            stats["activities"] += 1
            summ = conn.execute(_PAYLOAD_SQL, (source, "activity_summary", str(sid))).fetchone()
            det = conn.execute(_PAYLOAD_SQL, (source, "activity_detail", str(sid))).fetchone()
            if summ:
                ms = ex.extract_activity_metrics(json.loads(summ[0]), json.loads(det[0]) if det else None)
                stats["metrics"] += len(ms or [])
                if ms and not dry_run:
                    save_metrics(conn, "activity", str(aid), source, ms)
            if splits:
                laps = ex.extract_activity_laps(json.loads(splits[0]))
                stats["laps"] += len(laps or [])
                if laps and not dry_run:
                    save_laps(conn, aid, laps)
            if streams:
                srows = ex.extract_activity_streams(json.loads(streams[0]))
                stats["streams"] += len(srows or [])
                if srows and not dry_run:
                    save_streams(conn, aid, srows)
        except Exception as e:                      # 한 활동 실패로 전체 중단 금지
            log.error("reextract %s/%s: %s", source, sid, e)
            stats["errors"] += 1
    if not dry_run:
        conn.commit()
    return stats


if __name__ == "__main__":        # python3 -m src.sync.reextract --db <path> [--dry-run]
    import argparse

    ap = argparse.ArgumentParser(description="Garmin 랩·스트림 제자리 재추출(활동 id 유지)")
    ap.add_argument("--db", required=True)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    with sqlite3.connect(a.db) as _c:
        print(reextract_laps_streams(_c, dry_run=a.dry_run))

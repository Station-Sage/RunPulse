"""Garmin 활동 강제 재수집 백필 잡 — 이미 받은 활동의 detail·심박존·날씨·splits·스트림을 다시 받아 A1~A3 수정을 반영.

한 번에 N건만 처리(최신순·러닝 우선), 429 를 만나면 즉시 중단한다. 완료 목록은 DB 옆 JSON 에 남겨 이어서 실행한다.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from src.sync.extractors import get_extractor
from src.sync.garmin_activity_extras import RateLimitStop
from src.sync.garmin_activity_sync import _sync_single
from src.sync.rate_limiter import RateLimiter
from src.sync.sync_result import SyncResult

log = logging.getLogger(__name__)

_RUN_TYPES = ("running", "trail_running", "treadmill_running", "track_running", "virtual_run")


def _load_done(path: Path) -> set[str]:
    try:
        return set(json.loads(path.read_text()))
    except (OSError, ValueError):
        return set()


def pending_ids(conn, done: set[str], limit: int, sport: str = "running") -> list[tuple[str, dict]]:
    """미처리 Garmin 활동의 (source_id, 저장된 summary raw) — 최신순. sport=running|other|all."""
    rows = conn.execute(
        "SELECT p.entity_id, p.payload FROM source_payloads p "
        "JOIN activity_summaries a ON a.id = p.activity_id "
        "WHERE p.source='garmin' AND p.entity_type='activity_summary' "
        "ORDER BY a.start_time DESC"
    ).fetchall()
    out = []
    for eid, payload in rows:
        if eid in done:
            continue
        raw = json.loads(payload)
        at = raw.get("activityType")
        key = at.get("typeKey", "") if isinstance(at, dict) else str(at or "")
        is_run = key in _RUN_TYPES or "running" in key
        if sport == "running" and not is_run or sport == "other" and is_run:
            continue
        out.append((eid, raw))
        if len(out) >= limit:
            break
    return out


def run_backfill(conn, api, state_path: Path, limit: int = 20, sport: str = "running",
                 include_streams: bool = True, _sleep_fn=None) -> SyncResult:
    result = SyncResult(source="garmin", job_type="backfill")
    extractor = get_extractor("garmin")
    limiter = RateLimiter("garmin", sleep_fn=_sleep_fn)
    done = _load_done(state_path)
    todo = pending_ids(conn, done, limit, sport)
    result.total_items = len(todo)
    for sid, raw in todo:
        try:
            _sync_single(conn, api, extractor, limiter, result, raw, include_streams, force=True)
            conn.commit()
            if limiter._consecutive_429:      # 내부 재시도가 삼킨 429 — 불완전 수집이라 완료로 치지 않고 멈춘다
                raise RateLimitStop()
            result.synced_count += 1
            done.add(sid)
        except RateLimitStop:
            conn.commit()
            result.status, result.error_code, result.http_status = "partial", "rate_limited", 429
            result.retry_after = "rate_limited"
            break
        except Exception as e:
            log.error("[garmin/backfill] %s 실패: %s", sid, e)
            conn.rollback()
            result.error_count += 1
            result.errors.append((sid, str(e)))
    state_path.write_text(json.dumps(sorted(done)))
    return result

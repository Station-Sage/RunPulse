"""성능 최적화 — 배치 데이터 로더 + TTL 캐시.

N+1 쿼리를 제거하고 개별 메트릭 로딩을 배치로 통합.
페이지별 TTL 캐시로 반복 요청 시 DB 재조회 방지.
"""
from __future__ import annotations

import json
import sqlite3
import time
from typing import Any, Callable

# ── TTL 캐시 ─────────────────────────────────────────────────────────────────
_PAGE_CACHE_TTL = 30  # 초
_page_cache: dict[str, dict[str, Any]] = {}


def cached_page(page_key: str, db_path: str, builder: Callable[[], str]) -> str:
    """페이지 HTML을 TTL 캐시로 반환. 캐시 유효 시 builder 호출 생략."""
    key = f"{page_key}:{db_path}"
    now = time.monotonic()
    entry = _page_cache.get(key)
    if entry and now - entry["ts"] < _PAGE_CACHE_TTL:
        return entry["html"]
    html = builder()
    _page_cache[key] = {"ts": now, "html": html}
    return html


def invalidate_cache(db_path: str | None = None) -> None:
    """캐시 무효화. db_path 지정 시 해당 DB만, 없으면 전체."""
    if db_path is None:
        _page_cache.clear()
    else:
        to_del = [k for k in _page_cache if k.endswith(f":{db_path}")]
        for k in to_del:
            del _page_cache[k]


def load_metrics_batch(
    conn: sqlite3.Connection,
    target_date: str,
    metric_names: list[str],
) -> dict[str, float | None]:
    """여러 메트릭을 1회 쿼리로 로드. 각 메트릭의 최신 값 반환.

    activity_id IS NULL인 일별 메트릭 대상. date <= target_date 중 최신.
    """
    if not metric_names:
        return {}
    ph = ",".join("?" * len(metric_names))
    rows = conn.execute(
        f"""SELECT metric_name, metric_value
            FROM computed_metrics
            WHERE metric_name IN ({ph})
              AND activity_id IS NULL AND date <= ?
            ORDER BY date DESC""",
        (*metric_names, target_date),
    ).fetchall()
    result: dict[str, float | None] = {n: None for n in metric_names}
    for name, val in rows:
        if name in result and result[name] is None and val is not None:
            result[name] = float(val)
    return result


def load_metrics_json_batch(
    conn: sqlite3.Connection,
    target_date: str,
    metric_names: list[str],
) -> dict[str, dict | None]:
    """여러 메트릭의 JSON을 1회 쿼리로 로드."""
    if not metric_names:
        return {}
    ph = ",".join("?" * len(metric_names))
    rows = conn.execute(
        f"""SELECT metric_name, metric_json
            FROM computed_metrics
            WHERE metric_name IN ({ph})
              AND activity_id IS NULL AND date <= ?
            ORDER BY date DESC""",
        (*metric_names, target_date),
    ).fetchall()
    result: dict[str, dict | None] = {n: None for n in metric_names}
    for name, mj in rows:
        if name in result and result[name] is None and mj:
            try:
                result[name] = json.loads(mj)
            except Exception:
                pass
    return result


def load_activity_metrics_batch(
    conn: sqlite3.Connection,
    activity_ids: list[int],
    metric_names: list[str],
) -> dict[int, dict[str, float | None]]:
    """여러 활동의 메트릭을 1회 쿼리로 로드. N+1 제거."""
    if not activity_ids or not metric_names:
        return {}
    id_ph = ",".join("?" * len(activity_ids))
    name_ph = ",".join("?" * len(metric_names))
    rows = conn.execute(
        f"""SELECT activity_id, metric_name, metric_value
            FROM computed_metrics
            WHERE activity_id IN ({id_ph})
              AND metric_name IN ({name_ph})""",
        (*activity_ids, *metric_names),
    ).fetchall()
    result: dict[int, dict[str, float | None]] = {
        aid: {n: None for n in metric_names} for aid in activity_ids
    }
    for aid, name, val in rows:
        if aid in result and name in result[aid]:
            result[aid][name] = float(val) if val is not None else None
    return result


def load_darp_batch(
    conn: sqlite3.Connection,
    target_date: str,
) -> dict[str, dict]:
    """DARP 4개 거리를 1회 쿼리로 로드."""
    names = ["DARP_5k", "DARP_10k", "DARP_half", "DARP_full"]
    ph = ",".join("?" * len(names))
    rows = conn.execute(
        f"""SELECT metric_name, metric_value, metric_json
            FROM computed_metrics
            WHERE metric_name IN ({ph})
              AND activity_id IS NULL AND date <= ?
            ORDER BY date DESC""",
        (*names, target_date),
    ).fetchall()
    result: dict[str, dict] = {}
    for name, val, mj in rows:
        dist_key = name.split("_", 1)[1]
        if dist_key in result:
            continue
        if val is not None:
            try:
                parsed = json.loads(mj) if mj else {}
            except Exception:
                parsed = {}
            result[dist_key] = parsed or {"pace_sec_km": float(val)}
    return result

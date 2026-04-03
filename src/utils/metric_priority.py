"""RunPulse 메트릭 우선순위 해소 (Provider Priority Resolution) v0.3

같은 (scope_type, scope_id, metric_name)에 여러 provider가 있을 때,
UI에 보여줄 대표값(is_primary=1)을 결정합니다.

우선순위 (낮을수록 우선):
  user(0) > runpulse:ml(10) > runpulse:formula(20) > runpulse:rule(30)
  > garmin(100) > intervals(110) > strava(120) > runalyze(130)

사용법:
    from src.utils.metric_priority import resolve_primary, resolve_all_primaries
    resolve_primary(conn, "activity", "511", "trimp")
"""

from __future__ import annotations

import logging
import sqlite3

log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Provider Priority Table
# ─────────────────────────────────────────────────────────────────────────────

PROVIDER_PRIORITY: list[tuple[str, int]] = [
    ("user", 0),
    ("runpulse:ml", 10),
    ("runpulse:formula", 20),
    ("runpulse:rule", 30),
    ("garmin", 100),
    ("intervals", 110),
    ("strava", 120),
    ("runalyze", 130),
]

_DEFAULT_PRIORITY = 999


def get_provider_priority(provider: str) -> int:
    """provider 문자열의 우선순위 반환. 낮을수록 높은 우선순위."""
    for prefix, priority in PROVIDER_PRIORITY:
        if provider == prefix or provider.startswith(prefix + ":") or provider.startswith(prefix + "_"):
            return priority
    return _DEFAULT_PRIORITY


# ─────────────────────────────────────────────────────────────────────────────
# Primary Resolution
# ─────────────────────────────────────────────────────────────────────────────

def resolve_primary(
    conn: sqlite3.Connection,
    scope_type: str,
    scope_id: str,
    metric_name: str,
) -> int | None:
    """특정 (scope_type, scope_id, metric_name)에 대해 is_primary 재결정.

    Returns: primary로 선택된 metric_store.id 또는 None.
    """
    rows = conn.execute(
        "SELECT id, provider FROM metric_store "
        "WHERE scope_type = ? AND scope_id = ? AND metric_name = ?",
        (scope_type, scope_id, metric_name),
    ).fetchall()

    if not rows:
        return None

    # 모든 행 is_primary=0 리셋
    ids = [r[0] for r in rows]
    placeholders = ",".join("?" * len(ids))
    conn.execute(
        f"UPDATE metric_store SET is_primary = 0 WHERE id IN ({placeholders})",
        ids,
    )

    # 우선순위가 가장 높은(숫자가 낮은) 행 선택
    best_id: int | None = None
    best_rank: int = _DEFAULT_PRIORITY + 1

    for row_id, provider in rows:
        rank = get_provider_priority(provider)
        if rank < best_rank:
            best_rank = rank
            best_id = row_id

    if best_id is not None:
        conn.execute(
            "UPDATE metric_store SET is_primary = 1 WHERE id = ?",
            (best_id,),
        )

    return best_id


def resolve_for_scope(
    conn: sqlite3.Connection,
    scope_type: str,
    scope_id: str,
) -> int:
    """특정 scope의 모든 metric_name에 대해 is_primary 재결정.

    Returns: primary가 설정된 메트릭 수.
    """
    names = conn.execute(
        "SELECT DISTINCT metric_name FROM metric_store "
        "WHERE scope_type = ? AND scope_id = ?",
        (scope_type, scope_id),
    ).fetchall()

    count = 0
    for (name,) in names:
        if resolve_primary(conn, scope_type, scope_id, name) is not None:
            count += 1
    return count


def resolve_all_primaries(conn: sqlite3.Connection) -> int:
    """DB 전체의 모든 (scope_type, scope_id, metric_name) 그룹에 대해 is_primary 재결정.

    주로 초기 데이터 로드나 reprocess 후 호출합니다.

    Returns: primary가 설정된 총 그룹 수.
    """
    groups = conn.execute(
        "SELECT DISTINCT scope_type, scope_id, metric_name FROM metric_store"
    ).fetchall()

    count = 0
    for scope_type, scope_id, metric_name in groups:
        if resolve_primary(conn, scope_type, scope_id, metric_name) is not None:
            count += 1

    log.info("resolve_all_primaries: %d 그룹 처리 완료", count)
    return count

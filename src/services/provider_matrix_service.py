"""Provider 정체성 매트릭스 서비스 — 기간 집계 소스별 비교 (3-G-1).

읽기 전용. DB 쓰기 없음.
첫 번째 인자는 sqlite3.Connection.

SEMANTIC_GROUPS 13개 한정(설계 근거: DECISIONS.md의
[P7-IMPL-PROVIDER-MATRIX] 항목 — 03c-library.md §3-G 서두가 명시한
"시맨틱 그룹 13개 × Provider 4개" 기준, 목업 예시 행은 삽화). 기간 집계는
그룹 내 (metric_name, provider) 조합마다 "기간 내 가장 최근 활동에서 그
provider가 보고한 값" 하나를 대표값으로 사용 — 평균/합산 아님.

설계 문서: v0.3/data/phase-7-ui-renewal/04-component-catalog.md C4
"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from src.services.provider_comparison_service import (
    _build_values,
    _calc_discrepancy,
    _ordered_providers,
    _preferred_provider,
)
from src.utils.dedup import _SOURCE_PRIORITY
from src.utils.metric_groups import SEMANTIC_GROUPS


def get_provider_comparison_period(
    conn: sqlite3.Connection,
    days: int = 28,
    discrepancy_threshold: float = 5.0,
) -> dict:
    """기간 내 SEMANTIC_GROUPS 13개 × Provider 비교.

    그룹별 (metric_name, provider) 값은 기간 내 가장 최근 활동의 값을 사용.
    """
    conn.row_factory = sqlite3.Row
    end = date.today()
    start = end - timedelta(days=days - 1)
    start_s = start.isoformat()
    end_excl_s = (end + timedelta(days=1)).isoformat()

    canon_rows = conn.execute(
        "SELECT id, matched_group_id FROM v_canonical_activities"
        " WHERE start_time >= ? AND start_time < ? ORDER BY start_time DESC",
        (start_s, end_excl_s),
    ).fetchall()
    if not canon_rows:
        return {"mode": "period", "days": days, "state": "no_data", "rows": []}

    group_ids = [r["matched_group_id"] for r in canon_rows if r["matched_group_id"]]
    period_primary_source = _mode_primary_source(conn, group_ids)

    sibling_map: dict[int, list[int]] = {}
    all_scope_ids: set[int] = set()
    for r in canon_rows:
        cid, gid = r["id"], r["matched_group_id"]
        if gid:
            sibs = [s["id"] for s in conn.execute(
                "SELECT id FROM activity_summaries WHERE matched_group_id = ?", (gid,)
            ).fetchall()]
        else:
            sibs = [cid]
        sibling_map[cid] = sibs
        all_scope_ids.update(sibs)

    placeholders = ",".join("?" * len(all_scope_ids))
    metric_rows = conn.execute(
        f"SELECT scope_id, metric_name, provider, numeric_value, text_value"
        f" FROM metric_store WHERE scope_type='activity' AND scope_id IN ({placeholders})",
        [str(i) for i in all_scope_ids],
    ).fetchall()
    metric_idx: dict[tuple, dict] = {}
    for mr in metric_rows:
        d = dict(mr)
        metric_idx[(int(d["scope_id"]), d["metric_name"], d["provider"])] = d

    rows: list[dict] = []
    for group_name, group_def in SEMANTIC_GROUPS.items():
        cells: dict[str, dict] = {}
        for canon in canon_rows:  # start_time DESC = 최신부터
            for metric_name, provider in group_def["members"]:
                if provider in cells:
                    continue
                for sib_id in sibling_map[canon["id"]]:
                    key = (sib_id, metric_name, provider)
                    if key in metric_idx:
                        d = metric_idx[key]
                        val = d["numeric_value"] if d["numeric_value"] is not None else d["text_value"]
                        cells[provider] = {"value": val, "available": val is not None}
                        break

        if not cells or not any(c["available"] for c in cells.values()):
            continue

        all_providers = _ordered_providers({p for (_, _, p) in metric_idx.keys()})
        values_dict = _build_values(all_providers, cells)
        numeric_avail = [
            c["value"] for c in values_dict.values()
            if c["available"] and isinstance(c["value"], (int, float))
        ]
        reason = _preferred_provider(
            period_primary_source,
            {k for k, v in values_dict.items() if v["available"]},
        )
        rows.append({
            "slug": group_name,
            "label": group_def["display_name"],
            "unit": None,
            "values": values_dict,
            "discrepancy": _calc_discrepancy(numeric_avail, discrepancy_threshold),
            "preferredProvider": reason["provider"] if reason else None,
            "primaryReason": reason,
        })

    return {
        "mode": "period", "days": days,
        "state": "loaded" if rows else "no_data", "rows": rows,
    }


def _mode_primary_source(conn: sqlite3.Connection, group_ids: list[str]) -> str | None:
    """기간 내 활동 그룹들의 primary_source 최빈값 (동률 시 _SOURCE_PRIORITY 낮은 순)."""
    if not group_ids:
        return None
    conn.row_factory = sqlite3.Row
    placeholders = ",".join("?" * len(group_ids))
    rows = conn.execute(
        f"SELECT primary_source, COUNT(*) as cnt FROM activity_groups"
        f" WHERE group_id IN ({placeholders}) GROUP BY primary_source"
        f" ORDER BY cnt DESC",
        group_ids,
    ).fetchall()
    if not rows:
        return None
    top_cnt = rows[0]["cnt"]
    tied = [r["primary_source"] for r in rows if r["cnt"] == top_cnt]
    if len(tied) == 1:
        return tied[0]
    return min(tied, key=lambda p: _SOURCE_PRIORITY.get(p, 99))

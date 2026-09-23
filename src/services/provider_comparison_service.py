"""Provider 비교 서비스 — 활동 그룹 내 소스별 메트릭 비교 (3-G-2).

읽기 전용. DB 쓰기 없음.
첫 번째 인자는 sqlite3.Connection.

설계 문서: v0.3/data/phase-7-ui-renewal/04-component-catalog.md C4
"""
from __future__ import annotations

import sqlite3
from typing import Any

from src.utils.dedup import _SOURCE_PRIORITY
from src.utils.metric_groups import SEMANTIC_GROUPS
from src.utils.metric_registry import METRIC_REGISTRY

# provider 표시 순서 (raw + semantic 공통)
_KNOWN_ORDER = ["garmin", "intervals", "strava", "runalyze"]


def get_provider_comparison(
    conn: sqlite3.Connection,
    activity_id: int,
    discrepancy_threshold: float = 5.0,
) -> dict | None:
    """활동 그룹 내 소스별 메트릭 비교.

    활동이 없으면 None(→ API 404).
    matched_group_id 없으면 single_provider 상태.
    """
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM activity_summaries WHERE id = ?", (activity_id,)
    ).fetchone()
    if not row:
        return None

    act = dict(row)
    group_id = act.get("matched_group_id")
    if not group_id:
        return {
            "mode": "activity",
            "activity_id": activity_id,
            "state": "single_provider",
            "rows": [],
        }

    # 형제 행 전체 조회
    sibling_rows = conn.execute(
        "SELECT * FROM activity_summaries WHERE matched_group_id = ?",
        (group_id,),
    ).fetchall()
    siblings = [dict(r) for r in sibling_rows]
    sibling_sources: list[str] = [s["source"] for s in siblings]
    sibling_ids: list[int] = [s["id"] for s in siblings]
    sibling_by_source: dict[str, dict] = {s["source"]: s for s in siblings}

    # activity_groups 테이블에서 primary_source 조회
    ag_row = conn.execute(
        "SELECT primary_source FROM activity_groups WHERE group_id = ?",
        (group_id,),
    ).fetchone()
    primary_source: str = (
        ag_row["primary_source"] if ag_row
        else _fallback_primary(sibling_sources)
    )

    # semantic metric_store 행 조회 (형제 전체)
    placeholders = ",".join("?" * len(sibling_ids))
    metric_rows = conn.execute(
        f"SELECT scope_id, metric_name, provider, numeric_value, text_value"
        f" FROM metric_store"
        f" WHERE scope_type='activity' AND scope_id IN ({placeholders})",
        [str(i) for i in sibling_ids],
    ).fetchall()
    # (scope_id_int, metric_name, provider) → row dict
    metric_idx: dict[tuple, dict] = {}
    for mr in metric_rows:
        d = dict(mr)
        metric_idx[(int(d["scope_id"]), d["metric_name"], d["provider"])] = d

    # 전체 provider 집합
    semantic_providers: set[str] = {dict(r)["provider"] for r in metric_rows}
    all_providers: list[str] = _ordered_providers(
        set(sibling_sources) | semantic_providers
    )

    rows: list[dict] = []

    # ── 1. Raw 메트릭 행 (activity_summaries 컬럼) ────────────────────────────
    for metric_def in METRIC_REGISTRY.values():
        if (
            metric_def.storage != "activity_summary"
            or metric_def.scope != "activity"
            or metric_def.category == "meta"
        ):
            continue

        col = metric_def.name
        cell_map: dict[str, Any] = {
            src: sib.get(col) for src, sib in sibling_by_source.items()
        }
        if all(v is None for v in cell_map.values()):
            continue

        available_map: dict[str, dict] = {
            src: {"value": v, "available": v is not None}
            for src, v in cell_map.items()
        }
        values_dict = _build_values(all_providers, available_map)
        numeric_avail = [
            c["value"] for c in values_dict.values()
            if c["available"] and isinstance(c["value"], (int, float))
        ]
        rows.append({
            "slug": col,
            "label": metric_def.description or col,
            "unit": metric_def.unit,
            "values": values_dict,
            "discrepancy": _calc_discrepancy(numeric_avail, discrepancy_threshold),
            "preferredProvider": _preferred_provider(
                primary_source,
                {k for k, v in values_dict.items() if v["available"]},
            ),
        })

    # ── 2. Semantic 메트릭 행 ─────────────────────────────────────────────────
    for group_name, group_def in SEMANTIC_GROUPS.items():
        group_cells: dict[str, dict] = {}
        has_numeric = False

        for metric_name, provider in group_def["members"]:
            if provider in group_cells:
                continue  # 같은 provider의 첫 번째 값만 사용
            for sib_id in sibling_ids:
                key = (sib_id, metric_name, provider)
                if key in metric_idx:
                    d = metric_idx[key]
                    val_n = d.get("numeric_value")
                    val_t = d.get("text_value")
                    val = val_n if val_n is not None else val_t
                    group_cells[provider] = {"value": val, "available": val is not None}
                    if isinstance(val, (int, float)):
                        has_numeric = True
                    break

        if not group_cells or not any(c["available"] for c in group_cells.values()):
            continue

        values_dict = _build_values(all_providers, group_cells)
        numeric_avail = (
            [
                c["value"] for c in values_dict.values()
                if c["available"] and isinstance(c["value"], (int, float))
            ]
            if has_numeric
            else []
        )
        rows.append({
            "slug": group_name,
            "label": group_def["display_name"],
            "unit": None,
            "values": values_dict,
            "discrepancy": _calc_discrepancy(numeric_avail, discrepancy_threshold) if has_numeric else None,
            "preferredProvider": _preferred_provider(
                primary_source,
                {k for k, v in values_dict.items() if v["available"]},
            ),
        })

    return {
        "mode": "activity",
        "activity_id": activity_id,
        "state": "loaded",
        "rows": rows,
    }


# ─── helpers ─────────────────────────────────────────────────────────────────

def _fallback_primary(sources: list[str]) -> str:
    """activity_groups 행이 없을 때 _SOURCE_PRIORITY로 대표 소스 결정."""
    return min(sources, key=lambda s: _SOURCE_PRIORITY.get(s, 99), default="")


def _ordered_providers(providers: set[str]) -> list[str]:
    """provider를 일관된 순서로 정렬 (garmin/intervals/strava/runalyze → runpulse:* → 기타)."""
    result = [p for p in _KNOWN_ORDER if p in providers]
    result += sorted(p for p in providers if p.startswith("runpulse"))
    result += sorted(p for p in providers if p not in set(_KNOWN_ORDER) and not p.startswith("runpulse"))
    return result


def _build_values(
    all_providers: list[str],
    available: dict[str, dict],
) -> dict[str, dict]:
    """모든 provider에 ComparisonCell 생성 (없는 provider는 available=False)."""
    return {
        p: available.get(p, {"value": None, "available": False})
        for p in all_providers
    }


def _calc_discrepancy(
    numeric_values: list[float | int],
    threshold: float,
) -> dict | None:
    """숫자값 2개 이상이면 discrepancy 계산, 아니면 None."""
    vals = [v for v in numeric_values if isinstance(v, (int, float))]
    if len(vals) < 2:
        return None
    max_v, min_v = max(vals), min(vals)
    max_diff = max_v - min_v
    abs_min = abs(min_v)
    if abs_min != 0:
        max_diff_pct = max_diff / abs_min * 100
    elif max_v != 0:
        max_diff_pct = max_diff / abs(max_v) * 100
    else:
        max_diff_pct = 0.0
    detected = max_diff_pct > threshold
    return {
        "detected": detected,
        "maxDiff": round(max_diff, 4),
        "maxDiffPct": round(max_diff_pct, 2),
        "severity": "warning" if detected else "info",
    }


def _preferred_provider(
    primary_source: str,
    available_providers: set[str],
) -> dict | None:
    """preferredProvider / primaryReason 계산.

    BACKLOG 규칙:
    1. available이 정확히 1개이고 runpulse로 시작 → runpulse_always
    2. non-runpulse provider가 없으면 → None
    3. primary_source가 available에 있으면 그걸 선택
    4. 없으면 _SOURCE_PRIORITY 기준 최고 우선순위 non-runpulse 선택
    모든 케이스(2 제외)에서 ruleType="static_priority"
    """
    if not available_providers:
        return None

    # 규칙 1: exactly 1 available, runpulse
    if len(available_providers) == 1:
        only = next(iter(available_providers))
        if only.startswith("runpulse"):
            return {
                "provider": only,
                "ruleType": "runpulse_always",
                "rule": "RunPulse — 자체 산출",
            }

    non_runpulse = {p for p in available_providers if not p.startswith("runpulse")}

    # 규칙 2: non-runpulse 없음
    if not non_runpulse:
        return None

    # 규칙 3/4: primary_source 우선, 없으면 _SOURCE_PRIORITY
    if primary_source in available_providers:
        chosen = primary_source
    else:
        chosen = min(non_runpulse, key=lambda p: _SOURCE_PRIORITY.get(p, 99))

    ordered = sorted(non_runpulse, key=lambda p: _SOURCE_PRIORITY.get(p, 99))
    rule = "소스 우선순위 (" + " > ".join(ordered) + ")"
    return {
        "provider": chosen,
        "ruleType": "static_priority",
        "rule": rule,
    }

"""Provider 정체성 매트릭스 서비스 — 3-G-1 (기간별 Provider × 시맨틱 그룹).

기간 동안 각 Provider가 어떤 메트릭을 제공하는지 보여주는 매트릭스.
읽기 전용. DB 쓰기 없음.
첫 번째 인자는 sqlite3.Connection.

설계 문서: v0.3/data/phase-7-ui-renewal/03c-library.md §3-G-1
"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from typing import Any

from src.utils.dedup import _SOURCE_PRIORITY
from src.utils.metric_registry import METRIC_REGISTRY

_KNOWN_ORDER = ["garmin", "intervals", "strava", "runalyze"]

_CATEGORY_LABELS: dict[str, str] = {
    "load": "피트니스·피로",
    "pace": "페이스·속도",
    "hr": "심박",
    "sleep": "수면·회복",
    "power": "파워",
    "running_dynamics": "러닝 다이나믹스",
    "efficiency": "달리기 효율",
    "readiness": "컨디셔닝",
    "prediction": "레이스 준비도",
    "body": "신체 지표",
    "stress": "스트레스",
    "capacity": "능력치",
    "volume": "훈련량",
}

# 표시 순서 (값 없는 카테고리는 자동 제외)
_MATRIX_CATEGORY_ORDER = [
    "load", "pace", "hr", "sleep", "power", "running_dynamics",
    "efficiency", "readiness", "prediction", "body", "stress",
    "capacity", "volume",
]

# 매트릭스에서 제외할 카테고리
_EXCLUDED_CATEGORIES = {"meta", "athlete", "weather", "_unmapped"}


def get_provider_matrix(
    conn: sqlite3.Connection,
    period_days: int = 28,
    discrepancy_threshold: float = 5.0,
) -> dict[str, Any]:
    """기간별 Provider × 메트릭 정체성 매트릭스.

    Returns: {period_days, providers, groups, discrepancy_count}
    groups 각 항목: {key, label, rows}
    rows 각 항목: {slug, label, unit, values, preferredProvider,
                   primaryReason, discrepancy}
    """
    conn.row_factory = sqlite3.Row
    cutoff = str(date.today() - timedelta(days=period_days))

    act_avgs = _fetch_activity_averages(conn, cutoff)
    daily_latest = _fetch_daily_latest(conn, cutoff)
    wellness_latest = _fetch_wellness_latest(conn, cutoff)

    groups, all_providers = _build_groups(
        act_avgs, daily_latest, wellness_latest, discrepancy_threshold
    )

    discrepancy_count = sum(
        1
        for g in groups
        for r in g["rows"]
        if r.get("discrepancy") and r["discrepancy"].get("detected")
    )

    return {
        "period_days": period_days,
        "providers": all_providers,
        "groups": groups,
        "discrepancy_count": discrepancy_count,
    }


# ─── data fetchers ────────────────────────────────────────────────────────────

def _fetch_activity_averages(
    conn: sqlite3.Connection, cutoff: str
) -> dict[str, dict[str, float]]:
    """activity_summaries 컬럼 기간별 source별 평균.

    Returns: {col_name: {source: avg_value}}
    """
    cols = [
        m.name
        for m in METRIC_REGISTRY.values()
        if m.storage == "activity_summary"
        and m.scope == "activity"
        and m.category not in _EXCLUDED_CATEGORIES
    ]
    if not cols:
        return {}

    select_parts = ", ".join(f"AVG({c}) AS {c}" for c in cols)
    rows = conn.execute(
        f"SELECT source, {select_parts}"
        " FROM activity_summaries"
        " WHERE start_time >= ?"
        " GROUP BY source",
        (cutoff,),
    ).fetchall()

    result: dict[str, dict[str, float]] = {c: {} for c in cols}
    for row in rows:
        d = dict(row)
        src = d["source"]
        for col in cols:
            val = d.get(col)
            if val is not None:
                result[col][src] = val
    return result


def _fetch_daily_latest(
    conn: sqlite3.Connection, cutoff: str
) -> dict[str, dict[str, float]]:
    """metric_store daily scope 기간 내 provider별 최신 numeric_value.

    Returns: {metric_name: {provider: value}}
    """
    rows = conn.execute(
        """
        SELECT ms.metric_name, ms.provider, ms.numeric_value
        FROM metric_store ms
        INNER JOIN (
            SELECT metric_name, provider, MAX(scope_id) AS max_date
            FROM metric_store
            WHERE scope_type = 'daily'
              AND scope_id >= ?
              AND numeric_value IS NOT NULL
            GROUP BY metric_name, provider
        ) latest
          ON ms.metric_name = latest.metric_name
         AND ms.provider    = latest.provider
         AND ms.scope_id    = latest.max_date
        WHERE ms.scope_type = 'daily'
        """,
        (cutoff,),
    ).fetchall()

    result: dict[str, dict[str, float]] = {}
    for row in rows:
        d = dict(row)
        result.setdefault(d["metric_name"], {})[d["provider"]] = d["numeric_value"]
    return result


def _fetch_wellness_latest(
    conn: sqlite3.Connection, cutoff: str
) -> dict[str, Any]:
    """daily_wellness 기간 내 최신 행 컬럼값 반환 (provider = 'garmin').

    Returns: {col_name: value}
    """
    wellness_cols = [
        m.name
        for m in METRIC_REGISTRY.values()
        if m.storage == "wellness" and m.scope == "daily"
    ]
    if not wellness_cols:
        return {}

    cols_sql = ", ".join(wellness_cols)
    row = conn.execute(
        f"SELECT {cols_sql} FROM daily_wellness"
        " WHERE date >= ? ORDER BY date DESC LIMIT 1",
        (cutoff,),
    ).fetchone()

    if not row:
        return {}

    return {k: v for k, v in dict(row).items() if v is not None}


# ─── group builder ────────────────────────────────────────────────────────────

def _build_groups(
    act_avgs: dict[str, dict[str, float]],
    daily_latest: dict[str, dict[str, float]],
    wellness_latest: dict[str, Any],
    threshold: float,
) -> tuple[list[dict], list[str]]:
    """3개 소스 데이터를 카테고리별 그룹으로 조립."""
    all_providers_set: set[str] = set()
    groups: list[dict] = []

    for cat_key in _MATRIX_CATEGORY_ORDER:
        label = _CATEGORY_LABELS.get(cat_key, cat_key)
        rows: list[dict] = []

        for mdef in METRIC_REGISTRY.values():
            if mdef.category != cat_key:
                continue

            cell_map: dict[str, dict] = {}

            if mdef.storage == "activity_summary" and mdef.scope == "activity":
                for src, val in act_avgs.get(mdef.name, {}).items():
                    rounded = round(val, 2) if isinstance(val, float) else val
                    cell_map[src] = {"value": rounded, "available": True}

            elif mdef.storage == "metric" and mdef.scope == "daily":
                for prov, val in daily_latest.get(mdef.name, {}).items():
                    cell_map[prov] = {"value": val, "available": True}

            elif mdef.storage == "wellness" and mdef.scope == "daily":
                val = wellness_latest.get(mdef.name)
                if val is not None:
                    cell_map["garmin"] = {"value": val, "available": True}

            if not cell_map:
                continue

            all_providers_set.update(cell_map.keys())
            numeric_vals = [
                v["value"]
                for v in cell_map.values()
                if isinstance(v.get("value"), (int, float))
            ]
            available_set = set(cell_map.keys())
            reason = _preferred_provider(available_set)

            rows.append({
                "slug": mdef.name,
                "label": mdef.description or mdef.name,
                "unit": mdef.unit,
                "values": cell_map,
                "preferredProvider": reason["provider"] if reason else None,
                "primaryReason": reason,
                "discrepancy": _calc_discrepancy(numeric_vals, threshold),
            })

        if rows:
            groups.append({"key": cat_key, "label": label, "rows": rows})

    all_providers = _ordered_providers(all_providers_set)
    return groups, all_providers


# ─── helpers ──────────────────────────────────────────────────────────────────

def _ordered_providers(providers: set[str]) -> list[str]:
    """provider를 일관된 표시 순서로 정렬."""
    result = [p for p in _KNOWN_ORDER if p in providers]
    result += sorted(p for p in providers if p.startswith("runpulse"))
    result += sorted(
        p for p in providers
        if p not in set(_KNOWN_ORDER) and not p.startswith("runpulse")
    )
    return result


def _preferred_provider(available: set[str]) -> dict | None:
    """preferredProvider / primaryReason 계산.

    1. RunPulse 전용 → runpulse_always
    2. non-runpulse 없음 → None
    3. _SOURCE_PRIORITY 기준 선택 → static_priority
    """
    if not available:
        return None

    non_runpulse = {p for p in available if not p.startswith("runpulse")}

    if not non_runpulse:
        # RunPulse 전용
        chosen = min(available, key=lambda p: p)
        return {
            "provider": chosen,
            "ruleType": "runpulse_always",
            "rule": "RunPulse — 자체 산출",
        }

    chosen = min(non_runpulse, key=lambda p: _SOURCE_PRIORITY.get(p, 99))
    ordered = sorted(non_runpulse, key=lambda p: _SOURCE_PRIORITY.get(p, 99))
    rule = "소스 우선순위 (" + " > ".join(ordered) + ")"
    return {
        "provider": chosen,
        "ruleType": "static_priority",
        "rule": rule,
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
    diff = max_v - min_v
    abs_min = abs(min_v)
    if abs_min != 0:
        diff_pct = diff / abs_min * 100
    elif max_v != 0:
        diff_pct = diff / abs(max_v) * 100
    else:
        diff_pct = 0.0
    detected = diff_pct > threshold
    return {
        "detected": detected,
        "maxDiff": round(diff, 4),
        "maxDiffPct": round(diff_pct, 2),
        "severity": "warning" if detected else "info",
    }

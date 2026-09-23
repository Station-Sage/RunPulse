"""Phase 7b 서비스 레이어 - 메트릭 계산 분해 트리.

get_metric_breakdown() — parent_metric_id(children) + Calculator.requires(inputs) 조립.
Library/metrics 화면(03c-library.md)용. 06-data-layer-extensions.md D1 "2026-09-22 정정",
04-component-catalog.md C3 MetricBreakdownData 참조.
"""
from __future__ import annotations

import sqlite3

from src.utils.db_helpers import get_primary_metric
from src.utils.metric_registry import METRIC_REGISTRY


def _metric_label(metric_name: str) -> str:
    """METRIC_REGISTRY에서 한국어 설명, 없으면 metric_name 그대로."""
    md = METRIC_REGISTRY.get(metric_name)
    return md.description if md and md.description else metric_name


def _metric_item(row: dict) -> dict:
    """metric_store 행 → breakdown item dict."""
    return {
        "name": row["metric_name"],
        "label": _metric_label(row["metric_name"]),
        "value": row.get("numeric_value"),
        "unit": row.get("unit", ""),
        "provider": row.get("provider"),
        "confidence": row.get("confidence"),
    }


def get_metric_breakdown(
    conn: sqlite3.Connection,
    scope_type: str,
    scope_id: str,
    slug: str,
) -> dict | None:
    """slug 메트릭의 분해 트리를 반환.

    Returns MetricBreakdownData 형태 dict, 또는 None(slug 없음).
    children: parent_metric_id 기반 소유 분해.
    inputs: Calculator.requires 기반 입력 메트릭.
    """
    # 자기 자신
    self_row = get_primary_metric(conn, scope_type, scope_id, slug)
    if self_row is None:
        return None

    self_id = self_row["id"]

    # children: parent_metric_id = self_id 인 행
    conn.row_factory = sqlite3.Row
    child_rows = conn.execute(
        "SELECT * FROM metric_store "
        "WHERE scope_type=? AND scope_id=? AND parent_metric_id=? "
        "ORDER BY id",
        (scope_type, str(scope_id), self_id),
    ).fetchall()
    children = [_metric_item(dict(r)) for r in child_rows]

    # inputs: Calculator.requires 조회
    from src.metrics.engine import ALL_CALCULATORS
    calc = next((c for c in ALL_CALCULATORS if c.name == slug), None)
    inputs: list[dict] = []
    if calc:
        for req_name in calc.requires:
            req_row = get_primary_metric(conn, scope_type, scope_id, req_name)
            if req_row is None:
                continue
            inputs.append(_metric_item(req_row))

    return {
        "slug": slug,
        "label": _metric_label(slug),
        "value": self_row.get("numeric_value"),
        "unit": self_row.get("unit", ""),
        "provider": self_row.get("provider"),
        "confidence": self_row.get("confidence"),
        "children": children,
        "inputs": inputs,
    }

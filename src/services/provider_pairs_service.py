"""소스 비교 쌍 목록 서비스 (S6, ADR-021) — 한 행의 같은 러닝(또는 같은 날) 값 쌍과 이상치.

읽기 전용. 대표 쌍은 매트릭스와 동일하게 가장 차이가 큰 쌍을 쓴다.
"""
from __future__ import annotations

import sqlite3

from src.services.provider_matrix_collect import iqr_bounds, pair_points, running_groups
from src.services.provider_matrix_service import diffs_for, representative, window
from src.utils.provider_matrix_rows import get_row


def get_pairs(conn: sqlite3.Connection, group: str, days: int, today: str) -> dict | None:
    """알 수 없는 group이면 None."""
    row = get_row(group)
    if row is None:
        return None
    start, end = window(days, today)
    base = {"row": {"key": row.key, "label": row.label, "unit": row.unit, "format": row.format,
                    "compare": row.compare, "kind": row.kind},
            "definitions": row.definitions, "days": days, "pairs": [], "diff": None}
    if not row.kind.startswith("pair"):
        return {**base, "summary_text": "정의가 달라 값을 직접 비교하지 않아요.", "state": "not_comparable"}
    points = pair_points(conn, row, running_groups(conn, start, end), start, end)
    provs = sorted({p for pt in points for p in pt["values"]})
    diff = representative(diffs_for(row, points, provs))
    if diff is None:
        return {**base, "summary_text": "겹치는 데이터가 없어요.", "state": "no_data"}
    a, b = diff["a"], diff["b"]
    items = []
    for pt in points:
        if a in pt["values"] and b in pt["values"] and pt["values"][b] != 0:
            x, y = pt["values"][a], pt["values"][b]
            items.append({**pt, "ratio" if row.compare == "scale" else "diff_pct":
                          round(x / y if row.compare == "scale" else (x - y) / abs(y) * 100, 3), "outlier": False})
    key = "ratio" if row.compare == "scale" else "diff_pct"
    bounds = iqr_bounds([i[key] for i in items])
    if bounds:
        for i in items:
            i["outlier"] = not (bounds[0] <= i[key] <= bounds[1])
    return {**base, "diff": diff, "pairs": items, "summary_text": diff["explain_text"],
            "state": "ok" if diff["status"] != "insufficient" else "insufficient"}

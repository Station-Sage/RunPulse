"""소스 비교 매트릭스 서비스 (S6, ADR-021) — 같은 러닝을 소스별로 어떻게 계산하는지 한눈에.

읽기 전용. 행 정의는 src/utils/provider_matrix_rows.py, 수집·통계는 provider_matrix_collect.py.
임계값(15%, n<3, 30일 stale)은 서버에서만 판단하고 프론트는 status·텍스트만 표시한다.
"""
from __future__ import annotations

import sqlite3
from collections import Counter
from datetime import date, timedelta

from src.services.provider_matrix_collect import (
    LOOKBACK_DAYS, PROVIDER_ORDER, cell_summary, collect_daily_values, pair_points, plabel,
    provider_pair_order, running_groups, severity_key, summarize_pairs,
)
from src.utils.provider_matrix_rows import KIND_SECTION, ROWS, SECTIONS, MatrixRow

VALID_DAYS = (28, 56, 84)


def window(days: int, today: str) -> tuple[str, str]:
    end = date.fromisoformat(today)
    return (end - timedelta(days=days - 1)).isoformat(), end.isoformat()


def diffs_for(row: MatrixRow, points: list[dict], providers: list[str]) -> list[dict]:
    out = []
    for a, b in provider_pair_order(providers):
        pairs = [(p["values"][a], p["values"][b]) for p in points if a in p["values"] and b in p["values"]]
        out.append(summarize_pairs(pairs, a, b, row.compare, row.threshold_pct))
    return out


def representative(diffs: list[dict]) -> dict | None:
    return max(diffs, key=severity_key) if diffs else None


def _preferred(row: MatrixRow, groups: list[dict], available: list[str]) -> dict | None:
    if not available:
        return None
    count = Counter(g["primary_source"] for g in groups if g["primary_source"] in available)
    if count:
        prov, k = count.most_common(1)[0]
        return {"provider": prov, "reason_text": f"최근 러닝 {len(groups)}건 중 {k}건의 기본 소스예요"}
    prov = min(available, key=lambda p: PROVIDER_ORDER.index(p) if p in PROVIDER_ORDER else 99)
    return {"provider": prov, "reason_text": "기본 소스 우선순위로 골랐어요"}


def _cells(conn, row: MatrixRow, groups: list[dict], start: str, end: str) -> dict:
    lookback = (date.fromisoformat(end) - timedelta(days=LOOKBACK_DAYS)).isoformat()
    cells: dict = {}
    if row.kind in ("pair_activity", "definition"):
        from src.services.provider_matrix_collect import collect_activity_values
        pts: dict[str, list] = {}
        for item in collect_activity_values(conn, groups, row):
            for p, v in item["values"].items():
                pts.setdefault(p, []).append((item["group"]["date"], v))
        for p, lst in pts.items():
            cells[p] = cell_summary(lst, start, end)
    else:
        for p, series in collect_daily_values(conn, lookback, end, row).items():
            cells[p] = cell_summary(list(series.items()), start, end)
    return {p: c for p, c in cells.items() if c}


def get_matrix(conn: sqlite3.Connection, days: int, today: str) -> dict:
    start, end = window(days, today)
    groups = running_groups(conn, start, end)
    sections = {k: [] for k, _ in SECTIONS}
    single: list[dict] = []
    for row in ROWS:
        cells = _cells(conn, row, groups, start, end)
        providers = [p for p in row.providers() if p in cells]
        if len(providers) < 2:
            if providers:
                p = providers[0]
                single.append({"key": row.key, "label": row.label, "provider": p,
                               "provider_label": plabel(p), "cell": cells[p], "unit": row.unit, "format": row.format})
            continue
        diffs = diffs_for(row, pair_points(conn, row, groups, start, end), providers) if row.kind.startswith("pair") else []
        sections[KIND_SECTION[row.kind]].append({
            "key": row.key, "label": row.label, "unit": row.unit, "format": row.format, "kind": row.kind,
            "compare": row.compare, "cells": cells, "providers": providers,
            "definitions": {p: row.definitions.get(p) for p in providers},
            "pairs_n": max((d["n"] for d in diffs), default=0), "diff": representative(diffs), "diffs": diffs,
            "preferred": _preferred(row, groups, [p for p in providers if not cells[p]["stale"]] or providers),
            "href_group": row.key if row.kind.startswith("pair") else None,
        })
    return {
        "days": days, "sport": "running", "sample_n": len(groups),
        "header_text": "같은 러닝을 소스마다 다르게 계산해요. ★ 값을 판단에 씁니다.",
        "caption": f"최근 {days // 7}주 · 러닝 {len(groups)}건",
        "providers": [p for p in PROVIDER_ORDER if any(p in r["cells"] for s in sections.values() for r in s)],
        "sections": [{"key": k, "label": lbl, "rows": sections[k]} for k, lbl in SECTIONS if sections[k]],
        "single_source": single,
        "state": "ok" if (len(groups) or single or any(sections.values())) else "no_data",
    }

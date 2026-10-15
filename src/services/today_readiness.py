"""Today 게이지 데이터 — UTRS/CIRS/TSB의 값·전일 대비·서버 등급(status/status_label)·provider.

프론트는 임계값 테이블 없이 이 응답만 렌더한다(design 10-today §7.3, 등급 SSOT는 metrics.bands).
"""
from __future__ import annotations

import sqlite3
from datetime import date as _date
from datetime import timedelta

from src.metrics.bands import grade
from src.services.metric_freshness import assess
from src.services.metric_freshness_spec import FRESHNESS_SPEC
from src.utils import db_helpers

GAUGE_METRICS = ("utrs", "cirs", "tsb")
_VERSION = "v1"


def _row(conn: sqlite3.Connection, day: str, name: str) -> dict | None:
    return db_helpers.get_primary_metric(conn, "daily", day, name)


def _value(conn: sqlite3.Connection, day: str, name: str) -> tuple[float | None, str | None]:
    row = _row(conn, day, name)
    if not row:
        return None, None
    return row.get("numeric_value"), row.get("provider")


def build_readiness(conn: sqlite3.Connection, day: str) -> dict:
    """{utrs|cirs|tsb: {value, delta_1d, status, status_label, provider, version, confidence, freshness} | None}.

    freshness 는 FRESHNESS_SPEC 에 등록된 지표(utrs)만 채우고 나머지는 None.

    값이 없으면 해당 지표는 None(빈 게이지 "데이터 수집 중"). delta_1d는 전일 값이 있을 때만.
    """
    prev = (_date.fromisoformat(day) - timedelta(days=1)).isoformat()
    out: dict = {}
    for name in GAUGE_METRICS:
        row = _row(conn, day, name)
        value = row.get("numeric_value") if row else None
        provider = row.get("provider") if row else None
        if value is None:
            out[name] = None
            continue
        before, _ = _value(conn, prev, name)
        g = grade(name, value) or {}
        out[name] = {
            "value": value,
            "delta_1d": round(value - before, 1) if before is not None else None,
            "status": g.get("status"),
            "status_label": g.get("label"),
            "provider": provider,
            "version": _VERSION,
            "confidence": row.get("confidence"),
            "freshness": assess(conn, name, day, row) if name in FRESHNESS_SPEC else None,
        }
    return out

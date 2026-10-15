"""메트릭 추세 서비스 — 3-F (daily-scope 단일 메트릭의 기간별 시계열 + 신선도/행동 힌트)."""
from __future__ import annotations

import json
import sqlite3
from datetime import date, timedelta
from typing import Any

from src.metrics.bands import band_ranges, grade
from src.services.metric_display import HIGHER_IS_BETTER as _HIGHER_IS_BETTER, action_hint, display_meta
from src.services.metric_freshness import assess, crs_boost_hold
from src.services.metric_freshness_spec import FRESHNESS_SPEC
from src.services.metrics_basis_events import basis_change_events
from src.services.metrics_changelog_events import recompute_caption, version_events
from src.utils.db_helpers import get_metric_history, get_primary_metric
from src.utils.metric_registry import METRIC_REGISTRY

_WELLNESS_TEXT = frozenset({"sleep_start_time"})

_PERIOD_DAYS: dict[str, int] = {"4w": 28, "3m": 90, "6m": 180, "1y": 365}


def _crs_level(conn: sqlite3.Connection, date: str) -> int | None:
    """CRS 게이트 level(0~4) — 힌트는 점수 밴드가 아닌 level로 고른다. 없으면 None."""
    row = conn.execute(
        "SELECT json_value FROM metric_store WHERE scope_type='daily' AND scope_id=? AND metric_name='crs' "
        "AND is_primary=1 AND json_value IS NOT NULL",
        (date,),
    ).fetchone()
    try:
        level = json.loads(row[0]).get("level") if row else None
    except (TypeError, ValueError, AttributeError):
        return None
    return level if isinstance(level, int) and 0 <= level <= 4 else None


def get_metric_trend(
    conn: sqlite3.Connection, slug: str, period: str = "3m"
) -> dict[str, Any] | None:
    """slug 메트릭의 기간별 일별 시계열 반환. 데이터 없으면 None."""
    days = _PERIOD_DAYS.get(period, _PERIOD_DAYS["3m"])
    date_from = str(_today() - timedelta(days=days))

    mdef0 = METRIC_REGISTRY.get(slug)
    if mdef0 is not None and mdef0.storage == "wellness" and slug not in _WELLNESS_TEXT:
        conn.row_factory = sqlite3.Row
        wrows = conn.execute(
            f"SELECT date, {slug} AS v FROM daily_wellness WHERE date >= ? AND {slug} IS NOT NULL ORDER BY date",
            (date_from,),
        ).fetchall()
        points = [{"date": r["date"], "value": r["v"]} for r in wrows]
    else:
        history = get_metric_history(conn, slug, scope_type="daily", date_from=date_from)
        points = [{"date": r["scope_id"], "value": r["numeric_value"]} for r in history]
    if not points:
        return None

    current = points[-1]["value"]
    peak_entry = max(points, key=lambda p: (p["value"] is not None, p["value"] or 0))
    peak = {"value": peak_entry["value"], "date": peak_entry["date"]}
    valued = [p for p in points if p["value"] is not None]
    best = worst = None
    if valued:
        hi = max(valued, key=lambda p: p["value"])
        lo = min(valued, key=lambda p: p["value"])
        if _HIGHER_IS_BETTER.get(slug) is False:
            best, worst = lo, hi
        else:
            best, worst = hi, lo
    baseline = _baseline(valued)

    first_val = points[0]["value"]
    if first_val and current is not None:
        change_pct = (current - first_val) / first_val * 100
    else:
        change_pct = None

    mdef = METRIC_REGISTRY.get(slug)
    label = mdef.description if mdef else slug
    unit = mdef.unit if mdef else ""

    current_date = points[-1]["date"]
    freshness = assess(conn, slug, current_date, get_primary_metric(conn, "daily", current_date, slug)) \
        if slug in FRESHNESS_SPEC else None
    if slug == "crs":
        hint = action_hint(
            slug, (grade(slug, current) or {}).get("status"), _crs_level(conn, current_date),
            assertive=freshness["assertive"], boost_hold=crs_boost_hold(conn, current_date)["hold"])
    else:
        hint = action_hint(slug, (grade(slug, current) or {}).get("status"))

    return {
        "slug": slug,
        **display_meta(slug, unit, label),
        "label": label,
        "unit": unit,
        "action_hint": hint,
        "current_date": current_date,
        "freshness": freshness,
        "current": current,
        "peak": peak,
        "best": best,
        "worst": worst,
        "baseline": baseline,
        "bands": band_ranges(slug),
        "change_pct": change_pct,
        "points": points,
        "events": sorted(
            _race_events(conn, points[0]["date"], points[-1]["date"])
            + basis_change_events(conn, slug, points[0]["date"], points[-1]["date"])
            + version_events(conn, slug, points[0]["date"], points[-1]["date"]),
            key=lambda e: e["date"],
        ),
        "recompute_note": recompute_caption(conn, slug, points[0]["date"], points[-1]["date"]),
    }


def _race_events(conn: sqlite3.Connection, d0: str, d1: str) -> list[dict[str, Any]]:
    """차트 기간 내 대회(▲) — race_result_service.candidates 기준. 실패해도 차트는 계속."""
    try:
        from src.services import race_result_service

        rows = race_result_service.candidates(conn, d0)
    except sqlite3.Error:
        return []
    return [
        {"date": r["date"], "kind": "race", "label": r["name"] or "대회", "activity_id": r["activity_id"]}
        for r in reversed(rows) if d0 <= r["date"] <= d1
    ]


def _baseline(valued: list[dict[str, Any]]) -> dict[str, Any] | None:
    """조회 구간 값의 평균·P25·P75. 3점 미만이면 None."""
    vals = sorted(p["value"] for p in valued)
    if len(vals) < 3:
        return None

    def q(f: float) -> float:
        i = (len(vals) - 1) * f
        lo = int(i)
        hi = min(lo + 1, len(vals) - 1)
        return round(vals[lo] + (vals[hi] - vals[lo]) * (i - lo), 4)

    return {"mean": round(sum(vals) / len(vals), 4), "p25": q(0.25), "p75": q(0.75), "days": len(vals)}


def _today() -> date:
    return date.today()

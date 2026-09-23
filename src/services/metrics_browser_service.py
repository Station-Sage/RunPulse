"""메트릭 브라우저·추세 서비스 — 3-E/3-F (daily-scope 전용)."""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from typing import Any

from src.utils.db_helpers import get_metric_history, get_primary_metric
from src.utils.metric_registry import METRIC_REGISTRY

_CATEGORY_LABELS: dict[str, str] = {
    "load": "피트니스·피로",
    "pace": "페이스·속도",
    "hr": "심박",
    "sleep": "수면·회복",
    "power": "파워",
    "running_dynamics": "러닝 다이나믹스",
    "efficiency": "달리기 효율",
    "prediction": "레이스 준비도",
    "readiness": "컨디셔닝",
    "body": "신체 지표",
    "stress": "스트레스",
    "capacity": "능력치",
    "volume": "훈련량",
    "athlete": "프로필",
    "weather": "환경",
    "meta": "기타",
}

_PERIOD_DAYS: dict[str, int] = {"4w": 28, "3m": 90, "6m": 180, "1y": 365}


def get_metrics_browser(conn: sqlite3.Connection, date: str | None = None) -> dict[str, Any]:
    """카테고리별 daily-scope 메트릭 현재값 + 14일 스파크라인 반환.

    date가 None이면 metric_store에서 최신 날짜를 자동 조회.
    값이 없는 메트릭 및 비어 있는 카테고리는 응답에서 제외.
    """
    if date is None:
        row = conn.execute(
            "SELECT MAX(scope_id) FROM metric_store"
            " WHERE scope_type = 'daily' AND numeric_value IS NOT NULL"
        ).fetchone()
        date = row[0] if row and row[0] else str(_today())

    # daily-scope 메트릭을 category별로 수집
    cat_map: dict[str, list[dict[str, Any]]] = {}
    for name, mdef in METRIC_REGISTRY.items():
        if mdef.scope != "daily":
            continue
        row_data = get_primary_metric(conn, "daily", date, name)
        if row_data is None or row_data.get("numeric_value") is None:
            continue

        history = get_metric_history(conn, name, scope_type="daily", date_to=date)
        sparkline: list[float | None] = [r["numeric_value"] for r in history[-14:]]

        entry: dict[str, Any] = {
            "name": name,
            "label": mdef.description,
            "value": row_data["numeric_value"],
            "unit": mdef.unit,
            "provider": row_data.get("provider"),
            "confidence": row_data.get("confidence"),
            "sparkline": sparkline,
        }
        cat_map.setdefault(mdef.category, []).append(entry)

    categories = []
    for category, metrics in cat_map.items():
        label = _CATEGORY_LABELS.get(category, category)
        categories.append({"category": category, "label": label, "metrics": metrics})

    return {"date": date, "categories": categories}


def get_metric_trend(
    conn: sqlite3.Connection, slug: str, period: str = "3m"
) -> dict[str, Any] | None:
    """slug 메트릭의 기간별 일별 시계열 반환. 데이터 없으면 None."""
    days = _PERIOD_DAYS.get(period, _PERIOD_DAYS["3m"])
    date_from = str(_today() - timedelta(days=days))

    history = get_metric_history(conn, slug, scope_type="daily", date_from=date_from)
    if not history:
        return None

    points = [{"date": r["scope_id"], "value": r["numeric_value"]} for r in history]

    current = points[-1]["value"]
    peak_entry = max(points, key=lambda p: (p["value"] is not None, p["value"] or 0))
    peak = {"value": peak_entry["value"], "date": peak_entry["date"]}

    first_val = points[0]["value"]
    if first_val and current is not None:
        change_pct = (current - first_val) / first_val * 100
    else:
        change_pct = None

    mdef = METRIC_REGISTRY.get(slug)
    label = mdef.description if mdef else slug
    unit = mdef.unit if mdef else ""

    return {
        "slug": slug,
        "label": label,
        "unit": unit,
        "current": current,
        "peak": peak,
        "change_pct": change_pct,
        "points": points,
    }


def _today() -> date:
    return date.today()

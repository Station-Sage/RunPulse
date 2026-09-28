"""메트릭 브라우저·추세 서비스 — 3-E/3-F (daily-scope 전용)."""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from typing import Any

from src.utils.db_helpers import get_metric_history, get_primary_metrics
from src.utils.metric_registry import METRIC_REGISTRY
from src.metrics.bands import with_grade

# 스파크라인 조회 창(일). 2-6 성능 — 메트릭당(daily-scope 84개) 별도 쿼리 2회씩
# (get_primary_metric + 무제한 get_metric_history) 돌던 게 /library/metrics 776ms의
# 원인이었다(02-performance.md P-3). 값 조회는 1회 배치로, 히스토리도 1회 배치로 합치되
# "최근 14개" 슬라이스를 위해 넉넉히 90일치만 가져온다 — 그보다 드문드문 기록되는
# 메트릭은 스파크라인이 14개보다 짧게 나올 수 있음(에러 대신 짧은 리스트, 코딩 규칙).
_SPARKLINE_LOOKBACK_DAYS = 90

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

    daily_names = [name for name, mdef in METRIC_REGISTRY.items() if mdef.scope == "daily"]

    # 1회 배치 조회 — 메트릭마다 따로 묻던 걸 IN 절 하나로(위 _SPARKLINE_LOOKBACK_DAYS 주석).
    primaries = {r["metric_name"]: r for r in get_primary_metrics(conn, "daily", date, names=daily_names)}
    have_value = [n for n in daily_names if primaries.get(n, {}).get("numeric_value") is not None]

    sparkline_map: dict[str, list[float | None]] = {n: [] for n in have_value}
    if have_value:
        from datetime import date as _date_cls  # 매개변수 `date`(str)가 모듈의 date 클래스를 가려서 로컬 임포트
        lookback_from = str(_date_cls.fromisoformat(date) - timedelta(days=_SPARKLINE_LOOKBACK_DAYS))
        conn.row_factory = sqlite3.Row
        placeholders = ",".join("?" * len(have_value))
        hist_rows = conn.execute(
            "SELECT metric_name, numeric_value FROM metric_store "
            "WHERE scope_type='daily' AND is_primary=1 AND scope_id BETWEEN ? AND ? "
            f"AND metric_name IN ({placeholders}) ORDER BY metric_name, scope_id",
            [lookback_from, date, *have_value],
        ).fetchall()
        for r in hist_rows:
            sparkline_map[r["metric_name"]].append(r["numeric_value"])

    # daily-scope 메트릭을 category별로 수집
    cat_map: dict[str, list[dict[str, Any]]] = {}
    for name in have_value:
        mdef = METRIC_REGISTRY[name]
        row_data = primaries[name]
        sparkline = sparkline_map[name][-14:]

        entry: dict[str, Any] = {
            "name": name,
            "label": mdef.description,
            "value": row_data["numeric_value"],
            "unit": mdef.unit,
            "provider": row_data.get("provider"),
            "confidence": row_data.get("confidence"),
            "sparkline": sparkline,
        }
        with_grade(entry, name, row_data["numeric_value"])
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

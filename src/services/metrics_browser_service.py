"""메트릭 브라우저·추세 서비스 — 3-E/3-F (daily-scope 전용)."""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from typing import Any

from src.utils.db_helpers import get_metric_history
from src.utils.metric_registry import METRIC_REGISTRY
from src.metrics.bands import band_ranges, with_grade
from src.services.metric_display import HIGHER_IS_BETTER as _HIGHER_IS_BETTER, display_meta

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

_WELLNESS_TEXT = frozenset({"sleep_start_time"})

_PERIOD_DAYS: dict[str, int] = {"4w": 28, "3m": 90, "6m": 180, "1y": 365}


def confidence_label(conf: float | None) -> str | None:
    """신뢰도(0~1) → 높음/보통/낮음. 값 없으면 None."""
    if conf is None:
        return None
    return "높음" if conf >= 0.7 else "보통" if conf >= 0.4 else "낮음"


def _change(values: list[float | None], dates: list[str]) -> dict[str, Any] | None:
    """스파크라인 창의 첫 유효값 대비 마지막 값 변화(abs·pct·days). 비교 불가면 None."""
    pairs = [(d, v) for d, v in zip(dates, values) if v is not None]
    if len(pairs) < 2:
        return None
    (d0, v0), (d1, v1) = pairs[0], pairs[-1]
    days = (date.fromisoformat(d1) - date.fromisoformat(d0)).days
    if days <= 0:
        return None
    return {
        "abs": round(v1 - v0, 4),
        "pct": round((v1 - v0) / abs(v0) * 100, 2) if v0 else None,
        "days": days,
    }


def _latest_daily_date(conn: sqlite3.Connection) -> str:
    """metric_store·daily_wellness 중 가장 최근 일자. 데이터 없으면 오늘."""
    row = conn.execute(
        "SELECT MAX(scope_id) FROM metric_store WHERE scope_type = 'daily' AND numeric_value IS NOT NULL"
    ).fetchone()
    latest = row[0] if row and row[0] else None
    wrow = conn.execute("SELECT MAX(date) FROM daily_wellness").fetchone()
    if wrow and wrow[0] and (latest is None or wrow[0] > latest):
        latest = wrow[0]
    return latest or str(_today())


def _daily_history(
    conn: sqlite3.Connection, names: list[str], date: str
) -> dict[str, list[tuple[str, float, str | None, float | None]]]:
    """메트릭별 [(일자, 값, provider, confidence)] — 기준일 이전 90일 창, 값 있는 날만, 일자 오름차순."""
    from datetime import date as _d  # 매개변수 `date`(str)가 모듈의 date 클래스를 가려서 로컬 임포트
    lookback_from = str(_d.fromisoformat(date) - timedelta(days=_SPARKLINE_LOOKBACK_DAYS))
    out: dict[str, list[tuple[str, float, str | None, float | None]]] = {}
    store_names = [n for n in names if METRIC_REGISTRY[n].storage != "wellness"]
    if store_names:
        conn.row_factory = sqlite3.Row
        marks = ",".join("?" * len(store_names))
        for r in conn.execute(
            "SELECT metric_name, scope_id, numeric_value, provider, confidence FROM metric_store "
            "WHERE scope_type='daily' AND is_primary=1 AND numeric_value IS NOT NULL "
            f"AND scope_id BETWEEN ? AND ? AND metric_name IN ({marks}) ORDER BY scope_id",
            [lookback_from, date, *store_names],
        ).fetchall():
            out.setdefault(r["metric_name"], []).append(
                (r["scope_id"], r["numeric_value"], r["provider"], r["confidence"]))
    cols = [n for n in names if METRIC_REGISTRY[n].storage == "wellness" and n not in _WELLNESS_TEXT]
    if cols:
        conn.row_factory = sqlite3.Row
        for r in conn.execute(
            f"SELECT date, {', '.join(cols)} FROM daily_wellness WHERE date BETWEEN ? AND ? ORDER BY date",
            [lookback_from, date],
        ).fetchall():
            for c in cols:
                if r[c] is not None:
                    out.setdefault(c, []).append((r["date"], r[c], None, None))
    return out


def get_metrics_browser(conn: sqlite3.Connection, date: str | None = None) -> dict[str, Any]:
    """카테고리별 daily-scope 메트릭 현재값 + 14일 스파크라인 반환.

    date가 None이면 metric_store에서 최신 날짜를 자동 조회.
    값이 없는 메트릭 및 비어 있는 카테고리는 응답에서 제외.
    """
    if date is None:
        date = _latest_daily_date(conn)

    daily_names = [name for name, mdef in METRIC_REGISTRY.items() if mdef.scope == "daily"]
    history = _daily_history(conn, daily_names, date)

    # daily-scope 메트릭을 category별로 수집 — 기준일에 값이 없으면 창 안의 최신값을 쓰고 last_value_date로 알린다
    cat_map: dict[str, list[dict[str, Any]]] = {}
    for name in daily_names:
        rows = history.get(name)
        if not rows:
            continue
        mdef = METRIC_REGISTRY[name]
        last_date, value, provider, confidence = rows[-1]
        sparkline = [r[1] for r in rows[-14:]]

        entry: dict[str, Any] = {
            "name": name,
            "label": mdef.description,
            "value": value,
            "unit": mdef.unit,
            "provider": provider,
            "confidence": confidence,
            "sparkline": sparkline,
            "confidence_label": confidence_label(confidence),
            **display_meta(name, mdef.unit, mdef.description),
            "last_value_date": last_date,
            "change": _change(sparkline, [r[0] for r in rows[-14:]]),
        }
        with_grade(entry, name, value)
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

    return {
        "slug": slug,
        **display_meta(slug, unit, label),
        "label": label,
        "unit": unit,
        "current": current,
        "peak": peak,
        "best": best,
        "worst": worst,
        "baseline": baseline,
        "bands": band_ranges(slug),
        "change_pct": change_pct,
        "points": points,
    }


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

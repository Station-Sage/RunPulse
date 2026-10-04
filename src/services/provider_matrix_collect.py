"""Provider 매트릭스 수집·통계 헬퍼 (S6, ADR-021).

읽기 전용. 러닝 그룹 목록, 행별 값 수집(활동/일/프로필), 쌍 차이 요약, 셀 요약을 담당한다.
임계값(15%, n<3, 30일 stale, IQR×1.5)은 모두 여기(서버)에만 둔다.
"""
from __future__ import annotations

import math
import sqlite3
from datetime import date, timedelta

from src.utils.activity_types import normalize_activity_type
from src.utils.provider_matrix_rows import MatrixRow

MIN_PAIRS = 3
STALE_DAYS = 30
OUTLIER_IQR_K = 1.5
LOOKBACK_DAYS = 400
PROVIDER_LABELS = {"garmin": "Garmin", "intervals": "Intervals", "strava": "Strava",
                   "runalyze": "Runalyze", "runpulse": "RunPulse"}
PROVIDER_ORDER = ["garmin", "intervals", "strava", "runalyze", "runpulse"]


def plabel(p: str) -> str:
    return PROVIDER_LABELS.get(p, p)


def quantile(vals: list[float], q: float) -> float:
    s = sorted(vals)
    k = (len(s) - 1) * q
    lo, hi = math.floor(k), math.ceil(k)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def median(vals: list[float]) -> float | None:
    return quantile(vals, 0.5) if vals else None


def iqr_bounds(vals: list[float]) -> tuple[float, float] | None:
    if len(vals) < MIN_PAIRS:
        return None
    q1, q3 = quantile(vals, 0.25), quantile(vals, 0.75)
    return q1 - OUTLIER_IQR_K * (q3 - q1), q3 + OUTLIER_IQR_K * (q3 - q1)


def running_groups(conn: sqlite3.Connection, start: str, end: str) -> list[dict]:
    """기간 [start, end] 내 canonical 러닝 그룹. 최신순.

    sibling_by_source: 같은 그룹의 소스별 사본 id(같은 소스 사본이 여럿이면 가장 작은 id).
    """
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, source, matched_group_id, name, activity_type, start_time, distance_m"
        " FROM v_canonical_activities WHERE substr(start_time,1,10) >= ? AND substr(start_time,1,10) <= ?"
        " ORDER BY start_time DESC", (start, end),
    ).fetchall()
    out: list[dict] = []
    for r in rows:
        if normalize_activity_type(r["activity_type"], r["source"]) != "running":
            continue
        gid = r["matched_group_id"]
        sibs = conn.execute(
            "SELECT id, source FROM activity_summaries WHERE matched_group_id = ? ORDER BY id", (gid,)
        ).fetchall() if gid else [{"id": r["id"], "source": r["source"]}]
        by_source: dict[str, int] = {}
        for s in sibs:
            by_source.setdefault(s["source"], s["id"])
        out.append({"group_key": gid or f"solo_{r['id']}", "group_id": gid, "canonical_id": r["id"],
                    "date": r["start_time"][:10], "name": r["name"], "distance_m": r["distance_m"],
                    "primary_source": r["source"], "sibling_by_source": by_source})
    return out


def _fetch(conn: sqlite3.Connection, scope_type: str, ids: list[str], metric: str, like: str) -> dict[str, float]:
    out: dict[str, float] = {}
    for i in range(0, len(ids), 500):
        chunk = ids[i:i + 500]
        q = ",".join("?" * len(chunk))
        for sid, val in conn.execute(
            f"SELECT scope_id, numeric_value FROM metric_store WHERE scope_type=? AND metric_name=?"
            f" AND provider LIKE ? AND numeric_value IS NOT NULL AND scope_id IN ({q}) ORDER BY is_primary",
            (scope_type, metric, like, *chunk),
        ):
            out[sid] = float(val)
    return out


def _like(provider: str) -> str:
    return "runpulse%" if provider == "runpulse" else provider


def collect_activity_values(conn: sqlite3.Connection, groups: list[dict], row: MatrixRow) -> list[dict]:
    """그룹별 {group, values:{provider: v}}. RunPulse 값은 canonical id, 외부 값은 해당 소스 사본에서."""
    per_group = [{"group": g, "values": {}} for g in groups]
    for metric, provider, scope in row.members:
        if scope != "activity":
            continue
        ids = {}
        for item in per_group:
            g = item["group"]
            sid = g["canonical_id"] if provider == "runpulse" else g["sibling_by_source"].get(provider)
            if sid is not None:
                ids[str(sid)] = item
        found = _fetch(conn, "activity", list(ids), metric, _like(provider))
        for sid, v in found.items():
            ids[sid]["values"][provider] = v
    return per_group


def collect_daily_values(conn: sqlite3.Connection, start: str, end: str, row: MatrixRow) -> dict[str, dict[str, float]]:
    """{provider: {date: value}} — daily 멤버는 날짜 스코프, activity 멤버(프로필)는 활동 시작일로 환산."""
    out: dict[str, dict[str, float]] = {}
    for metric, provider, scope in row.members:
        series = out.setdefault(provider, {})
        if scope == "daily":
            rows = conn.execute(
                "SELECT scope_id, numeric_value FROM metric_store WHERE scope_type='daily' AND metric_name=?"
                " AND provider LIKE ? AND numeric_value IS NOT NULL AND scope_id >= ? AND scope_id <= ?"
                " ORDER BY is_primary", (metric, _like(provider), start, end)).fetchall()
        else:
            rows = conn.execute(
                "SELECT substr(a.start_time,1,10), m.numeric_value FROM metric_store m"
                " JOIN activity_summaries a ON CAST(a.id AS TEXT) = m.scope_id"
                " WHERE m.scope_type='activity' AND m.metric_name=? AND m.provider LIKE ?"
                " AND m.numeric_value IS NOT NULL AND substr(a.start_time,1,10) >= ?"
                " AND substr(a.start_time,1,10) <= ? ORDER BY a.start_time", (metric, _like(provider), start, end)
            ).fetchall()
        for d, v in rows:
            series[d] = float(v)
    return out


def cell_summary(points: list[tuple[str, float]], window_start: str, end: str) -> dict | None:
    """points=[(date, value)]. 최신값·기준일·창 내 중앙값·stale(마지막 값이 기간 끝 30일 이전)."""
    if not points:
        return None
    last_date, latest = max(points, key=lambda p: p[0])
    in_win = [v for d, v in points if window_start <= d <= end]
    stale_cut = (date.fromisoformat(end) - timedelta(days=STALE_DAYS)).isoformat()
    return {"median": median(in_win), "latest": latest, "last_date": last_date,
            "stale": last_date < stale_cut, "estimated": False, "n": len(in_win)}


def pair_points(conn: sqlite3.Connection, row: MatrixRow, groups: list[dict], start: str, end: str) -> list[dict]:
    """쌍 비교용 시점 목록 [{date, canonical_id, name, distance_m, values}] (값 2개 이상인 것만). 최신순."""
    out: list[dict] = []
    if row.kind == "pair_activity":
        for item in collect_activity_values(conn, groups, row):
            if len(item["values"]) >= 2:
                g = item["group"]
                out.append({"date": g["date"], "canonical_id": g["canonical_id"], "name": g["name"],
                            "distance_m": g["distance_m"], "values": item["values"]})
    elif row.kind == "pair_daily":
        series = collect_daily_values(conn, start, end, row)
        days = sorted({d for s in series.values() for d in s}, reverse=True)
        for d in days:
            vals = {p: s[d] for p, s in series.items() if d in s}
            if len(vals) >= 2:
                out.append({"date": d, "canonical_id": None, "name": None, "distance_m": None, "values": vals})
    return out


def summarize_pairs(pairs: list[tuple[float, float]], a: str, b: str, compare: str, threshold_pct: float) -> dict:
    """pairs=[(a값, b값)]. same → (a−b)/b %, scale → a/b 비율. n<3이면 insufficient."""
    la, lb = plabel(a), plabel(b)
    vals = []
    for x, y in pairs:
        if y == 0:
            continue
        vals.append(x / y if compare == "scale" else (x - y) / abs(y) * 100)
    base = {"a": a, "b": b, "label": f"{la}↔{lb}", "mode": compare, "n": len(vals),
            "median": None, "q1": None, "q3": None}
    if len(vals) < MIN_PAIRS:
        return {**base, "status": "insufficient", "status_label": "표본 부족",
                "explain_text": f"겹치는 러닝이 {len(vals)}건뿐이라 비교하지 않아요."}
    med, q1, q3 = median(vals), quantile(vals, 0.25), quantile(vals, 0.75)
    base.update(median=round(med, 3), q1=round(q1, 3), q3=round(q3, 3))
    if compare == "scale":
        return {**base, "status": "scale", "status_label": f"×{med:.2f}",
                "explain_text": f"{la}은 같은 러닝을 {lb}보다 보통 {med:.1f}배로 계산해요. 척도가 달라 차이로 보지 않아요."}
    differs = abs(med) > threshold_pct
    return {**base, "status": "differs" if differs else "similar",
            "status_label": f"{med:+.0f}%" if differs else f"비슷함 ±{abs(med):.0f}%",
            "explain_text": (f"{la}이 {lb}보다 중앙값 기준 {med:+.0f}% 달라요." if differs
                             else f"두 소스 값이 거의 같아요(중앙 차이 {med:+.1f}%).")}


def severity_key(d: dict) -> float:
    """대표 diff 선택용: 클수록 차이가 큼. insufficient는 -1."""
    if d["median"] is None:
        return -1.0
    return abs(math.log(d["median"])) if d["mode"] == "scale" and d["median"] > 0 else abs(d["median"])


def provider_pair_order(providers: list[str]) -> list[tuple[str, str]]:
    """(a, b) 쌍 목록. 차이는 a를 b 기준으로 본다. b는 RunPulse가 있으면 RunPulse, 아니면 우선순위가 앞선 소스."""
    ps = sorted(providers, key=lambda p: PROVIDER_ORDER.index(p) if p in PROVIDER_ORDER else 99)
    out = []
    for i, x in enumerate(ps):
        for y in ps[i + 1:]:
            out.append((x, y) if y == "runpulse" else (y, x))
    return out

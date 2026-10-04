"""웰니스 /:date 일 상세 — 헤드라인·근거·준비도·수면·Body Battery·기준선·7일 점·이전/다음 날짜.

읽기 전용. 등급(status)은 metrics.bands SSOT에서 온다(프론트는 임계값 없음).
기준선 창은 당일을 제외한다: mean7 = d−7..d−1, p25/p75 = d−28..d−1, 수면 평균 = d−30..d−1.
표본 n<7인 기준선 키는 생략한다("기준선 수집 중" 표시는 프론트가 키 부재로 판단).
"""
from __future__ import annotations

import math
import sqlite3
from datetime import date as _date
from datetime import datetime, timedelta, timezone

from src.metrics.bands import grade

MIN_N = 7
Z_MIN = 0.5  # 근거로 삼을 최소 |z|

# slug, 컬럼, 주어, (높을 때 서술, 낮을 때 서술), 높을수록 좋은가
_REASONS = (
    ("sleep_duration_sec", "sleep_duration_sec", "수면이", ("충분해요", "짧았어요"), True),
    ("hrv_last_night", "hrv_last_night", "HRV가", ("높아요", "낮아요"), True),
    ("resting_hr", "resting_hr", "안정 심박이", ("높아요", "낮아요"), False),
    ("body_battery_high", "body_battery_high", "Body Battery 최고치가", ("높아요", "낮아요"), True),
)
_STAGE_KEYS = ("deep", "light", "rem", "awake")


def _d(s: str) -> _date:
    return _date.fromisoformat(s)


def _shift(day: str, n: int) -> str:
    return (_d(day) + timedelta(days=n)).isoformat()


def _percentile(sorted_vals: list[float], q: float) -> float:
    k = (len(sorted_vals) - 1) * q
    lo, hi = math.floor(k), math.ceil(k)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (k - lo)


def percentile_band(values: list[float | None]) -> dict | None:
    """시리즈의 평소 범위 {p25, p75}. 값이 MIN_N개 미만이면 None."""
    vals = sorted(float(v) for v in values if v is not None)
    if len(vals) < MIN_N:
        return None
    return {"p25": round(_percentile(vals, 0.25), 1), "p75": round(_percentile(vals, 0.75), 1)}


def _window(conn: sqlite3.Connection, col: str, day: str, back: int) -> list[float]:
    rows = conn.execute(
        f"SELECT {col} FROM daily_wellness WHERE date >= ? AND date < ? AND {col} IS NOT NULL",
        (_shift(day, -back), day),
    ).fetchall()
    return [float(r[0]) for r in rows]


def _stats(vals: list[float]) -> tuple[float, float] | None:
    if len(vals) < MIN_N:
        return None
    mean = sum(vals) / len(vals)
    var = sum((v - mean) ** 2 for v in vals) / len(vals)
    return mean, math.sqrt(var)


def _metric(conn: sqlite3.Connection, name: str, day: str) -> float | None:
    row = conn.execute(
        "SELECT numeric_value FROM metric_store WHERE scope_type='daily' AND scope_id=?"
        " AND metric_name=? AND is_primary=1",
        (day, name),
    ).fetchone()
    return None if row is None or row[0] is None else float(row[0])


def _readiness(conn: sqlite3.Connection, day: str) -> dict:
    out = {}
    for name in ("utrs", "cirs"):
        v = _metric(conn, name, day)
        g = grade(name, v) if v is not None else None
        out[name] = None if g is None else {"value": v, "status": g["status"], "status_label": g["label"]}
    return out


def _baselines(conn: sqlite3.Connection, day: str) -> dict:
    out: dict = {}
    hrv28 = _window(conn, "hrv_last_night", day, 28)
    if len(hrv28) >= MIN_N:
        hrv7 = _window(conn, "hrv_last_night", day, 7)
        s = sorted(hrv28)
        entry = {"mean7": round(sum(hrv7) / len(hrv7), 1) if hrv7 else None,
                 "p25": round(_percentile(s, 0.25), 1), "p75": round(_percentile(s, 0.75), 1), "n": len(hrv28)}
        lo, hi = _metric(conn, "hrv_baseline_balanced_low", day), _metric(conn, "hrv_baseline_balanced_upper", day)
        if lo is not None and hi is not None:
            entry["garmin_band"] = [lo, hi]
        out["hrv_last_night"] = entry
    rhr28 = _window(conn, "resting_hr", day, 28)
    if len(rhr28) >= MIN_N:
        rhr7 = _window(conn, "resting_hr", day, 7)
        s = sorted(rhr28)
        out["resting_hr"] = {"mean7": round(sum(rhr7) / len(rhr7), 1) if rhr7 else None,
                             "p25": round(_percentile(s, 0.25), 1), "p75": round(_percentile(s, 0.75), 1),
                             "n": len(rhr28)}
    sl30 = _window(conn, "sleep_duration_sec", day, 30)
    if len(sl30) >= MIN_N:
        out["sleep_duration_sec"] = {"mean30": round(sum(sl30) / len(sl30)), "n": len(sl30)}
    return out


def _stages(conn: sqlite3.Connection, day: str) -> dict | None:
    vals = {k: _metric(conn, f"sleep_{k}_sec", day) for k in _STAGE_KEYS}
    if all(v is None for v in vals.values()):
        return None
    return {k: v for k, v in vals.items()}


def _reasons(conn: sqlite3.Connection, day: str, core: dict) -> list[dict]:
    cands = []
    for slug, col, subject, words, higher_better in _REASONS:
        value = core.get(col)
        st = _stats(_window(conn, col, day, 28)) if value is not None else None
        if st is None or st[1] <= 0:
            continue
        mean, sd = st
        z = (value - mean) / sd
        if abs(z) < Z_MIN:
            continue
        up = z > 0
        cands.append({
            "slug": slug, "value": value, "baseline": round(mean, 1), "delta": round(value - mean, 1),
            "direction": "up" if up else "down", "good": up == higher_better,
            "chip": f"{subject} 평소보다 {words[0] if up else words[1]}", "_z": abs(z),
        })
    cands.sort(key=lambda c: -c["_z"])
    for c in cands:
        del c["_z"]
    return cands[:2]


def _headline(readiness: dict, reasons: list[dict]) -> dict:
    u = readiness.get("utrs")
    status, label = (u["status"], u["status_label"]) if u else ("neutral", "정보 없음")
    if reasons:
        text = f"회복 {label} — " + ". ".join(r["chip"] for r in reasons) + "."
    else:
        text = f"회복 {label} — 평소와 비슷해요."
    return {"status": status, "status_label": label, "text": text, "reasons": reasons}


def _as_of(updated_at: str | None) -> str | None:
    if not updated_at:
        return None
    try:
        dt = datetime.fromisoformat(updated_at).replace(tzinfo=timezone.utc).astimezone()
    except ValueError:
        return None
    return dt.strftime("%H:%M")


def _nav(conn: sqlite3.Connection, day: str) -> dict:
    prev = conn.execute("SELECT MAX(date) FROM daily_wellness WHERE date < ?", (day,)).fetchone()[0]
    nxt = conn.execute("SELECT MIN(date) FROM daily_wellness WHERE date > ?", (day,)).fetchone()[0]
    return {"prev": prev, "next": nxt}


def _week(conn: sqlite3.Connection, day: str) -> list[dict]:
    monday = _d(day) - timedelta(days=_d(day).weekday())
    out = []
    for i in range(7):
        d = (monday + timedelta(days=i)).isoformat()
        v = _metric(conn, "utrs", d)
        g = grade("utrs", v) if v is not None else None
        out.append({"date": d, "status": g["status"] if g else "none"})
    return out


def build_day(conn: sqlite3.Connection, day: str, today: str) -> dict:
    """일 상세 확장 필드. 기록이 없는 날도 week·nav는 채운다(has_record=False)."""
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM daily_wellness WHERE date = ?", (day,)).fetchone()
    core = dict(row) if row else {}
    is_today = day == today
    base = {"has_record": bool(row), "is_today": is_today, "nav": _nav(conn, day), "week": _week(conn, day)}
    if not row:
        return {**base, "headline": None, "readiness": _readiness(conn, day), "sleep": None,
                "body_battery": None, "baselines": {}, "as_of": None}
    readiness = _readiness(conn, day)
    baselines = _baselines(conn, day)
    reasons = _reasons(conn, day, core)
    as_of_t = _as_of(core.get("updated_at")) if is_today else None
    return {
        **base,
        "headline": _headline(readiness, reasons),
        "readiness": readiness,
        "sleep": {"score": core.get("sleep_score"), "duration_sec": core.get("sleep_duration_sec"),
                  "mean30_sec": (baselines.get("sleep_duration_sec") or {}).get("mean30"),
                  "stages": _stages(conn, day)},
        "body_battery": {"high": core.get("body_battery_high"), "low": core.get("body_battery_low"),
                         "charged": _metric(conn, "sleep_body_battery_change", day)},
        "baselines": baselines,
        "as_of": {"avg_stress": as_of_t, "steps": as_of_t} if as_of_t else None,
    }

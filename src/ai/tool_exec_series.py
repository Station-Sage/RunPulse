"""시계열·인사이트·체크인·예측 조회 도구 실행기 — get_wellness_series/get_activity_stream/get_insights/get_checkins/get_predictions."""
from __future__ import annotations

import json
import sqlite3
from datetime import date, timedelta

from src.ai.tool_format import columnar

_MAX_SERIES_DAYS = 120
_MAX_POINTS = 300
_MAX_INSIGHTS = 10
_MAX_CHECKIN_DAYS = 28
_STREAM_CHANNELS = {"heart_rate", "cadence", "power_watts", "altitude_m", "speed_ms", "grade_pct", "distance_m"}


def _clamp_days(args: dict, default: int, cap: int) -> tuple[str, str]:
    end = args.get("date_to") or date.today().isoformat()
    days = max(1, min(int(args.get("days", default)), cap))
    start = args.get("date_from") or (date.fromisoformat(end[:10]) - timedelta(days=days - 1)).isoformat()
    if (date.fromisoformat(end[:10]) - date.fromisoformat(start[:10])).days + 1 > cap:
        start = (date.fromisoformat(end[:10]) - timedelta(days=cap - 1)).isoformat()
    return start[:10], end[:10]


def _stats(vals: list[float]) -> dict:
    if not vals:
        return {}
    s = sorted(vals)
    return {"n": len(s), "min": round(s[0], 2), "max": round(s[-1], 2), "mean": round(sum(s) / len(s), 2),
            "median": round(s[len(s) // 2], 2)}


def _exec_get_wellness_series(conn: sqlite3.Connection, args: dict) -> dict:
    """일별 요약(kind 별 평균·최소·최대)과 7/28일 평균 기준선. kind 미지정 시 존재하는 kind 목록."""
    start, end = _clamp_days(args, 14, _MAX_SERIES_DAYS)
    kind = args.get("kind")
    if not kind:
        rows = conn.execute("SELECT kind, COUNT(DISTINCT date), MIN(date), MAX(date) FROM wellness_series"
                            " WHERE date BETWEEN ? AND ? GROUP BY kind ORDER BY kind", (start, end)).fetchall()
        return {"range": [start, end], "kinds": columnar(["kind", "days", "first", "last"], [list(r) for r in rows])}
    rows = conn.execute(
        "SELECT date, AVG(value), MIN(value), MAX(value), COUNT(*) FROM wellness_series"
        " WHERE kind=? AND date BETWEEN ? AND ? AND value IS NOT NULL GROUP BY date ORDER BY date",
        (kind, start, end)).fetchall()
    data = [[r[0], round(r[1], 2), round(r[2], 2), round(r[3], 2), r[4]] for r in rows]
    means = [r[1] for r in data]
    base = {f"mean_{n}d": round(sum(means[-n:]) / len(means[-n:]), 2) for n in (7, 28) if means}
    return {"kind": kind, "range": [start, end], "baseline": base,
            **columnar(["date", "mean", "min", "max", "samples"], data)}


def _exec_get_activity_stream(conn: sqlite3.Connection, args: dict) -> dict:
    """활동 스트림 채널을 30초(기본)로 리샘플한 ≤300점과 통계. 로컬 전용."""
    aid, ch = args.get("activity_id"), args.get("channel", "heart_rate")
    if aid is None:
        return {"error": "activity_id 필요"}
    if ch not in _STREAM_CHANNELS:
        return {"error": f"channel 은 {sorted(_STREAM_CHANNELS)} 중 하나"}
    lo = int(args.get("from_sec", 0))
    hi = int(args.get("to_sec", 10 ** 7))
    step = max(1, int(args.get("resample_sec", 30)))
    rows = conn.execute(
        f"SELECT elapsed_sec, {ch} FROM activity_streams WHERE activity_id=? AND elapsed_sec BETWEEN ? AND ?"
        f" AND {ch} IS NOT NULL ORDER BY elapsed_sec, sample_idx", (int(aid), lo, hi)).fetchall()
    if not rows:
        return {"activity_id": int(aid), "channel": ch, "error": "스트림 없음"}
    buckets: dict[int, list[float]] = {}
    for t, v in rows:
        buckets.setdefault(t // step * step, []).append(v)
    pts = [[k, round(sum(v) / len(v), 2)] for k, v in sorted(buckets.items())]
    if len(pts) > _MAX_POINTS:
        k = -(-len(pts) // _MAX_POINTS)
        pts = pts[::k]
    return {"activity_id": int(aid), "channel": ch, "resample_sec": step, "stats": _stats([r[1] for r in rows]),
            **columnar(["sec", ch], pts)}


def _exec_get_insights(conn: sqlite3.Connection, args: dict) -> dict:
    """능동 인사이트 사건(기본 열린 것) ≤10건 — 규칙 문장·근거 신호."""
    state = args.get("state", "open")
    limit = max(1, min(int(args.get("limit", 5)), _MAX_INSIGHTS))
    where, params = ("WHERE state IN ('open','seen')", []) if state == "open" else ("WHERE state=?", [state])
    rows = conn.execute(
        f"SELECT id, kind, severity, as_of, state, text, signals_json FROM insight_events {where}"
        " ORDER BY CASE severity WHEN 'act' THEN 0 WHEN 'watch' THEN 1 ELSE 2 END, as_of DESC LIMIT ?",
        params + [limit]).fetchall()
    out = []
    for r in rows:
        try:
            sig = json.loads(r[6]) if r[6] else []
        except ValueError:
            sig = []
        out.append([r[0], r[1], r[2], r[3], r[4], r[5], json.dumps(sig, ensure_ascii=False)[:300]])
    return columnar(["id", "kind", "severity", "as_of", "state", "text", "signals"], out)


def _exec_get_checkins(conn: sqlite3.Connection, args: dict) -> dict:
    """체크인(피로·통증·메모)과 활동 피드백(RPE·통증) ≤28일. 질병 자유문은 미동의 시 제외."""
    from src.services.illness_consent import has_consent

    start, end = _clamp_days(args, 14, _MAX_CHECKIN_DAYS)
    consent = has_consent(conn)
    ci = conn.execute("SELECT input_date, fatigue, pain, mood, note FROM user_inputs"
                      " WHERE input_type='checkin' AND input_date BETWEEN ? AND ? ORDER BY input_date",
                      (start, end)).fetchall()
    ci_rows = [[r[0], r[1], r[2] if consent else _generic(r[2]), r[3], r[4] if consent else None] for r in ci]
    fb = conn.execute(
        "SELECT substr(COALESCE(a.start_time,''),1,10), f.activity_id, f.rpe, f.pain, f.pain_sites, f.note"
        " FROM activity_feedback f LEFT JOIN activity_summaries a ON a.id=f.activity_id"
        " WHERE substr(COALESCE(a.start_time,''),1,10) BETWEEN ? AND ? ORDER BY 1", (start, end)).fetchall()
    fb_rows = [[r[0], r[1], r[2], r[3] if consent else _generic(r[3]), r[4], r[5] if consent else None] for r in fb]
    return {"range": [start, end],
            "checkins": columnar(["date", "fatigue", "pain", "mood", "note"], ci_rows),
            "activity_feedback": columnar(["date", "activity_id", "rpe", "pain", "pain_sites", "note"], fb_rows)}


def _generic(text):
    """미동의 시 질병 표현이 섞일 수 있는 통증 문구를 일반화한다."""
    if not text:
        return text
    return "컨디션 이상" if any(w in str(text).lower() for w in ("illness", "sick", "fever", "질병", "감기", "열")) else text


def _exec_get_predictions(conn: sqlite3.Connection, args: dict) -> dict:
    """최근 예측 스냅샷, 거리별 베스트 에포트, 대회 기록 요약."""
    limit = max(1, min(int(args.get("limit", 6)), 20))
    snaps = conn.execute(
        "SELECT as_of, provider, distance_m, pred_s, low_s, high_s, confidence FROM prediction_snapshots"
        " WHERE mode='live' ORDER BY as_of DESC, distance_m LIMIT ?", (limit,)).fetchall()
    best = conn.execute(
        "SELECT effort_name, MIN(elapsed_sec), COUNT(*) FROM activity_best_efforts WHERE elapsed_sec IS NOT NULL"
        " GROUP BY effort_name ORDER BY MIN(distance_m) LIMIT 12").fetchall()
    races = conn.execute(
        "SELECT race_name, distance_m, official_time_sec, effort, note FROM race_results ORDER BY id DESC LIMIT ?",
        (limit,)).fetchall()
    return {"predictions": columnar(["as_of", "provider", "distance_m", "pred_s", "low_s", "high_s", "confidence"],
                                    [list(r) for r in snaps]),
            "best_efforts": columnar(["effort", "best_sec", "n"], [list(r) for r in best]),
            "races": columnar(["name", "distance_m", "time_sec", "effort", "note"], [list(r) for r in races])}

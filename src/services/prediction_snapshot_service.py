"""예측 스냅샷·전향 평가(P7-PRED-63) — 모델별(r3 기본·기기·r4 섀도·Garmin) 예측을 그날 값 그대로 보존하고,
대회 확인 시 대회 전 예측(D-0·D-7·D-28)과 실제 기록을 비교해 채운다. 기본 표시 전환 판단의 근거(REVIEW-07 §R4-8(4)).

live 스냅샷은 동기화 직후 '오늘' 예측만 쓴다(과거 날짜 재계산값은 전향이 아니다). 재계산이 metric_store 를 덮어도
스냅샷은 바뀌지 않는다. 값이 그대로면 7일마다 1행만 쓴다.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date, timedelta

PROVIDERS = ("runpulse:formula_v1", "runpulse:ref_garmin", "runpulse:shadow_r4", "runpulse:shadow_r4_asym", "garmin")
DISTANCES = {"race_pred_5k_sec": 5000.0, "race_pred_10k_sec": 10000.0, "race_pred_half_sec": 21097.5,
             "race_pred_marathon_sec": 42195.0}
HORIZONS = (0, 7, 28)        # 대회일 기준 며칠 전 예측을 평가하나
TOLERANCE_DAYS = 7           # 그 시점 스냅샷이 없으면 이만큼 더 이전까지 허용(주 1회 기록)
REPEAT_DAYS = 7              # 값이 같으면 이 간격으로만 다시 기록
GARMIN_STALE_DAYS = 14       # Garmin 예측은 동기화가 드물다 — 이보다 오래된 값은 스냅샷하지 않음


def _latest(conn, metric: str, provider: str, day: str, max_age: int | None):
    row = conn.execute(
        "SELECT scope_id, numeric_value, json_value FROM metric_store WHERE scope_type='daily' AND metric_name=? "
        "AND provider=? AND scope_id<=? ORDER BY scope_id DESC LIMIT 1", (metric, provider, day)).fetchone()
    if not row or row[1] is None:
        return None
    if max_age is not None and (date.fromisoformat(day) - date.fromisoformat(row[0][:10])).days > max_age:
        return None
    return row


def record_snapshots(conn: sqlite3.Connection, day: str, mode: str = "live") -> int:
    """day 의 모델별·거리별 예측을 스냅샷한다. 쓴 행 수 반환. runpulse 경로는 그날 값만, Garmin 은 14일 이내 최신값."""
    n = 0
    for provider in PROVIDERS:
        for metric, dist in DISTANCES.items():
            row = _latest(conn, metric, provider, day, GARMIN_STALE_DAYS if provider == "garmin" else 0)
            if row is None:
                continue
            js = json.loads(row[2]) if row[2] else {}
            last = conn.execute(
                "SELECT as_of, pred_s FROM prediction_snapshots WHERE mode=? AND provider=? AND distance_m=? "
                "ORDER BY as_of DESC LIMIT 1", (mode, provider, dist)).fetchone()
            if last and round(last[1]) == round(row[1]) and \
                    (date.fromisoformat(day) - date.fromisoformat(last[0])).days < REPEAT_DAYS:
                continue
            inputs = {k: js[k] for k in ("contributions", "signals_s", "reasons", "tanda_s", "daniels_s") if k in js}
            cur = conn.execute(
                "INSERT OR IGNORE INTO prediction_snapshots (as_of, mode, provider, variant, model_version, distance_m, "
                "pred_s, low_s, high_s, confidence, inputs_json) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (day, mode, provider, js.get("variant") or js.get("path"), js.get("model_version"), dist, row[1],
                 js.get("low_s"), js.get("high_s"), js.get("confidence"), json.dumps(inputs, ensure_ascii=False)))
            n += cur.rowcount
    conn.commit()
    return n


def _covariates(conn, race_date: str, activity_id: int) -> dict:
    w = conn.execute("SELECT sleep_score, hrv_last_night, body_battery_high, resting_hr FROM daily_wellness "
                     "WHERE date=?", (race_date,)).fetchone()
    prev = (date.fromisoformat(race_date) - timedelta(days=1)).isoformat()
    tsb = conn.execute("SELECT numeric_value FROM metric_store WHERE scope_type='daily' AND metric_name='tsb' "
                       "AND provider='runpulse:formula_v1' AND scope_id=?", (prev,)).fetchone()
    t = conn.execute("SELECT numeric_value FROM metric_store WHERE scope_type='activity' AND scope_id=? "
                     "AND metric_name='weather_temp_c' AND is_primary=1", (str(activity_id),)).fetchone()
    keys = ("sleep_score", "hrv_last_night", "body_battery_high", "resting_hr")
    out = dict(zip(keys, w)) if w else {}
    out.update(tsb_prev=tsb[0] if tsb else None, temp_c=t[0] if t else None)
    return out


def evaluate_race(conn: sqlite3.Connection, activity_id: int) -> int:
    """확인된 대회(race_results)에 대해 거리가 같은 live 스냅샷을 horizon 별로 1행씩 골라 실제 기록·잔차·공변량을 채운다.
    잔차 = 예측/실제 − 1 (%, 양수 = 실제가 더 빠름). 반환: 채운 행 수. 전력(allout)이 아니면 평가하지 않는다."""
    row = conn.execute(
        "SELECT substr(a.start_time,1,10), r.distance_m, COALESCE(r.official_time_sec, a.elapsed_time_sec, "
        "a.moving_time_sec), r.effort FROM race_results r JOIN activity_summaries a ON a.id=r.activity_id "
        "WHERE r.activity_id=?", (activity_id,)).fetchone()
    if not row or row[3] != "allout" or not row[2]:
        return 0
    race_date, dist_m, actual, _ = row
    dist = min(DISTANCES.values(), key=lambda d: abs(d - dist_m))
    if abs(dist - dist_m) / dist > 0.03:
        return 0
    cov = json.dumps(_covariates(conn, race_date, activity_id), ensure_ascii=False)
    n = 0
    for provider in PROVIDERS:
        for h in HORIZONS:
            hi = (date.fromisoformat(race_date) - timedelta(days=h)).isoformat()
            lo = (date.fromisoformat(race_date) - timedelta(days=h + TOLERANCE_DAYS)).isoformat()
            snap = conn.execute(
                "SELECT id, pred_s FROM prediction_snapshots WHERE mode='live' AND provider=? AND distance_m=? "
                "AND as_of<=? AND as_of>=? AND race_activity_id IS NULL ORDER BY as_of DESC LIMIT 1",
                (provider, dist, hi, lo)).fetchone()
            if not snap:
                continue
            conn.execute("UPDATE prediction_snapshots SET race_activity_id=?, horizon_days=?, actual_s=?, "
                         "residual_pct=?, covariates_json=? WHERE id=?",
                         (activity_id, h, actual, round((snap[1] / actual - 1) * 100, 2), cov, snap[0]))
            n += 1
    conn.commit()
    return n


def summary(conn: sqlite3.Connection) -> list[dict]:
    """provider·horizon 별 전향 평가 요약: n, MAE%, 편향%, 80% 범위 적중 수."""
    rows = conn.execute(
        "SELECT provider, horizon_days, count(*), avg(abs(residual_pct)), avg(residual_pct), "
        "sum(CASE WHEN low_s <= actual_s AND actual_s <= high_s THEN 1 ELSE 0 END), "
        "sum(CASE WHEN low_s IS NOT NULL THEN 1 ELSE 0 END) FROM prediction_snapshots "
        "WHERE mode='live' AND actual_s IS NOT NULL GROUP BY provider, horizon_days ORDER BY provider, horizon_days"
    ).fetchall()
    return [{"provider": p, "horizon_days": h, "n": n, "mae_pct": round(m, 2), "bias_pct": round(b, 2),
             "hit80": hit, "n_range": nr} for p, h, n, m, b, hit, nr in rows]

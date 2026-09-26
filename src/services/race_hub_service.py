"""Today 목표 레이스 허브 — 활성 목표 + D-day + 예측 기록·목표 격차·예측 추이."""
from __future__ import annotations

import sqlite3

from src.services import prediction_compare_service
from src.services.race_projection_service import project_race_form
from datetime import date as _date, timedelta  # noqa: F401

_BUCKETS = [
    ("5k",       5.0,     1.0),
    ("10k",      10.0,    1.5),
    ("half",     21.0975, 2.0),
    ("marathon", 42.195,  2.5),
]


def bucket_for_distance(distance_km: float | None) -> str | None:
    """목표 거리(km)에 대응하는 예측 버킷. 중심에서 허용오차 이내이고 가장 가까운 버킷, 없으면 None."""
    if distance_km is None:
        return None
    best_bucket: str | None = None
    best_diff = float("inf")
    for name, center, tol in _BUCKETS:
        diff = abs(distance_km - center)
        if diff <= tol and diff < best_diff:
            best_diff = diff
            best_bucket = name
    return best_bucket


def get_race_hub(conn: sqlite3.Connection, date: str | None = None) -> dict:
    """가장 가까운 다가오는 활성 목표와 준비 현황.

    반환: {"goal", "prediction", "form", "projection"} — 각 None 가능. projection은 레이스 아침 폼 예측(race_projection_service).
    """
    conn.row_factory = sqlite3.Row

    if date is None:
        date = _date.today().isoformat()

    # 가장 가까운 다가오는 활성 목표 1개 (과거 목표 제외)
    goal_row = conn.execute(
        "SELECT id, name, race_date, distance_km, target_time_sec, target_pace_sec_km"
        " FROM goals"
        " WHERE status = 'active' AND race_date IS NOT NULL AND race_date >= ?"
        " ORDER BY race_date ASC, id DESC LIMIT 1",
        (date,),
    ).fetchone()

    if goal_row is None:
        return {"goal": None, "prediction": None, "form": None, "projection": None}

    goal_dict = dict(goal_row)
    race_date_str: str = goal_dict["race_date"]
    days_left = (_date.fromisoformat(race_date_str) - _date.fromisoformat(date)).days
    goal_out = {
        "id":                  goal_dict["id"],
        "name":                goal_dict["name"],
        "race_date":           race_date_str,
        "distance_km":         goal_dict["distance_km"],
        "target_time_sec":     goal_dict["target_time_sec"],
        "target_pace_sec_km":  goal_dict["target_pace_sec_km"],
        "days_left":           days_left,
        "weeks_left":          days_left // 7,
    }

    # 예측 버킷 결정
    bucket = bucket_for_distance(goal_dict["distance_km"])
    prediction = None
    if bucket is not None:
        metric_name = f"race_pred_{bucket}_sec"
        # 기준일 이전 최신 primary 값
        latest = conn.execute(
            "SELECT scope_id, numeric_value FROM metric_store"
            " WHERE metric_name = ? AND scope_type = 'daily'"
            "   AND is_primary = 1 AND numeric_value IS NOT NULL AND scope_id <= ?"
            " ORDER BY scope_id DESC LIMIT 1",
            (metric_name, date),
        ).fetchone()
        if latest is not None:
            value_sec = int(latest["numeric_value"])
            as_of = latest["scope_id"]
            target = goal_dict["target_time_sec"]
            gap_sec = (value_sec - target) if target is not None else None
            # 90일 이력 (오름차순)
            cutoff = (_date.fromisoformat(date) - timedelta(days=90)).isoformat()
            history_rows = conn.execute(
                "SELECT scope_id AS date, numeric_value AS value FROM metric_store"
                " WHERE metric_name = ? AND scope_type = 'daily'"
                "   AND is_primary = 1 AND numeric_value IS NOT NULL"
                "   AND scope_id >= ? AND scope_id <= ?"
                " ORDER BY scope_id ASC",
                (metric_name, cutoff, date),
            ).fetchall()
            prediction = {
                "bucket":    bucket,
                "value_sec": value_sec,
                "as_of":     as_of,
                "gap_sec":   gap_sec,
                "history":   [{"date": r["date"], "value": int(r["value"])} for r in history_rows],
                "compare":   prediction_compare_service.compare(conn, bucket, date),   # P7-PRED-71 3경로 비교
            }

    return {
        "goal":       goal_out,
        "prediction": prediction,
        "form":       _get_form(conn, date),
        "projection": project_race_form(conn, race_date_str, date),
    }


def _get_form(conn: sqlite3.Connection, date: str) -> dict:
    """현재 폼: CTL·TSB 각각 기준일 이전 최신 값."""
    ctl_row = conn.execute(
        "SELECT numeric_value FROM metric_store"
        " WHERE scope_type = 'daily' AND metric_name = 'ctl'"
        "   AND is_primary = 1 AND scope_id <= ?"
        " ORDER BY scope_id DESC LIMIT 1",
        (date,),
    ).fetchone()
    tsb_row = conn.execute(
        "SELECT numeric_value FROM metric_store"
        " WHERE scope_type = 'daily' AND metric_name = 'tsb'"
        "   AND is_primary = 1 AND scope_id <= ?"
        " ORDER BY scope_id DESC LIMIT 1",
        (date,),
    ).fetchone()
    return {
        "ctl": ctl_row["numeric_value"] if ctl_row else None,
        "tsb": tsb_row["numeric_value"] if tsb_row else None,
    }


def form_band(tsb: float) -> str:
    """레이스 아침 TSB 해석 라벨 — 프론트 `formBand`(raceHub.ts)와 같은 경계."""
    if tsb < -30:
        return "과부하"
    if tsb < -10:
        return "훈련 부하 높음"
    if tsb < 5:
        return "중립"
    if tsb <= 25:
        return "레이스 최적"
    return "회복 과다"


def _signed(v: float) -> str:
    r = round(v)
    return f"+{r}" if r > 0 else (f"\u2212{-r}" if r < 0 else "0")


def race_briefing(hub: dict, tsb: float | None) -> tuple[str, list[dict]] | None:
    """목표 레이스가 있을 때 오늘 브리핑을 레이스 국면(빌드/테이퍼/레이스 주간/당일)에 맞춰 만든다.

    반환: (헤드라인, 근거 리스트) 또는 None(목표 없음·TSB 없음). 근거 metric 이름은
    metric_store에 없어 프론트에서 드릴 없는 칩으로 렌더링된다.
    """
    goal = hub.get("goal")
    if not goal or tsb is None:
        return None
    n = goal["days_left"]
    taper = next((s for s in (hub.get("projection") or {}).get("scenarios", []) if s["key"] == "taper"), None)
    suffix = ""
    if taper is not None:
        suffix = f" 테이퍼를 지키면 레이스 아침 TSB {_signed(taper['tsb'])}({form_band(taper['tsb'])})이 예상돼요."

    if n == 0:
        headline = "오늘이 레이스입니다 — 준비한 대로 나가세요."
    elif n <= 7:
        headline = "레이스 주간입니다 — 새 자극 없이 짧은 활성화 러닝과 수면에 집중하세요."
    elif n <= 21:
        headline = "테이퍼 구간입니다 — 부하를 줄이며 회복을 쌓을 때예요." + suffix
    elif tsb < -20:
        headline = f"레이스까지 {n}일 — 피로가 높아 오늘은 회복 위주를 권합니다." + suffix
    elif tsb < -10:
        headline = f"레이스까지 {n}일 — 피로가 쌓이는 빌드 구간이에요. 오늘은 가볍게 가세요." + suffix
    else:
        headline = f"레이스까지 {n}일 — 컨디션 여유가 있어 핵심 세션을 소화하기 좋습니다."

    name = goal.get("name") or "레이스"
    evidence = [{"type": "metric", "metric": "race_days_left", "value": n, "label": f"{name} D-{n}" if n else f"{name} D-DAY"}]
    if taper is not None:
        evidence.append({
            "type": "metric", "metric": "race_form_projection", "value": taper["tsb"],
            "label": f"레이스 아침 TSB {_signed(taper['tsb'])} (테이퍼 시)",
        })
    return headline, evidence

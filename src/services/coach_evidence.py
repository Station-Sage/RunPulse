"""Coach 답변 근거 v2 (30-coach-chat design §4.4·§7.3) — "이 답변이 실제로 쓴 입력"만 칩으로 남긴다.

- 규칙 경로: readiness_decision 근거 + 오늘 계획 세션 + 체크인(항상 노출).
- LLM 경로: 위 후보 + 브리핑 근거 중 답변 본문이 인용한 값만(숫자가 반올림 오차 안에서 일치 + 지표 키워드).
- 각 항목은 role(supports|caveat)과 저장 시점 스냅샷 {value, computed_at, version, as_of}을 가진다.
- 조회 시점에 같은 as_of의 현재값을 다시 읽어 drift(값 변화)를 알려 준다. Calculator가 아닌 서비스라 SQL 사용 가능.
"""
from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timedelta

from src.utils.format_ko import fmt_distance, fmt_signed, workout_ko

MAX_ITEMS = 8
DRIFT_ABS = 5.0
DRIFT_REL = 0.25

_KEYWORDS: dict[str, tuple[str, ...]] = {
    "tsb": ("tsb", "폼", "훈련 스트레스 균형"),
    "body_battery": ("body battery", "바디배터리", "바디 배터리"),
    "sleep_score": ("수면",),
    "utrs": ("utrs", "훈련 준비도"),
    "race_form_projection": ("레이스 아침", "테이퍼", "폼"),
    "race_days_left": ("레이스", "대회"),
}
_WELLNESS_COLUMNS = {"body_battery": "body_battery_high", "sleep_score": "sleep_score"}
_NUM = re.compile(r"[-+−]?\d+(?:\.\d+)?")


def _rest_signal(metric: str, value) -> bool | None:
    """True=쉬라는 신호, False=진행 신호, None=중립."""
    if not isinstance(value, (int, float)):
        return None
    if metric == "tsb":
        return True if value < -15 else (False if value >= -10 else None)
    if metric in ("body_battery", "sleep_score"):
        return True
    return None


def _snapshot(conn: sqlite3.Connection, item: dict, as_of: str) -> dict:
    """metric_store 대표값의 계산 시각·버전을 함께 남긴다(없는 종류는 시각만)."""
    snap = {"value": item.get("value"), "computed_at": None, "version": None, "as_of": as_of}
    if item.get("type") == "metric":
        row = conn.execute(
            "SELECT numeric_value, algorithm_version, COALESCE(updated_at, created_at), scope_id FROM metric_store"
            " WHERE scope_type='daily' AND metric_name=? AND is_primary=1 AND scope_id<=?"
            " ORDER BY scope_id DESC LIMIT 1", (item["metric"], as_of)).fetchone()
        if row:
            snap.update(value=row[0], version=row[1], computed_at=row[2], as_of=row[3])
    return snap


def _read_current(conn: sqlite3.Connection, item: dict) -> dict | None:
    """저장된 as_of 기준 현재값 — metric_store(daily) 또는 daily_wellness. 없거나 추적 불가면 None."""
    snap = item.get("snapshot") or {}
    as_of, metric = snap.get("as_of"), item.get("metric")
    if not as_of or not metric:
        return None
    if item.get("type") == "metric":
        row = conn.execute(
            "SELECT numeric_value, algorithm_version, COALESCE(updated_at, created_at) FROM metric_store"
            " WHERE scope_type='daily' AND scope_id=? AND metric_name=? AND is_primary=1",
            (as_of, metric)).fetchone()
        return {"value": row[0], "version": row[1], "computed_at": row[2]} if row and row[0] is not None else None
    col = _WELLNESS_COLUMNS.get(metric)
    if item.get("type") == "wellness" and col:
        row = conn.execute(f"SELECT {col} FROM daily_wellness WHERE date=?", (as_of,)).fetchone()
        return {"value": row[0], "version": None, "computed_at": None} if row and row[0] is not None else None
    return None


def is_drifted(then, now) -> bool:
    """|now−then| ≥ max(5, |then|×0.25) 이거나 부호가 뒤집힌 경우."""
    if not isinstance(then, (int, float)) or not isinstance(now, (int, float)):
        return False
    if then * now < 0:
        return True
    return abs(now - then) >= max(DRIFT_ABS, abs(then) * DRIFT_REL)


def _status_of(metric: str, value) -> str | None:
    from src.metrics.bands import grade
    try:
        g = grade(metric, value)
    except Exception:
        return None
    return g["status"] if g else None


def with_current(conn: sqlite3.Connection, item: dict) -> dict:
    """조회용 — current{value,display,computed_at}|null 과 drifted를 붙인 복사본."""
    out = dict(item)
    cur = _read_current(conn, item) if item.get("snapshot") else None
    out["current"] = None
    out["drifted"] = False
    if cur:
        out["current"] = {**cur, "display": fmt_signed(cur["value"])}
        then = item["snapshot"].get("value")
        status_changed = bool(item.get("status")) and _status_of(item["metric"], cur["value"]) not in (None, item["status"])
        out["drifted"] = is_drifted(then, cur["value"]) or status_changed
    return out


def _cited(text: str, item: dict) -> bool:
    metric, value = item.get("metric", ""), item.get("value")
    low = text.lower()
    if not any(k in low for k in _KEYWORDS.get(metric, (metric.lower(),))):
        return False
    if not isinstance(value, (int, float)):
        return True
    tol = 0.5 if abs(value) >= 10 else 0.06
    for tok in _NUM.findall(text):
        n = float(tok.replace("−", "-"))
        if abs(abs(n) - abs(value)) <= tol:
            return True
    return False


def _candidates(conn: sqlite3.Connection, date: str) -> list[dict]:
    """규칙 경로가 쓰는 입력 — 판정 근거 → 계획 세션 → 체크인 (role은 판정 방향과 비교해 부여)."""
    from src.services.today_service import get_todays_checkin
    from src.training.fatigue import readiness_decision
    d = readiness_decision(conn, date=date)
    rest_dir = d["fatigue_level"] in ("moderate", "high")
    items = [dict(e) for e in d["evidence"]]
    try:
        from src.training.adjuster import adjust_todays_plan
        plan_adj = adjust_todays_plan(conn, date=date)
    except Exception:
        plan_adj = None
    if plan_adj:
        dist = f" {fmt_distance(plan_adj['distance_km'])}" if plan_adj.get("distance_km") else ""
        adjusted = bool(plan_adj.get("adjusted"))
        label = (f"오늘 계획: {workout_ko(plan_adj['original_type'])}{dist} → {workout_ko(plan_adj['adjusted_type'])}"
                 if adjusted else
                 f"오늘 계획: {workout_ko(plan_adj.get('workout_type', plan_adj.get('original_type', '')))}{dist}")
        items.append({"type": "plan", "metric": "plan_session", "value": None, "label": label,
                      "_rest": adjusted})
    ci = get_todays_checkin(conn, date)
    if ci and (ci.get("fatigue") is not None or ci.get("pain")):
        f = ci.get("fatigue")
        rest = bool(ci.get("pain")) or (f is not None and f >= 7)
        go = not rest and f is not None and f <= 4
        parts = ([f"피로 {f}"] if f is not None else []) + (["통증 있음"] if ci.get("pain") else [])
        items.append({"type": "user_input", "metric": "checkin", "value": f, "label": " · ".join(parts) + " (직접 입력)",
                      "pinned": True, "_rest": True if rest else (False if go else None)})
    for it in items:
        sig = it.pop("_rest") if "_rest" in it else _rest_signal(it["metric"], it.get("value"))
        it["role"] = "supports" if sig is None or sig == rest_dir else "caveat"
    return items


def _briefing_extras(conn: sqlite3.Connection) -> list[dict]:
    """Today 브리핑 근거(레이스 예측·UTRS 등) — LLM 답변이 인용했을 때만 후보가 된다."""
    try:
        from src.services.today_service import get_today_briefing
        return [dict(e, role="supports") for e in get_today_briefing(conn)["evidence"]]
    except Exception:
        return []


def build_answer_evidence(conn: sqlite3.Connection, text: str, *, llm: bool, as_of: str) -> list[dict]:
    """답변에 저장할 근거 목록. llm=True면 본문이 인용한 값만 남긴다(체크인은 항상)."""
    try:
        items = _candidates(conn, as_of) + (_briefing_extras(conn) if llm else [])
        if llm:
            items = [i for i in items if i.get("pinned") or _cited(text, i)]
        seen, out = set(), []
        for it in items:
            if it["metric"] in seen:
                continue
            seen.add(it["metric"])
            drill = {"scope_type": "daily", "scope_id": as_of} if it.get("type") == "metric" else None
            out.append({**it, "drill": drill, "snapshot": _snapshot(conn, it, as_of)})
        out.sort(key=lambda i: i["role"] == "caveat")
        return out[:MAX_ITEMS]
    except Exception:
        return []


def _kst_date(created_at: str | None) -> str | None:
    if not created_at:
        return None
    try:
        return (datetime.fromisoformat(created_at) + timedelta(hours=9)).date().isoformat()
    except ValueError:
        return None


def view_evidence(conn: sqlite3.Connection, msg: dict) -> None:
    """GET용 — 근거에 current/drifted를 붙이고, 옛(스냅샷 없는) 메시지는 legacy로 표시한다."""
    items = msg.get("evidence") or []
    if msg.get("role") != "assistant" or not items:
        msg["evidence_legacy"] = False
        return
    legacy = any("snapshot" not in i for i in items)
    msg["evidence_legacy"] = legacy
    if legacy:
        msg["evidence"] = [dict(i, role="legacy", drill=None) for i in items]
        msg["as_of"] = msg.get("as_of") or _kst_date(msg.get("created_at"))
        return
    msg["evidence"] = [with_current(conn, i) for i in items]

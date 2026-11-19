"""지표 해석 AI 다듬기 표면(ADR-059 2단계) — 분해 v2 화면의 규칙 해석 문장을 개인 추세·다른 지표·대회/계획 맥락으로 엮는다.

규칙 문장(밴드 so_what → 행동 힌트 → 90일 대비 personal 순)이 기본값이고, 동기화 뒤 백그라운드에서 다듬은 문장만
`meaning.interpretation={text, source}` 로 덧붙인다(요청 스레드는 캐시만 읽음). AI 로 보내는 facts 는 계산된 비건강
수치뿐이다 — 웰니스 원값(수면·HRV·스트레스)·체크인·메모·대회 이름은 넣지 않고, 문자열은 redact_health_text 를 거친다.
"""
from __future__ import annotations

import sqlite3
from datetime import date as _date, timedelta

from src.services import ai_wording as aw

_GUIDE = (
    "- 지표 해석 문장입니다. text 는 규칙이 내린 해석이고 facts 는 이 러너의 같은 날 계산값입니다.\n"
    "- 현재 값(value)을 본인 기준(avg_7d·avg_90d·value_28d_ago)과 비교하거나, 다른 지표(ctl·atl·tsb·acwr·utrs·cirs)와의"
    " 관계, 다가오는 대회(days_to_race)·오늘 계획(planned_today)과 엮어 원문에 없는 정보를 하나 이상 더합니다.\n"
    "- 원문의 권장 방향은 유지합니다. 더할 정보가 없으면 원문 그대로 둡니다. 지표 이름은 facts.metric 을 씁니다."
)
SURFACE = aw.register(aw.Surface(name="metric_interp", guide=_GUIDE, max_chars=160))

SLUGS = ("tsb", "ctl", "atl", "utrs", "cirs", "rri",
         "race_pred_5k_sec", "race_pred_10k_sec", "race_pred_half_sec", "race_pred_marathon_sec")
# 함께 보여 줄 계산 지표(훈련 부하·종합 점수) — 웰니스 원값은 넣지 않는다.
RELATED = ("ctl", "atl", "tsb", "acwr", "utrs", "cirs")
RACE_LOOKAHEAD_DAYS = 120
_RACE_LABEL = {5.0: "5K", 10.0: "10K", 21.1: "하프", 42.2: "풀마라톤"}


def _num(v) -> float | None:
    return round(float(v), 2 if abs(float(v)) < 10 else 1) if isinstance(v, (int, float)) else None


def _value_at(conn: sqlite3.Connection, name: str, day: str) -> float | None:
    r = conn.execute("SELECT numeric_value FROM metric_store WHERE scope_type='daily' AND scope_id=? AND metric_name=?"
                     " AND is_primary=1", (day, name)).fetchone()
    return r[0] if r and r[0] is not None else None


def _related(conn: sqlite3.Connection, slug: str, day: str) -> dict:
    from src.metrics.bands import grade
    out: dict = {}
    for name in RELATED:
        if name == slug:
            continue
        v = _value_at(conn, name, day)
        if v is None:
            continue
        out[name] = _num(v)
        band = grade(name, v)
        if band:
            out[f"{name}_status"] = band["label"]
    return out


def _race(conn: sqlite3.Connection, day: str) -> dict:
    """가장 가까운 예정 대회의 거리·남은 일수(이름은 자유 입력이라 넣지 않음). 없으면 {}."""
    hi = (_date.fromisoformat(day) + timedelta(days=RACE_LOOKAHEAD_DAYS)).isoformat()
    try:
        r = conn.execute("SELECT race_date, distance_km FROM race_calendar WHERE status='planned'"
                         " AND race_date BETWEEN ? AND ? ORDER BY race_date LIMIT 1", (day, hi)).fetchone()
    except sqlite3.Error:
        return {}
    if not r:
        return {}
    km = float(r[1] or 0)
    label = _RACE_LABEL.get(round(km, 1)) or f"{km:g}km"
    return {"race_distance": label, "days_to_race": (_date.fromisoformat(r[0]) - _date.fromisoformat(day)).days}


def _plan(conn: sqlite3.Connection, day: str) -> dict:
    from src.utils.format_ko import workout_ko
    try:
        r = conn.execute("SELECT workout_type, distance_km FROM planned_workouts WHERE date=? ORDER BY id LIMIT 1",
                         (day,)).fetchone()
    except sqlite3.Error:
        return {}
    if not r:
        return {}
    out = {"planned_today": workout_ko(r[0])}
    if r[1]:
        out["planned_km"] = _num(r[1])
    return out


def rule_text(explain: dict) -> str | None:
    """규칙 해석 문장 — so_what(밴드) → 행동 힌트 → personal(90일 대비). 없으면 None."""
    from src.services.metric_display import action_hint
    m = explain.get("meaning") or {}
    return (m.get("so_what") or action_hint(explain["slug"], explain.get("status"), value=explain.get("value"))
            or m.get("personal") or None)


def build_facts(conn: sqlite3.Connection, explain: dict) -> dict:
    """AI 에 줄 근거 — 계산된 비건강 수치만(평면 dict). 시간·페이스 단위는 화면과 같은 문자열."""
    from src.services.metrics_explain import _fmt_by_unit
    slug, day, unit = explain["slug"], explain["scope"]["id"], explain.get("unit")
    fmt = (lambda v: _fmt_by_unit(v, unit)) if unit in ("sec", "sec/km") else _num
    base = (explain.get("meaning") or {}).get("baseline") or {}
    facts: dict = {"metric": explain.get("name_ko") or slug}
    if explain.get("value") is not None:
        facts["value"] = fmt(explain["value"])
    if explain.get("status_label"):
        facts["status"] = explain["status_label"]
    for k in ("avg_7d", "avg_90d"):
        if base.get(k) is not None:
            facts[k] = fmt(base[k])
    if base.get("delta_1d") is not None and unit not in ("sec", "sec/km"):
        facts["delta_1d"] = _num(base["delta_1d"])
    prev = _value_at(conn, slug, (_date.fromisoformat(day) - timedelta(days=28)).isoformat())
    if prev is not None:
        facts["value_28d_ago"] = fmt(prev)
    if (explain.get("conclusion") or {}).get("text"):
        facts["conclusion"] = explain["conclusion"]["text"]
    facts.update(_related(conn, slug, day))
    facts.update(_race(conn, day))
    facts.update(_plan(conn, day))
    return {k: (aw.redact_health_text(v) if isinstance(v, str) else v) for k, v in facts.items()}


def build_item(conn: sqlite3.Connection, explain: dict) -> aw.Item | None:
    """일별 분해 응답 → 다듬을 한 건(scope_key='{slug}:{day}'). 지원 밖·규칙 문장 없음은 None."""
    if explain.get("slug") not in SLUGS or (explain.get("scope") or {}).get("type") != "daily":
        return None
    rule = rule_text(explain)
    if not rule:
        return None
    return aw.Item(f"{explain['slug']}:{explain['scope']['id']}", rule, build_facts(conn, explain))


def interpretation(conn: sqlite3.Connection, explain: dict) -> dict | None:
    """요청 스레드용 {text, source} — 캐시만 읽는다. 대상이 아니면 None(키 생략)."""
    try:
        item = build_item(conn, explain)
    except sqlite3.Error:
        return None
    return aw.present(conn, SURFACE, item.scope_key, item.rule_text, item.facts) if item else None


def collect(conn: sqlite3.Connection, day: str) -> list[aw.Item]:
    """warm 대상 — day 의 지원 지표 전부(요청 경로와 같은 rule_text·facts 라 해시가 맞는다)."""
    from src.services.metrics_explain import get_metric_explain
    items = []
    for slug in SLUGS:
        try:
            ex = get_metric_explain(conn, "daily", day, slug)
        except (sqlite3.Error, KeyError, ValueError):
            continue
        it = build_item(conn, ex) if ex else None
        if it:
            items.append(it)
    return items

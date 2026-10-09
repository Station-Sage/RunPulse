"""통증 입력 처리 — 단계별 op 강제, 다음 2일 제안, 반복 통증 알림 (ADR-035, DESIGN-PLAN-ROW-ACTION-COACHING §4).

진단·병명은 다루지 않는다. mild 는 강도를 낮춰 계속, moderate/severe 는 휴식으로 고정한다.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date, timedelta

from src.services.activity_feedback_service import MAX_SITES, PAIN_SITES

LEVELS = ("mild", "moderate", "severe")
MILD_OPS = ("reduce", "easy", "rest", "skip")
PROPOSAL_DAYS = 2
REPEAT_DAYS = 14
Q_TYPES = ("tempo", "threshold", "marathon", "long_mp", "interval", "long")
RULE_VERSION = "pain_v1"


def resolve(op: str, params: dict) -> str:
    """reason=pain 입력을 검증하고 실제 적용할 op 를 돌려준다(moderate/severe 는 rest 로 강제). 오류는 ValueError."""
    if params.get("reason") != "pain" or op == "move":
        return op
    level = params.get("pain_level")
    if level not in LEVELS:
        raise ValueError("통증 정도(mild/moderate/severe)를 선택해 주세요")
    sites = params.get("pain_sites") or []
    if not isinstance(sites, list) or len(sites) > MAX_SITES or any(s not in PAIN_SITES for s in sites):
        raise ValueError(f"통증 부위는 목록에서 최대 {MAX_SITES}개까지 고를 수 있어요")
    if level == "mild":
        if op not in MILD_OPS:
            raise ValueError("통증이 있을 땐 줄이거나 쉬는 것만 고를 수 있어요")
        return op
    return "rest"


def reasons(params: dict) -> list:
    reason = params.get("reason")
    if reason == "pain":
        return [{"key": "pain", "level": params["pain_level"], "sites": list(params.get("pain_sites") or [])}]
    return [{"key": "user", "label": str(reason)}] if reason else []


def _pain_rows(conn: sqlite3.Connection, start: str, end: str) -> list[tuple[str, dict]]:
    out = []
    for d, rj in conn.execute(
            "SELECT date, reasons_json FROM plan_adjustments WHERE source='user' AND decision='accepted'"
            " AND date >= ? AND date <= ? ORDER BY date", (start, end)):
        for r in json.loads(rj or "[]"):
            if r.get("key") == "pain":
                out.append((d, r))
    return out


def proposal(conn: sqlite3.Connection, day: str) -> dict | None:
    """직전 2일 안에 저장된 통증 조정이 있으면 day 의 세션에 대한 제안(adjust_todays_plan 형식), 없으면 None."""
    d = date.fromisoformat(day)
    rows = _pain_rows(conn, (d - timedelta(days=PROPOSAL_DAYS)).isoformat(), (d - timedelta(days=1)).isoformat())
    levels = {r["level"] for _d, r in rows}
    level = "severe" if "severe" in levels else "moderate" if "moderate" in levels else None
    if level is None:
        return None
    r = conn.execute("SELECT id, workout_type, distance_km, target_pace_min, target_pace_max, description"
                     " FROM planned_workouts WHERE date = ? ORDER BY id LIMIT 1", (day,)).fetchone()
    if r is None or r[1] in (None, "rest", "race"):
        return None
    w = dict(zip(("id", "workout_type", "distance_km", "target_pace_min", "target_pace_max", "description"), r))
    msg = "통증 기록 후 이틀은 쉬어 가는 걸 권해요"
    w.update(adjusted=True, adjusted_type="rest", reasons=[{"key": "pain", "label": msg}], rule_version=RULE_VERSION)
    if level == "moderate" and w["workout_type"] not in Q_TYPES and w["distance_km"]:
        w.update(adjusted_type=w["workout_type"], adjusted_distance_km=round(w["distance_km"] * 0.6, 1),
                 reasons=[{"key": "pain", "label": "통증 기록 후 이틀은 거리를 줄이길 권해요"}])
    return w


def repeat(conn: sqlite3.Connection, today: str) -> dict | None:
    """최근 14일 통증 조정이 2건 이상이거나 같은 부위가 두 번이면 PAIN_REPEAT 알림."""
    d = date.fromisoformat(today)
    rows = _pain_rows(conn, (d - timedelta(days=REPEAT_DAYS)).isoformat(), today)
    sites = [s for _d, r in rows for s in r.get("sites") or []]
    if len({x for x, _r in rows}) < 2 and len(sites) == len(set(sites)):
        return None
    return {"code": "PAIN_REPEAT", "severity": "caution",
            "text": "같은 부위 통증이 2주 사이 두 번 기록됐어요. 통증이 사라질 때까지 품질 세션은 미뤄 두는 게 안전해요."}

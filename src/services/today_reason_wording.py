"""Today 히어로 조정·보류 사유의 AI 다듬기 표면 (ADR-059 1단계) — 판정은 규칙 그대로, 문장만 원인과 오늘 세션을 잇는다.

조정 여부·종류는 adjuster(규칙)가 정하고 여기서는 건드리지 않는다. AI 에는 비건강 신호(TSB·ACWR·UTRS·CIRS·
Body Battery·수면 점수·대회까지 남은 일수·이번 주 진행)만 facts 로 주고, 사유 문장의 질병·부상·통증은
공통 계층이 '몸 상태 이상 신호' 로 일반화한다(ADR-057/058). 메모·활동 이름 같은 자유 입력은 넣지 않는다.
"""
from __future__ import annotations

import sqlite3

from src.services import ai_wording as aw

SURFACE = aw.register(aw.Surface(
    name="today_reason",
    guide=("- Today 화면의 '오늘 훈련을 바꾼(또는 증량을 보류한) 이유' 한 줄입니다.\n"
           "- facts 의 부하·회복 신호(TSB, ACWR, UTRS, CIRS, Body Battery, 수면 점수)와 대회까지 남은 일수·이번 주 진행을 엮어"
           " 왜 오늘 세션을 이렇게 하는지 한 단계 더 설명합니다. 근거가 약하면 원문을 그대로 둡니다.\n"
           "- 바뀐 세션 이름(from→to)과 보류 여부는 원문대로 유지합니다."),
    max_chars=120,
    forbidden=("괜찮아요", "무시", "강행"),
))

_FATIGUE = {"high": "높음", "moderate": "중간", "low": "낮음"}


def _ro(word: str) -> str:
    """받침 없음/ㄹ받침이면 '로', 그 외 받침이면 '으로' (프론트 euroRo 와 같은 규칙)."""
    code = ord(word[-1]) - 0xAC00 if word else -1
    final = code % 28 if 0 <= code <= 11171 else 0
    return f"{word}{'로' if final in (0, 8) else '으로'}"


def rule_text(state: dict) -> str | None:
    """briefing_state → 사유 규칙 문장(조정 우선, 없으면 보류). 둘 다 없으면 None."""
    adj = state.get("adjustment")
    if adj:
        head = f"{adj['reason']} — " if adj.get("reason") else ""
        return f"{head}오늘은 {adj['from']} 대신 {_ro(adj['to'])} 해요."
    texts = [r.get("text") for r in state.get("hold_reason") or [] if r.get("text")]
    return " · ".join(texts) + "." if texts else None


_RECENT_DAYS = 3   # 오늘 값이 아직 없으면 최근 3일 안의 마지막 값(adjuster 의 TSB 폴백과 같은 취지)


def _metric(conn: sqlite3.Connection, day: str, name: str) -> float | None:
    from datetime import date as _date, timedelta
    since = (_date.fromisoformat(day) - timedelta(days=_RECENT_DAYS)).isoformat()
    row = conn.execute("SELECT numeric_value FROM metric_store WHERE scope_type='daily' AND metric_name=?"
                       " AND is_primary=1 AND scope_id<=? AND scope_id>=? AND numeric_value IS NOT NULL"
                       " ORDER BY scope_id DESC LIMIT 1", (name, day, since)).fetchone()
    return round(float(row[0]), 2 if name == "acwr" else 1) if row else None


def facts(conn: sqlite3.Connection, day: str, state: dict, adj: dict | None, week: dict | None,
          race_days_left: int | None) -> dict:
    """AI 근거 — 값이 있는 비건강 신호만(평면 dict)."""
    out: dict = {"kind": "adjust" if state.get("adjustment") else "hold"}
    sess = state.get("session") or {}
    if sess.get("title"):
        out["session"] = sess["title"]
    if sess.get("distance_m") and sess.get("workout_type") != "rest":
        out["distance_km"] = round(sess["distance_m"] / 1000, 1)
    if adj:
        if adj.get("fatigue_level") in _FATIGUE:
            out["fatigue"] = _FATIGUE[adj["fatigue_level"]]
        w = adj.get("wellness") or {}
        for k in ("body_battery", "sleep_score"):
            if w.get(k) is not None:
                out[k] = w[k]
    for name in ("tsb", "acwr", "utrs", "cirs"):
        v = _metric(conn, day, name)
        if v is not None:
            out[name] = v
    if race_days_left is not None:
        out["race_days_left"] = race_days_left
    if week and week.get("plan_km"):
        out["week_done_km"], out["week_plan_km"] = week["done_km"], week["plan_km"]
    return out


def item(conn: sqlite3.Connection, day: str, state: dict, adj: dict | None, week: dict | None,
         race_days_left: int | None) -> aw.Item | None:
    """조정·보류 사유가 있을 때만 한 건(scope_key = 날짜)."""
    text = rule_text(state)
    if not text:
        return None
    return aw.Item(day, text, facts(conn, day, state, adj, week, race_days_left))


def collect(conn: sqlite3.Connection, day: str | None = None) -> list[aw.Item]:
    """동기화 뒤 워밍용 — 오늘 히어로 상태를 규칙으로 다시 계산해 사유 항목을 만든다."""
    from datetime import date as _date

    from src.services import today_hero
    day = day or _date.today().isoformat()
    week = today_hero.build_week(conn, day)
    state, adj = today_hero.briefing_core(conn, day, week)
    it = item(conn, day, state, adj, week, today_hero.race_days_left(conn, day))
    return [it] if it else []


def ai_view_for_adjustment(conn: sqlite3.Connection, day: str) -> dict | None:
    """계획 조정 카드용 — 그날 Today '오늘 이유'의 AI 문장({text, source:'ai'})을 재사용한다(사용자 결정 2026-11-20, D20).

    캐시만 읽고 생성을 예약하지 않는다(생성은 Today·동기화 경로). 조정(adjust) 사유가 아니거나 캐시가 낡았거나
    AI 문장이 없으면 None — 카드는 규칙 사유 줄을 그대로 쓴다.
    """
    try:
        items = collect(conn, day)
    except Exception:  # noqa: BLE001 — 카드 조회를 실패시키지 않는다(규칙 사유로 계속)
        return None
    if not items or items[0].facts.get("kind") != "adjust":
        return None
    it = items[0]
    view = aw.present(conn, SURFACE, it.scope_key, it.rule_text, it.facts, it.basis)
    return view if view["source"] == "ai" else None

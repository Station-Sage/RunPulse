"""/library/story 월·주 문단의 AI 다듬기 표면 (ADR-059 1단계) — 규칙 문단 + 기간 근거를 엮은 한 문단.

규칙 문단(story_service._rule_narrative_*)이 기본값이다. AI 에는 기간 집계(거리·횟수·최장·CTL 시작/끝)·강도 분포·
이전 기간 대비·ACWR 최고일 등급·대표 세션(유형·거리)·마일스톤 제목(종류별 상한 적용 후)을 facts 로 준다.
활동 이름·메모는 보내지 않는다. scope_key = 기간 id('2026-09'·'2026-W39'). 블록 기간은 대상이 아니다.
현재형(ADR-059 D15·D16): 재생성 기준 = 반올림한 facts(마일스톤 제목 포함 — 마일스톤 생성·삭제 시 재생성) + 규칙 문단 +
그 기간 활동 서명(편집·rematch 시 재생성, `wording_deps.period_signature`).
"""
from __future__ import annotations

import sqlite3

from src.services import ai_wording as aw

SURFACE = aw.register(aw.Surface(
    name="story_paragraph",
    guide=("- 훈련 이야기 화면의 기간(월·주) 요약 문단입니다.\n"
           "- facts 의 이전 기간 대비 변화·강도 분포·대표 세션·마일스톤을 엮어 이 기간 훈련이 어떤 흐름이었는지"
           " 2문장 안에서 말합니다. 규칙 문단의 수치(거리·횟수·CTL)는 유지합니다.\n"
           "- 부하 최고일(ACWR)은 등급(risk_label) 표현만 쓰고 '위험' 으로 단정하지 않습니다."),
    max_chars=200,
))
MAX_MILESTONES = 4


def facts(story: dict) -> dict:
    """get_story 응답 일부 → 평면 근거(값이 있는 것만)."""
    out: dict = {"period": story["period"]["label"]}
    for c in story.get("compare") or []:
        if c.get("prev"):
            out[f"prev_{c['key']}"] = c["prev"]
            out[f"{c['key']}_delta_pct"] = c["delta_pct"]
    if story.get("compare_basis"):
        out["compare_basis"] = story["compare_basis"]
    it = story.get("intensity") or {}
    if it.get("status") == "ok":
        out["easy_pct"], out["tempo_pct"], out["hard_pct"] = it["z12_pct"], it["z3_pct"], it["z45_pct"]
    rp = story.get("risk_peak") or {}
    if rp.get("value") is not None:
        out["acwr_peak"] = rp["value"]
        if rp.get("status_label"):
            out["acwr_peak_label"] = rp["status_label"]
    sessions = [f"{s.get('workout_label') or '러닝'} {s['distance_km']}km"
                for s in story.get("key_sessions") or [] if s.get("distance_km")]
    if sessions:
        out["key_sessions"] = ", ".join(sessions)
    titles = [m["title"] for m in (story.get("milestones") or [])[:MAX_MILESTONES] if m.get("title")]
    if titles:
        out["milestones"] = ", ".join(titles)
    for ch in story.get("chips") or []:
        if str(ch.get("label", "")).startswith("최장") and ch.get("value"):
            out["longest_km"] = ch["value"]
    return out


def item(story: dict, rule_paragraph: str, conn: sqlite3.Connection | None = None) -> aw.Item | None:
    """월·주 기간만, 미래 기간·기록 없음 제외. conn 이 있으면 기간 활동 서명을 의존으로 건다."""
    from src.services.ai_wording_basis import default_basis
    pid = story["period"]["id"]
    if story.get("is_future") or pid.startswith("b-") or "아직 없습니다" in rule_paragraph:
        return None
    f = facts(story)
    deps = None
    if conn is not None and story["period"].get("start") and story["period"].get("end"):
        from src.services.wording_deps import period_signature
        deps = {"acts": period_signature(conn, story["period"]["start"], story["period"]["end"])}
    return aw.Item(pid, rule_paragraph, f, default_basis(rule_paragraph, f, deps))


def current_periods(today: str) -> list[str]:
    from datetime import date as _date
    d = _date.fromisoformat(today)
    y, w, _ = d.isocalendar()
    return [today[:7], f"{y}-W{w:02d}"]


def collect(conn: sqlite3.Connection, today: str | None = None) -> list[aw.Item]:
    """동기화 뒤 워밍용 — 이번 달·이번 주 문단."""
    from datetime import date as _date

    from src.services import story_service
    today = today or _date.today().isoformat()
    items: list[aw.Item] = []
    for pid in current_periods(today):
        story = story_service.build_story(conn, pid)
        it = item(story, story["paragraph_rule"], conn)
        if it:
            items.append(it)
    return items

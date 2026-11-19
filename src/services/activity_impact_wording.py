"""활동 상세 '이 러닝의 의미' 문장 — 규칙 줄(서버 생성)과 AI 요약 표면 (ADR-059 1단계).

규칙 줄은 값이 있는 항목만 만든다(근거 없는 문장 금지, 이전 프론트 impactLines 와 같은 문구). AI 는 그 줄과
활동 기본값(날짜·거리·평균 페이스·운동 유형)·그날 계획 세션·대회까지 남은 일수를 엮어 한두 문장으로 의미를 말한다.
활동 이름·메모(자유 입력)는 보내지 않는다. scope_key = 활동 id.

스냅샷형(ADR-059 D16): src_hash 는 그 활동 자신의 데이터 서명(`wording_deps.activity_signature` — 거리·페이스·HR·랩·
플랜 매칭·피드백·마일스톤)과 직전 비교 대상 활동의 서명·비교 기준·대회 D-day 로만 만든다. 이후 CTL/TSB 변동이나
새 활동 추가는 재생성하지 않는다(비교 집합은 이전 활동뿐). 생성 한도(D17): 최근 RECENT_DAYS 일 활동은 동기화 직후,
그보다 오래된 활동은 처음 열 때 한 번(백그라운드, 쿨다운).
"""
from __future__ import annotations

import math
import sqlite3

from src.services import ai_wording as aw

SURFACE = aw.register(aw.Surface(
    name="activity_impact",
    guide=("- 활동 상세의 '이 러닝의 의미' 요약입니다. text 는 규칙이 만든 줄들(' / ' 로 구분)입니다.\n"
           "- 그날 계획 세션(planned)·유사 활동 비교·체력(CTL) 변화·대회까지 남은 일수를 엮어 이 러닝이 훈련 흐름에서"
           " 무엇을 했는지 한두 문장으로 말합니다. 줄을 차례로 바꿔 읽기만 할 거라면 원문을 그대로 둡니다.\n"
           "- 비교 순위·페이스 차이는 원문 수치 그대로 씁니다. 좋다·나쁘다를 원문보다 단정하지 않습니다."),
    max_chars=140,
))
LINE_SEP = " / "


def _jsround(v: float) -> int:
    """JS Math.round 와 같은 반올림(.5 는 +∞ 쪽) — 이전 프론트 문구와 같은 숫자를 낸다."""
    return math.floor(v + 0.5)


def _signed(v: float, digits: int, sign_of: float | None = None) -> str:
    s = f"{v:.{digits}f}" if digits else str(_jsround(v))
    return s if (v if sign_of is None else sign_of) < 0 else f"+{s}"


def impact_lines(impact: dict) -> list[str]:
    """임팩트 dict → 화면 줄 목록. 값이 없는 항목은 만들지 않는다."""
    out: list[str] = []
    ctl, tsb = impact.get("ctl_contribution"), impact.get("tsb")
    if ctl is not None:
        out.append(f"이 날 체력(CTL) {_signed(ctl, 1)}" + (f" · 폼(TSB) {_signed(tsb, 0)}" if tsb is not None else ""))
    s = impact.get("similar")
    if s:
        diff = s.get("pace_diff_sec") or 0
        d = abs(_jsround(diff))
        cmp = f"{d}초/km 빠름" if diff < 0 else f"{d}초/km 느림" if diff > 0 else "평균과 같음"
        basis = s.get("basis")
        group = "같은 코스" if basis == "same_course" else (
            f"같은 {s.get('class_label') or '유형'}" if basis == "same_class" else "비슷한 거리")
        out.append(f"{group} 이전 {s['n']}회 중 {s['pace_rank']}번째로 빠른 페이스 (평균보다 {cmp})")
        if s.get("load_median") is not None and s.get("load_pct_vs_median") is not None:
            out.append(f"부하 대비: {group} 중앙값 {_jsround(s['load_median'])} 대비 "
                       f"{_signed(s['load_pct_vs_median'], 0, _jsround(s['load_pct_vs_median']))}%")
    else:
        out.append("판정할 기준이 아직 부족해요(같은 유형·코스 기록 5회 필요)")
    race = impact.get("race")
    if race:
        out.append(f"{race['name']} D-{race['days_left']}에 쌓은 세션")
    return out


def _pace(sec: float | None) -> str | None:
    if not sec:
        return None
    s = int(round(sec))
    return f"{s // 60}:{s % 60:02d}/km"


def facts(conn: sqlite3.Connection, activity_id: int, impact: dict) -> dict:
    """AI 근거 — 활동 기본값·그날 계획·임팩트 수치(자유 입력 제외)."""
    out: dict = {}
    r = conn.execute("SELECT start_time, distance_m, avg_pace_sec_km FROM activity_summaries WHERE id=?",
                     (activity_id,)).fetchone()
    if r:
        out["date"] = str(r[0])[:10]
        if r[1]:
            out["distance_km"] = round(r[1] / 1000, 1)
        if _pace(r[2]):
            out["avg_pace"] = _pace(r[2])
        try:
            p = conn.execute("SELECT workout_type, distance_km FROM planned_workouts WHERE matched_activity_id=?"
                             " ORDER BY id DESC LIMIT 1", (activity_id,)).fetchone()
        except sqlite3.Error:
            p = None
        if p:
            from src.services.today_hero import WORKOUT_LABELS
            out["planned"] = WORKOUT_LABELS.get(p[0], p[0])
            if p[1]:
                out["planned_km"] = p[1]
    for k in ("ctl_contribution", "tsb", "load"):
        if impact.get(k) is not None:
            out[k] = impact[k]
    if (impact.get("similar") or {}).get("class_label"):
        out["workout_class"] = impact["similar"]["class_label"]
    if impact.get("race"):
        out["race_days_left"] = impact["race"]["days_left"]
    return out


def snapshot_basis(conn: sqlite3.Connection, activity_id: int, impact: dict) -> dict:
    """재생성 기준 — 활동 자신 + 직전 비교 대상 활동(그 활동이 편집되면 이 문구도 재생성) + 비교 기준·대회 D-day."""
    from src.services.wording_deps import activity_signature
    s = impact.get("similar") or {}
    return {"own": activity_signature(conn, activity_id), "cmp_basis": s.get("basis"),
            "cmp_prev": activity_signature(conn, s.get("latest_id")) if s.get("latest_id") else None,
            "race_days_left": (impact.get("race") or {}).get("days_left")}


def item(conn: sqlite3.Connection, activity_id: int, impact: dict, lines: list[str]) -> aw.Item:
    return aw.Item(str(activity_id), LINE_SEP.join(lines), facts(conn, activity_id, impact),
                   snapshot_basis(conn, activity_id, impact))


def attach(conn: sqlite3.Connection, activity_id: int, impact: dict | None, config: dict | None,
           schedule: bool = True) -> dict | None:
    """impact 에 lines(규칙 줄)·wording({text, source}) 을 붙인다. schedule=False 면 캐시만 읽는다(생성 예약 없음)."""
    if impact is None:
        return None
    lines = impact_lines(impact)
    it = item(conn, activity_id, impact, lines)
    if schedule:
        from src.services.ai_wording_live import present_or_warm
        wording = present_or_warm(conn, config, SURFACE, it)
    else:
        wording = aw.present(conn, SURFACE, it.scope_key, it.rule_text, it.facts, it.basis)
    return {**impact, "lines": lines, "wording": wording}


RECENT_DAYS = 14      # 동기화 직후 선생성 범위(사용자 결정 2026-11-20)
RECENT_MAX = 30       # 한 번의 동기화에서 선생성할 최대 활동 수(하루 2회 러닝 대비 여유)


def _today(conn: sqlite3.Connection) -> str:
    from src.services.milestone_events import today_local
    return today_local(conn)


def collect(conn: sqlite3.Connection, today: str | None = None) -> list[aw.Item]:
    """동기화 뒤 워밍용 — 최근 RECENT_DAYS 일 러닝(최대 RECENT_MAX). 이미 최신인 항목은 warm 이 건너뛴다."""
    from datetime import date as _date, timedelta

    from src.services.activity_impact_service import get_activity_impact
    since = (_date.fromisoformat(today or _today(conn)) - timedelta(days=RECENT_DAYS - 1)).isoformat()
    rows = conn.execute("SELECT id FROM v_canonical_activities WHERE distance_m > 0 AND substr(start_time,1,10) >= ?"
                        " ORDER BY start_time DESC LIMIT ?", (since, RECENT_MAX * 2)).fetchall()
    items: list[aw.Item] = []
    for (aid,) in rows:
        imp = get_activity_impact(conn, aid)
        if imp is not None:
            items.append(item(conn, aid, imp, impact_lines(imp)))
        if len(items) >= RECENT_MAX:
            break
    return items

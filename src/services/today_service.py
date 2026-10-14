"""Phase 7 서비스 레이어 - Today(관여 계층 L0~L2) 데이터 조회 + 체크인 저장.

읽기 전용 원칙(Phase 5) + save_checkin()만 쓰기 예외(D3, 07-migration-roadmap.md).
첫 번째 인자는 sqlite3.Connection. 반환값은 dict/list (snake_case 키, 단위 변환 없음).

readiness/training_status 계산은 재구현하지 않고 dashboard_service.get_dashboard_data()를
그대로 재사용한다 — 임계값 테이블(_interpret_level)과 훈련 단계 판정(_get_training_phase)이
이미 거기서 readiness/training_status에 반영돼 있음.

get_today_briefing()은 규칙 기반(임계값)이다 — LLM 미사용.
get_today_narrative()는 AI 우선 + 규칙 기반 fallback — chat_engine provider 체인 재사용.

설계 문서: v0.3/data/phase-7-ui-renewal/06-data-layer-extensions.md (D3, D5)
           v0.3/data/phase-7-ui-renewal/DECISIONS.md [P7-DESIGN-7B-API]
"""
from __future__ import annotations

import sqlite3

from . import input_limits


def get_today_status(conn: sqlite3.Connection, date: str | None = None) -> dict:
    """오늘 상태 지표 — readiness(utrs/cirs/crs) + training_status(ctl/atl/tsb/acwr).

    dashboard_service.get_dashboard_data()의 부분집합. 날짜·wellness·race_predictions·
    weekly_summary는 Today L0/L1에서 쓰지 않으므로 뺀다.

    providers는 dashboard_service가 버리는 metric_store.provider를 UTRS/CIRS/TSB에
    한해 별도로 다시 조회해 얹는다 — MetricCell(C2)의 P3(Provider 배지 필수) 요건 때문.
    dashboard_service.get_dashboard_data()는 v1 레거시 대시보드와 공유하는 함수라 그
    반환 구조는 바꾸지 않는다(추가 쿼리 방식, 순수 additive).
    """
    from src.services.dashboard_service import get_dashboard_data
    from src.utils import db_helpers

    data = get_dashboard_data(conn, date)
    provider_rows = db_helpers.get_primary_metrics(
        conn, "daily", data["date"], names=["utrs", "cirs", "tsb"],
    )
    providers = {r["metric_name"]: r.get("provider") for r in provider_rows}
    return {
        "date": data["date"],
        "readiness": data["readiness"],
        "training_status": data["training_status"],
        "providers": providers,
    }


def _dominant_zone(conn: sqlite3.Connection, start_time: str, config: dict | None) -> dict | None:
    """활동일의 HR존 분포에서 최다 존과 비중. 데이터 없으면 None."""
    from src.analysis.zones_analysis import analyze_zones

    day = start_time[:10]
    z = analyze_zones(conn, day, day + "T99", config)
    if z["data_source"] == "none":
        return None
    key, info = max(z["zone_distribution"].items(), key=lambda kv: kv[1]["pct"])
    return {"zone": int(key[1:]), "pct": round(info["pct"]), "source": z["data_source"]}


def get_recent_activities(conn: sqlite3.Connection, limit: int = 3, config: dict | None = None) -> list[dict]:
    """최근 활동 N개 (v_canonical_activities 기준, 중복 제거됨). 각 항목에 route 미리보기 포함.

    가장 최근 활동에만 hr_zone({zone, pct, source}|None)을 붙인다(S2b 히어로 의미 문장용).
    """
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, name, activity_type, start_time, distance_m, duration_sec, source"
        " FROM v_canonical_activities"
        " ORDER BY start_time DESC LIMIT ?",
        (limit,),
    ).fetchall()
    activities = [dict(r) for r in rows]
    from src.services.activity_service import _route_previews
    previews = _route_previews(conn, [a["id"] for a in activities])
    for a in activities:
        a["route"] = previews.get(a["id"])
    if activities:
        try:
            activities[0]["hr_zone"] = _dominant_zone(conn, activities[0]["start_time"], config)
        except Exception:
            activities[0]["hr_zone"] = None
    return activities


def get_today_briefing(conn: sqlite3.Connection, date: str | None = None) -> dict:
    """규칙 기반(임계값) 한 줄 브리핑 + 근거 리스트.

    LLM 미사용 — coding-rules.md의 "AI 응답 파싱 실패: graceful fallback(규칙 기반)"과
    같은 패턴을 브리핑 자체의 1차 구현으로 사용한다. AI 생성 브리핑으로 업그레이드하는
    건 별도 판단(범위 밖).

    헤드라인·근거는 src.training.fatigue.readiness_decision()로 판정한다(TSB만 보던
    이전 로직 대신 wellness도 함께 본다 — adjuster.py의 당일 계획 조정과 같은 판정
    기준을 공유해 "Today는 핵심 세션, Coach는 항상 휴식" 같은 모순을 없앤다).
    """
    from src.training.fatigue import readiness_decision

    status = get_today_status(conn, date)
    training = status["training_status"]
    readiness = status["readiness"]

    decision = readiness_decision(conn, date=status["date"], tsb=training.get("tsb"))
    headline = decision["headline"]
    evidence: list[dict] = list(decision["evidence"])

    utrs = readiness.get("utrs")
    if utrs and utrs.get("value") is not None:
        evidence.append({
            "type": "metric",
            "metric": "utrs",
            "value": utrs["value"],
            "label": f"UTRS {utrs['value']:.0f} ({utrs.get('level', '')})".strip(),
        })

    # 목표 레이스가 있으면 헤드라인을 레이스 국면에 맞추고 근거를 앞에 붙인다(맥락 있는 안내)
    from src.services.race_hub_service import get_race_hub, race_briefing
    race = race_briefing(get_race_hub(conn, status["date"]), training.get("tsb"))
    if race is not None:
        headline, race_evidence = race
        evidence = race_evidence + evidence

    from src.services._narrative import attach_drill
    attach_drill(conn, evidence, status["date"])
    return {"date": status["date"], "headline": headline, "evidence": evidence}


def get_todays_checkin(conn: sqlite3.Connection, date: str | None = None) -> dict | None:
    """오늘(또는 지정 날짜) 체크인 조회 — 없으면 None.

    QuickInput(C5)의 "이미 당일 입력이 있으면 compact+complete 상태로 표시"
    (03g-common-patterns.md 7-5) 판단에 쓰인다.
    """
    if date is None:
        date = conn.execute("SELECT date('now','localtime')").fetchone()[0]

    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT id, input_date, input_type, fatigue, pain, note, activity_id, created_at"
        " FROM user_inputs WHERE input_date = ? AND input_type = 'checkin'",
        (date,),
    ).fetchone()
    return dict(row) if row else None


def get_today_milestones(conn: sqlite3.Connection, limit: int = 20) -> list[dict]:
    """최근 마일스톤 목록 — Today 1-D 패널용 얇은 wrapper.

    milestone_service.get_recent_milestones()를 그대로 노출한다.
    03a-today.md가 Today L2 조회를 today_service 하나로 묶어서 기대하기 때문.
    """
    from src.services import milestone_service
    return milestone_service.get_recent_milestones(conn, limit=limit)


def get_today_narrative(
    conn: sqlite3.Connection,
    date: str | None = None,
    config: dict | None = None,
    year: int | None = None,
    month: int | None = None,
) -> dict:
    """Today L2 성장 내러티브 — 구현은 today_narrative.get_today_narrative."""
    from src.services import today_narrative

    return today_narrative.get_today_narrative(conn, date=date, config=config, year=year, month=month)



def save_checkin(
    conn: sqlite3.Connection,
    fatigue: int | None = None,
    pain: str | None = None,
    note: str | None = None,
    activity_id: int | None = None,
    input_date: str | None = None,
) -> dict:
    """QuickInput 체크인 저장 — user_inputs UPSERT (D3).

    같은 날짜에 이미 체크인이 있으면 갱신한다(UNIQUE(input_date, input_type)).
    범위 밖 fatigue·알 수 없는 pain 은 ValueError(내부 호출용 최소 불변식 — `input_limits`).
    """
    input_limits.check_checkin(fatigue, pain)
    if input_date is None:
        input_date = conn.execute("SELECT date('now','localtime')").fetchone()[0]

    conn.execute(
        """
        INSERT INTO user_inputs (input_date, input_type, fatigue, pain, note, activity_id)
        VALUES (?, 'checkin', ?, ?, ?, ?)
        ON CONFLICT(input_date, input_type) DO UPDATE SET
            fatigue = excluded.fatigue,
            pain = excluded.pain,
            note = excluded.note,
            activity_id = excluded.activity_id
        """,
        (input_date, fatigue, pain, note, activity_id),
    )
    conn.commit()

    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT id, input_date, input_type, fatigue, pain, note, activity_id, created_at"
        " FROM user_inputs WHERE input_date = ? AND input_type = 'checkin'",
        (input_date,),
    ).fetchone()
    return dict(row)

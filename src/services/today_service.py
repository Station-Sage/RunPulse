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
    """Today L2 성장 내러티브 — AI 우선, 전체 실패 시 규칙 기반 fallback.

    컨텍스트: 이번 달(또는 year/month 지정 달) CTL 변화량, 월간 누적거리·활동수,
    최근 7일 수면 추세, 최근 마일스톤 5개. 이 수치만 프롬프트에 올려 환각 방지.

    year/month 둘 다 있으면 그 달 전체, 이번 달이면 오늘까지, 과거 달이면 말일까지.
    둘 중 하나만 있으면 무시하고 기존(오늘 기준) 동작.

    반환: {date, text, source("ai"|"rule"), evidence, milestones, highlights}
    """
    from src.services import milestone_service
    from src.services.week_digest import week_digests
    from src.services._narrative import (
        attach_drill, build_evidence, build_narrative_prompt, month_date_range,
        get_narrative_cache, peak_ctl_in_range, query_metric, rule_narrative,
        set_narrative_cache, sleep_trend,
    )
    from src.ai.chat_engine import _build_chat_provider_chain, _call_provider, get_ai_provider

    # ── 연월 범위 결정 (get_today_status 호출 전에 확정 — 과거 달 조회 시
    #    training_status가 오늘이 아니라 그 달 기준으로 나와야 함) ──────────
    if year is not None and month is not None:
        month_start, date = month_date_range(year, month)
        month_label: str | None = f"{year}년 {month}월"
        status = get_today_status(conn, date)
    else:
        status = get_today_status(conn, date)
        if date is None:
            date = status["date"]
        month_start = date[:7] + "-01"
        month_label = None

    # ── 캐시 조회 (AI 성공 결과만 저장돼 있음) ────────────────────────────
    cached = get_narrative_cache(conn, month_start, date)
    if cached is not None:
        # 마일스톤은 캐시(내러티브 문장)와 별개로 항상 최신 규칙으로 다시 조회한다
        cached["weeks"] = week_digests(conn, month_start, date)
        cached["milestones"] = milestone_service.get_recent_milestones(
            conn, limit=5, date_from=month_start, date_to=date)
        return cached

    training = status["training_status"]
    ctl_now = training.get("ctl")

    ctl_start = query_metric(conn, "daily", month_start, "ctl")

    # ── 해당 달 누적거리·활동수·최장 러닝 ─────────────────────────────────
    row = conn.execute(
        "SELECT COUNT(*), COALESCE(SUM(distance_m), 0), COALESCE(MAX(distance_m), 0)"
        " FROM v_canonical_activities"
        " WHERE DATE(start_time) >= ? AND DATE(start_time) <= ?",
        (month_start, date),
    ).fetchone()
    month_count = int(row[0]) if row else 0
    month_dist_km = round(float(row[1]) / 1000.0, 1) if row else 0.0
    longest_run_km = round(float(row[2]) / 1000.0, 1) if row and row[2] else 0.0

    peak_ctl = peak_ctl_in_range(conn, month_start, date)

    # ── 수면 추세 (해당 달 말일 기준 최근 7일 vs 이전 7일) ────────────────
    sleep_recent, sleep_prev = sleep_trend(conn, date)

    # ── 최근 마일스톤 (조회 중인 달로 스코프 — 과거 달 조회 시 오늘 기준
    #    "최근" 마일스톤이 뜨지 않게) ────────────────────────────────────────
    milestones = milestone_service.get_recent_milestones(
        conn, limit=5, date_from=month_start, date_to=date,
    )

    # ── evidence 조립 (데이터 있는 항목만) ────────────────────────────────
    period_label = month_label or "이번 달"
    evidence = build_evidence(
        ctl_now, ctl_start, month_dist_km, month_count,
        sleep_recent, sleep_prev, period_label,
    )
    attach_drill(conn, evidence, status["date"])

    # ── highlights 조립 ───────────────────────────────────────────────────
    highlights = {
        "total_distance_km": month_dist_km,
        "activity_count": month_count,
        "longest_run_km": longest_run_km,
        "peak_ctl": peak_ctl,
    }

    weeks = week_digests(conn, month_start, date)
    # ── AI 생성 시도 ───────────────────────────────────────────────────────
    text = None
    source = "rule"
    provider = get_ai_provider(config)
    chain = _build_chat_provider_chain(provider, config)
    if chain:
        prompt = build_narrative_prompt(
            date, ctl_now, ctl_start, month_dist_km, month_count,
            sleep_recent, sleep_prev, month_label=month_label, weeks=weeks,
        )
        for prov in chain:
            ai_result = _call_provider(prov, prompt, config)
            if ai_result:
                text = ai_result
                source = "ai"
                break

    if text is None:
        text = rule_narrative(
            ctl_now, ctl_start, month_dist_km, month_count,
            sleep_recent, sleep_prev, month_label=month_label,
        )

    out = {
        "date": date,
        "text": text,
        "source": source,
        "evidence": evidence,
        "milestones": milestones,
        "highlights": highlights,
        "weeks": weeks,
    }
    # ── AI 성공 시에만 캐시 저장 ───────────────────────────────────────────
    if source == "ai":
        set_narrative_cache(conn, month_start, date, out)
    return out


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
    """
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

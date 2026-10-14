"""Today L2 성장 내러티브 — AI 우선, 규칙 기반 fallback (today_service 에서 분리, 300줄 캡).

외부 진입점은 `today_service.get_today_narrative` (얇은 위임). 비러닝은 러닝 합계와 별도 한 줄로만 다룬다(ADR-051).
"""
from __future__ import annotations

import sqlite3


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
    from src.services.today_service import get_today_status
    from src.services.run_totals import other_line, other_totals, run_totals
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
    rt = run_totals(conn, month_start, date)
    month_count, month_dist_km, longest_run_km = rt["count"], rt["distance_km"], rt["longest_km"]
    month_other = other_totals(conn, month_start, date)

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
        "other": month_other,
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
            other_line=other_line(month_other),
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

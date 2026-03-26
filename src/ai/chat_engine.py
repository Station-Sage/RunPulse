"""AI 채팅 엔진 — 교체 가능 구조.

config.json의 ai.provider 설정에 따라 다른 AI API 호출.
지원: 'rule' (규칙 기반 fallback), 'claude', 'openai', 'genspark'.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from typing import Any

log = logging.getLogger(__name__)


def get_ai_provider(config: dict | None = None) -> str:
    """설정에서 AI 제공자 이름 반환."""
    if not config:
        return "rule"
    return config.get("ai", {}).get("provider", "rule")


def chat(
    conn: sqlite3.Connection,
    user_message: str,
    config: dict | None = None,
    chip_id: str | None = None,
) -> str:
    """사용자 메시지에 대한 AI 응답 생성.

    Args:
        conn: DB 연결 (컨텍스트 빌드용).
        user_message: 사용자 입력 텍스트.
        config: 설정 dict.
        chip_id: 추천 칩 ID (칩 클릭 시).

    Returns:
        AI 응답 텍스트 (마크다운).
    """
    provider = get_ai_provider(config)

    # 프롬프트 빌드
    if chip_id:
        from .briefing import build_chip_prompt
        prompt = build_chip_prompt(conn, chip_id)
    else:
        from .ai_context import build_context, format_context_text
        ctx = build_context(conn)
        ctx_text = format_context_text(ctx)
        prompt = f"당신은 RunPulse AI 러닝 코치입니다. 아래 분석 데이터를 참고하여 답변하세요.\n\n{ctx_text}\n\n사용자 질문: {user_message}"

    # 제공자별 분기
    if provider == "claude":
        return _call_claude(prompt, config)
    elif provider == "openai":
        return _call_openai(prompt, config)
    elif provider == "genspark":
        return _call_genspark(prompt, config)
    else:
        return _rule_based_response(conn, user_message, chip_id)


def _rule_based_response(
    conn: sqlite3.Connection,
    user_message: str,
    chip_id: str | None = None,
) -> str:
    """규칙 기반 fallback 응답 (API 없을 때). 키워드 매칭."""
    from .ai_context import build_context

    ctx = build_context(conn)
    parts: list[str] = []
    msg = user_message.lower()

    # 칩별 특화 응답
    if chip_id == "today_deep":
        act = ctx.get("today_activity")
        if act:
            parts.append(f"**오늘 활동 분석**\n- 거리: {act.get('distance_km', '-')}km\n"
                         f"- 페이스: {act.get('avg_pace_sec_km', '-')}초/km\n"
                         f"- 심박: {act.get('avg_hr', '-')}bpm")
        else:
            parts.append("오늘은 아직 활동이 기록되지 않았습니다.")
    elif chip_id == "weekly_review":
        wk = ctx.get("weekly") or {}
        parts.append(f"**이번 주 훈련 리뷰**\n- 점수: {wk.get('total_score', '-')}\n"
                     f"- 거리: {wk.get('total_distance_km', '-')}km\n"
                     f"- 횟수: {wk.get('run_count', '-')}회")
    elif chip_id == "recovery_advice":
        rec = ctx.get("recovery") or {}
        grade = rec.get("grade", "정보 없음")
        parts.append(f"**회복 상태**: {grade}\n\n"
                     "충분한 수면과 수분 섭취를 유지하세요. "
                     "바디 배터리가 50 이하라면 저강도 훈련을 권장합니다.")
    elif chip_id == "injury_risk":
        acwr = ctx.get("acwr") or {}
        avg = (acwr.get("average") or {}) if acwr else {}
        status = avg.get("status", "정보 없음")
        parts.append(f"**부상 위험 분석**\n- ACWR 상태: {status}\n\n"
                     "ACWR이 1.3 이상이면 부하 급증 위험이 있습니다. "
                     "훈련량을 10% 이내로 점진적으로 늘리세요.")
    # 키워드 기반 분기 (칩 없을 때)
    elif any(k in msg for k in ["강도", "오늘 훈련", "뭐 해", "무슨 운동", "할까"]):
        _respond_training_recommendation(parts, ctx)
    elif any(k in msg for k in ["마라톤", "레이스", "준비도", "대회"]):
        _respond_race_readiness(parts, ctx, conn)
    elif any(k in msg for k in ["회복", "컨디션", "피로", "쉬어"]):
        _respond_recovery(parts, ctx)
    elif any(k in msg for k in ["페이스", "속도", "빨라", "느려", "기록"]):
        _respond_pace(parts, ctx, conn)
    elif any(k in msg for k in ["부상", "위험", "cirs", "acwr", "과훈련"]):
        _respond_injury(parts, ctx)
    elif any(k in msg for k in ["주간", "이번주", "이번 주", "weekly"]):
        _respond_weekly(parts, ctx)
    elif any(k in msg for k in ["vo2", "vdot", "체력", "피트니스"]):
        _respond_fitness(parts, ctx, conn)
    else:
        # 기본: 컨텍스트 기반 종합 응답
        _respond_general(parts, ctx, conn, user_message)

    return "\n".join(parts) if parts else "데이터가 충분하지 않아 분석이 어렵습니다. 동기화 후 다시 시도해주세요."


def _respond_training_recommendation(parts: list[str], ctx: dict) -> None:
    """훈련 강도 추천."""
    rec = ctx.get("recovery") or {}
    fit = ctx.get("fitness") or {}
    tsb = fit.get("tsb")
    grade = rec.get("grade", "")

    parts.append("**오늘의 훈련 추천**")
    if grade in ("A", "B"):
        parts.append("컨디션 양호! 고강도 훈련(인터벌/템포) 가능합니다.")
    elif grade == "C":
        parts.append("보통 컨디션. 중강도(이지런/템포) 권장합니다.")
    else:
        parts.append("피로 회복이 필요합니다. 가벼운 조깅이나 휴식을 권장합니다.")

    if tsb is not None:
        if tsb > 5:
            parts.append(f"- TSB {tsb:+.1f} — 신선한 상태. 강도 높여도 됩니다.")
        elif tsb > -10:
            parts.append(f"- TSB {tsb:+.1f} — 적정 훈련 상태.")
        else:
            parts.append(f"- TSB {tsb:+.1f} — 피로 축적. 볼륨 줄이세요.")

    plan = ctx.get("plan_today")
    if plan:
        wtype = plan.get("workout_type", "")
        dist = plan.get("distance_km")
        parts.append(f"\n📋 오늘 계획: **{wtype}**" + (f" {dist}km" if dist else ""))


def _respond_race_readiness(parts: list[str], ctx: dict, conn) -> None:
    """레이스 준비도."""
    goal = ctx.get("goal")
    parts.append("**레이스 준비도**")

    if goal:
        parts.append(f"- 목표: {goal.get('name', '-')} ({goal.get('distance_km', '-')}km)")
        race_date = goal.get("race_date")
        if race_date:
            from datetime import date
            try:
                days_left = (date.fromisoformat(race_date) - date.today()).days
                parts.append(f"- D-{days_left}")
            except ValueError:
                pass
    else:
        parts.append("설정된 목표 레이스가 없습니다. 훈련 탭에서 목표를 추가하세요.")

    # RRI, VDOT
    rri_row = conn.execute(
        "SELECT metric_value FROM computed_metrics WHERE metric_name='RRI' "
        "AND activity_id IS NULL ORDER BY date DESC LIMIT 1"
    ).fetchone()
    if rri_row and rri_row[0]:
        rri = float(rri_row[0])
        status = "준비 완료! 🎉" if rri >= 80 else "보통. 추가 훈련 필요." if rri >= 60 else "부족. 훈련을 늘리세요."
        parts.append(f"- RRI(준비도): {rri:.0f}/100 — {status}")


def _respond_recovery(parts: list[str], ctx: dict) -> None:
    """회복 조언."""
    rec = ctx.get("recovery") or {}
    raw = rec.get("raw") or {}
    parts.append("**회복 상태 분석**")
    parts.append(f"- 회복 등급: {rec.get('grade', '정보 없음')}")

    bb = raw.get("body_battery")
    if bb is not None:
        if bb >= 60:
            parts.append(f"- 바디배터리: {bb} — 양호. 일상 훈련 가능.")
        elif bb >= 30:
            parts.append(f"- 바디배터리: {bb} — 보통. 중강도까지 권장.")
        else:
            parts.append(f"- 바디배터리: {bb} — 낮음. 충분한 휴식 필요.")

    sleep = raw.get("sleep_score")
    if sleep is not None:
        parts.append(f"- 수면 점수: {sleep}" + (" — 수면 부족. 일찍 취침하세요." if sleep < 60 else ""))

    hrv = raw.get("hrv_value")
    if hrv is not None:
        parts.append(f"- HRV: {hrv}ms")

    parts.append("\n💡 회복 팁: 충분한 수분 섭취, 7~9시간 수면, 스트레칭/폼롤링 권장")


def _respond_pace(parts: list[str], ctx: dict, conn) -> None:
    """페이스/기록 관련."""
    parts.append("**페이스 분석**")

    eftp_row = conn.execute(
        "SELECT metric_value, metric_json FROM computed_metrics WHERE metric_name='eFTP' "
        "AND activity_id IS NULL ORDER BY date DESC LIMIT 1"
    ).fetchone()
    if eftp_row and eftp_row[0]:
        pace = int(eftp_row[0])
        m, s = divmod(pace, 60)
        parts.append(f"- 역치 페이스(eFTP): {m}:{s:02d}/km")

    vdot_row = conn.execute(
        "SELECT metric_value FROM computed_metrics WHERE metric_name='VDOT' "
        "AND activity_id IS NULL ORDER BY date DESC LIMIT 1"
    ).fetchone()
    if vdot_row and vdot_row[0]:
        parts.append(f"- VDOT: {float(vdot_row[0]):.1f}")

    act = ctx.get("today_activity")
    if act and act.get("avg_pace_sec_km"):
        p = act["avg_pace_sec_km"]
        m, s = divmod(int(p), 60)
        parts.append(f"- 오늘 평균 페이스: {m}:{s:02d}/km")

    parts.append("\n💡 페이스를 올리려면: 주 1~2회 인터벌/템포런 + 주간 거리 10% 이내 점진적 증가")


def _respond_injury(parts: list[str], ctx: dict) -> None:
    """부상 위험 분석."""
    acwr = ctx.get("acwr") or {}
    avg = (acwr.get("average") or {}) if acwr else {}
    parts.append("**부상 위험 분석**")
    acwr_val = avg.get("acwr")
    if acwr_val:
        status = "적정" if 0.8 <= acwr_val <= 1.3 else "주의" if acwr_val <= 1.5 else "위험"
        parts.append(f"- ACWR: {acwr_val} ({status})")
    parts.append("\n💡 부상 예방: 주간 훈련량 10% 이내 증가, 다양한 강도 혼합, 충분한 회복일")


def _respond_weekly(parts: list[str], ctx: dict) -> None:
    """주간 리뷰."""
    wk = ctx.get("weekly") or {}
    parts.append("**이번 주 훈련 리뷰**")
    parts.append(f"- 점수: {wk.get('total_score', '-')}")
    parts.append(f"- 거리: {wk.get('total_distance_km', '-')}km")
    parts.append(f"- 횟수: {wk.get('run_count', '-')}회")

    trends = ctx.get("trends_4w") or []
    if trends:
        parts.append("\n📊 4주 추세:")
        for t in trends[-4:]:
            parts.append(f"  {t['week_start']}: {t['total_distance_km']}km ({t['run_count']}회)")


def _respond_fitness(parts: list[str], ctx: dict, conn) -> None:
    """체력/피트니스."""
    fit = ctx.get("fitness") or {}
    parts.append("**피트니스 현황**")
    ctl = fit.get("ctl")
    if ctl is not None:
        parts.append(f"- CTL(만성부하): {ctl:.1f}")
    vo2 = fit.get("vo2max_garmin") or fit.get("vo2max_runalyze")
    if vo2:
        parts.append(f"- VO2Max: {vo2:.1f}")

    vdot_row = conn.execute(
        "SELECT metric_value FROM computed_metrics WHERE metric_name='VDOT' "
        "AND activity_id IS NULL ORDER BY date DESC LIMIT 1"
    ).fetchone()
    if vdot_row and vdot_row[0]:
        parts.append(f"- VDOT: {float(vdot_row[0]):.1f}")

    rec_row = conn.execute(
        "SELECT metric_value FROM computed_metrics WHERE metric_name='REC' "
        "AND activity_id IS NULL ORDER BY date DESC LIMIT 1"
    ).fetchone()
    if rec_row and rec_row[0]:
        parts.append(f"- 러닝 효율성(REC): {float(rec_row[0]):.0f}/100")


def _respond_general(parts: list[str], ctx: dict, conn, user_message: str) -> None:
    """키워드 매칭 안 될 때 종합 응답."""
    parts.append(f"**\"{user_message}\"에 대한 분석**\n")

    # 핵심 지표 요약
    fit = ctx.get("fitness") or {}
    rec = ctx.get("recovery") or {}
    if fit.get("tsb") is not None:
        parts.append(f"- TSB(신선도): {fit['tsb']:+.1f}")
    if rec.get("grade"):
        parts.append(f"- 회복 등급: {rec['grade']}")

    # 최근 활동
    act = ctx.get("today_activity")
    if act:
        parts.append(f"- 오늘 활동: {act.get('distance_km', '-')}km, "
                     f"페이스 {act.get('avg_pace_sec_km', '-')}초/km")

    goal = ctx.get("goal")
    if goal:
        parts.append(f"- 목표: {goal.get('name', '-')}")

    parts.append("\n💡 더 정확한 답변을 원하시면:")
    parts.append("- 설정 > AI에서 Claude 또는 ChatGPT API 키를 입력하세요")
    parts.append("- 또는 구체적으로 질문해주세요 (예: '오늘 훈련 강도는?', '마라톤 준비도 확인')")

    return "\n".join(parts) if parts else "데이터가 충분하지 않아 분석이 어렵습니다. 동기화 후 다시 시도해주세요."


def _call_claude(prompt: str, config: dict | None) -> str:
    """Claude API 호출 (향후 구현)."""
    api_key = (config or {}).get("ai", {}).get("claude_api_key", "")
    if not api_key:
        return "Claude API 키가 설정되지 않았습니다. 설정 > AI에서 키를 입력하세요."
    try:
        import httpx
        resp = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"]
    except Exception as exc:
        log.warning("Claude API 오류: %s", exc)
        return f"AI 응답 생성 실패: {exc}"


def _call_openai(prompt: str, config: dict | None) -> str:
    """OpenAI API 호출 (향후 구현)."""
    api_key = (config or {}).get("ai", {}).get("openai_api_key", "")
    if not api_key:
        return "OpenAI API 키가 설정되지 않았습니다."
    try:
        import httpx
        resp = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 1024,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except Exception as exc:
        log.warning("OpenAI API 오류: %s", exc)
        return f"AI 응답 생성 실패: {exc}"


def _call_genspark(prompt: str, config: dict | None) -> str:
    """Genspark API 호출 (무료, 향후 구현)."""
    return ("Genspark 연동은 아직 구현되지 않았습니다. "
            "config.json에서 ai.provider를 'claude' 또는 'openai'로 변경하세요.")

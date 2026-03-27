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


class RateLimitError(Exception):
    """429 Too Many Requests — provider 전환 트리거."""
    pass


def chat(
    conn: sqlite3.Connection,
    user_message: str,
    config: dict | None = None,
    chip_id: str | None = None,
) -> str:
    """사용자 메시지에 대한 AI 응답 생성 — provider chain fallback 지원.

    Args:
        conn: DB 연결 (컨텍스트 빌드용).
        user_message: 사용자 입력 텍스트.
        config: 설정 dict.
        chip_id: 추천 칩 ID (칩 클릭 시).

    Returns:
        AI 응답 텍스트 (마크다운).
    """
    provider = get_ai_provider(config)

    # 최근 대화 이력 (맥락 유지)
    chat_history = _load_recent_chat(conn, limit=6)

    # 프롬프트 빌드
    if chip_id:
        from .briefing import build_chip_prompt
        prompt = build_chip_prompt(conn, chip_id)
    else:
        from .chat_context import build_chat_context
        ctx_text = build_chat_context(conn, user_message, chat_history, provider=provider)
        prompt = _build_system_prompt(ctx_text, user_message, chat_history)

    # provider chain: 선택 → gemini → groq → rule
    chain = _build_chat_provider_chain(provider, config)
    for prov in chain:
        try:
            # Function calling 지원 provider는 도구 기반 호출
            if prov == "gemini" and not chip_id:
                result = _call_gemini_with_tools(conn, prompt, config)
                if result:
                    return result
                continue
            result = _call_provider(prov, prompt, config)
            if result:
                return result
        except RateLimitError:
            log.warning("%s 429 → 다음 provider로 전환", prov)
            continue
        except Exception:
            log.warning("provider '%s' 실패, 다음으로", prov, exc_info=True)
            continue

    return _rule_based_response(conn, user_message, chip_id)


def _build_chat_provider_chain(selected: str, config: dict | None) -> list[str]:
    """채팅용 provider 시도 순서."""
    ai_cfg = (config or {}).get("ai", {})
    chain = []
    _PROVIDERS = {"gemini", "groq", "claude", "openai"}
    if selected in _PROVIDERS:
        chain.append(selected)
    if "gemini" not in chain and ai_cfg.get("gemini_api_key"):
        chain.append("gemini")
    if "groq" not in chain and ai_cfg.get("groq_api_key"):
        chain.append("groq")
    return chain


def _call_provider(provider: str, prompt: str, config: dict | None) -> str | None:
    """단일 provider 호출. 성공 시 텍스트, 실패/429 시 None."""
    _dispatch = {
        "gemini": _call_gemini, "groq": _call_groq,
        "claude": _call_claude, "openai": _call_openai,
    }
    fn = _dispatch.get(provider)
    if not fn:
        return None
    try:
        result = fn(prompt, config)
        if result and "설정되지 않았습니다" not in result and "실패" not in result:
            return result
        return None
    except RateLimitError:
        log.warning("%s 429 rate limit → 다음 provider로 전환", provider)
        return None
    except Exception as exc:
        log.warning("provider '%s' 호출 실패: %s", provider, exc)
        return None


_SYSTEM_PROMPT = """당신은 RunPulse AI 러닝 코치입니다. 반드시 한국어로만 답변하세요.

## 핵심 원칙
- 아래 제공된 데이터만 사용. 데이터에 없는 수치를 만들어내지 마세요.
- 거리/페이스/시간은 소수점 1자리까지만 표시 (예: 21.0km, 5:30/km).
- 이전 대화 맥락을 반드시 이어서 답변하세요.

## 훈련 조언 원칙
- 대회 임박(D-14 이내): 테이퍼링 추천 (볼륨 감량, 강도 유지, 고강도 세션 축소)
- 대회 임박(D-7 이내): 경량 조깅/완전 휴식 추천
- CIRS < 30 + ACWR 0.8~1.3: 정상 훈련 가능. 이지런만 추천하지 마세요.
- 사용자가 "더 강하게", "스피드", "템포" 등 고강도를 원하면 데이터가 허용하는 범위에서 수용하세요.
- 훈련 추천 시 반드시 구체적으로: "내일 6km 템포런 (5:10/km 목표)" 형태.

## 데이터 해석
- CIRS < 25: 부상 위험 낮음, 고강도 가능
- CIRS 25~50: 주의, 중강도 권장
- CIRS > 75: 휴식 필수
- ACWR 0.8~1.3: 안전 범위
- TSB > 0: 신선, TSB < -20: 피로 축적

## 훈련 계획 추천 형식
사용자가 훈련 스케줄/계획을 요청하면 반드시 아래 형식으로 답변:

**[날짜] [훈련 유형] [총 거리]km**
- 워밍업: [거리]km @ [페이스]/km
- 메인: [거리]km × [세트]회 @ [페이스]/km (회복 조깅 [거리]km @ [페이스]/km)
- 쿨다운: [거리]km @ [페이스]/km

예시:
**3/29(토) 템포런 10km**
- 워밍업: 2km @ 6:00/km
- 메인: 6km @ 5:10/km
- 쿨다운: 2km @ 6:30/km

**3/30(일) 인터벌 8km**
- 워밍업: 2km @ 6:00/km
- 메인: 1km × 4회 @ 4:30/km (회복 조깅 400m @ 6:30/km)
- 쿨다운: 1.6km @ 6:30/km

페이스는 Daniels VDOT 기반 E/M/T/I pace를 사용하세요.

## 응답 형식
1. 3~7문장 (훈련 계획 요청 시 필요한 만큼 길게).
2. 질문에 직접 답변부터.
3. 응답 마지막에 추천 질문 3개:
   [추천: 질문1 | 질문2 | 질문3]
"""


def _build_system_prompt(context: str, user_message: str,
                         chat_history: list[dict] | None = None) -> str:
    """시스템 프롬프트 + 컨텍스트 + 대화 이력 + 질문 조합."""
    parts = [_SYSTEM_PROMPT, "\n", context]

    if chat_history:
        parts.append("\n\n## 이전 대화")
        for msg in chat_history:
            role = "사용자" if msg.get("role") == "user" else "코치"
            parts.append(f"\n{role}: {msg.get('content', '')[:200]}")

    parts.append(f"\n\n## 사용자 질문\n{user_message}")
    return "".join(parts)


def _load_recent_chat(conn: sqlite3.Connection, limit: int = 3) -> list[dict]:
    """최근 채팅 이력 로드 (프롬프트 컨텍스트용)."""
    try:
        rows = conn.execute(
            "SELECT role, content FROM chat_messages ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [{"role": r[0], "content": r[1]} for r in reversed(rows)]
    except Exception:
        return []


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


def _call_gemini_with_tools(conn: sqlite3.Connection, prompt: str,
                            config: dict | None) -> str | None:
    """Gemini Function Calling — AI가 도구를 호출하여 DB 데이터 수집 후 답변."""
    api_key = (config or {}).get("ai", {}).get("gemini_api_key", "")
    if not api_key:
        return None
    model = (config or {}).get("ai", {}).get("gemini_model", "gemini-2.0-flash")
    temp = (config or {}).get("ai", {}).get("_temperature", 0.7)

    from .tools import TOOL_DECLARATIONS, execute_tool
    try:
        import httpx

        # 1차 호출: 프롬프트 + 도구 목록
        contents = [{"parts": [{"text": prompt}]}]
        body: dict = {
            "contents": contents,
            "tools": [{"function_declarations": TOOL_DECLARATIONS}],
            "generationConfig": {"maxOutputTokens": 2048, "temperature": temp},
        }

        max_rounds = 3  # 최대 도구 호출 횟수
        for _ in range(max_rounds):
            resp = httpx.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                params={"key": api_key},
                headers={"Content-Type": "application/json"},
                json=body, timeout=60,
            )
            if resp.status_code == 429:
                raise RateLimitError("Gemini 429")
            resp.raise_for_status()
            data = resp.json()

            candidates = data.get("candidates", [])
            if not candidates:
                return None

            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts:
                return None

            # 텍스트 응답 확인
            text_parts = [p["text"] for p in parts if "text" in p]
            func_calls = [p["functionCall"] for p in parts if "functionCall" in p]

            if not func_calls:
                # 도구 호출 없음 → 텍스트 답변 반환
                return text_parts[0] if text_parts else None

            # 도구 호출 실행
            # 대화에 AI 응답 추가
            contents.append({"role": "model", "parts": parts})

            # 각 함수 호출 실행 + 결과 추가
            func_response_parts = []
            for fc in func_calls:
                fn_name = fc["name"]
                fn_args = fc.get("args", {})
                log.info("Gemini 도구 호출: %s(%s)", fn_name, fn_args)
                result_json = execute_tool(conn, fn_name, fn_args)
                func_response_parts.append({
                    "functionResponse": {
                        "name": fn_name,
                        "response": {"content": result_json},
                    }
                })

            contents.append({"parts": func_response_parts})
            body["contents"] = contents

        # max_rounds 초과
        log.warning("Gemini function calling %d회 초과", max_rounds)
        return text_parts[0] if text_parts else None

    except RateLimitError:
        raise
    except Exception as exc:
        log.warning("Gemini function calling 실패: %s", exc)
        return None


def _call_gemini(prompt: str, config: dict | None) -> str:
    """Google Gemini API 호출 (무료 tier). 429 시 RateLimitError."""
    api_key = (config or {}).get("ai", {}).get("gemini_api_key", "")
    if not api_key:
        return "Gemini API 키가 설정되지 않았습니다. 설정 > AI에서 키를 입력하세요.\n발급: https://aistudio.google.com/apikey"
    model = (config or {}).get("ai", {}).get("gemini_model", "gemini-2.0-flash")
    temp = (config or {}).get("ai", {}).get("_temperature", 0.7)
    try:
        import httpx
        resp = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            params={"key": api_key},
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "maxOutputTokens": 2048,
                    "temperature": temp,
                },
            },
            timeout=60,
        )
        if resp.status_code == 429:
            log.warning("Gemini 429 Too Many Requests")
            raise RateLimitError("Gemini 429")
        resp.raise_for_status()
        data = resp.json()
        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts:
                return parts[0].get("text", "빈 응답")
        return "Gemini에서 빈 응답을 받았습니다."
    except RateLimitError:
        raise
    except Exception as exc:
        log.warning("Gemini API 오류: %s", exc)
        return f"Gemini 응답 생성 실패: {exc}"


def _call_groq(prompt: str, config: dict | None) -> str:
    """Groq API 호출 (무료 tier, Llama 3.3 70B 등). 429 시 RateLimitError."""
    api_key = (config or {}).get("ai", {}).get("groq_api_key", "")
    if not api_key:
        return "Groq API 키가 설정되지 않았습니다. 설정 > AI에서 키를 입력하세요.\n발급: https://console.groq.com/keys"
    model = (config or {}).get("ai", {}).get("groq_model", "llama-3.3-70b-versatile")
    temp = (config or {}).get("ai", {}).get("_temperature", 0.7)
    try:
        import httpx
        resp = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 2048,
                "temperature": temp,
            },
            timeout=60,
        )
        if resp.status_code == 429:
            log.warning("Groq 429 Too Many Requests")
            raise RateLimitError("Groq 429")
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except RateLimitError:
        raise
    except Exception as exc:
        log.warning("Groq API 오류: %s", exc)
        return f"Groq 응답 생성 실패: {exc}"


def _call_genspark(prompt: str, config: dict | None) -> str:
    """Genspark 수동 모드 — 프롬프트를 준비하고 사용자가 붙여넣기.

    이 모드에서는 실제 AI 호출을 하지 않고, 프롬프트를 저장해둡니다.
    사용자가 Genspark에서 응답을 받아 붙여넣기하면 저장됩니다.
    """
    # 프롬프트를 _last_prompt에 저장 (UI에서 접근)
    _call_genspark._last_prompt = prompt
    return (
        "📋 **프롬프트가 준비되었습니다.**\n\n"
        "1. 아래 '프롬프트 복사' 버튼을 클릭하세요\n"
        "2. [Genspark AI 채팅](https://www.genspark.ai/agents?type=ai_chat)을 열어 붙여넣으세요\n"
        "3. AI 응답을 받으면 '응답 붙여넣기'에 입력하세요"
    )

_call_genspark._last_prompt = ""


def _call_genspark_selenium(prompt: str, config: dict | None) -> str:
    """Genspark 자동 모드 — proot + Selenium으로 DOM 자동화.

    설정 필요: proot-distro + chromium + chromedriver + selenium
    """
    try:
        from src.ai.genspark_driver import send_and_receive
        return send_and_receive(prompt)
    except ImportError:
        return ("Genspark 자동 모드에는 proot + Selenium 설정이 필요합니다.\n"
                "설정 → AI에서 'genspark' (수동 모드)로 변경하세요.")
    except Exception as exc:
        log.warning("Genspark Selenium 오류: %s", exc)
        return f"Genspark 자동 모드 오류: {exc}"

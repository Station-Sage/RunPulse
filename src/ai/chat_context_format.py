"""AI 채팅 컨텍스트 — 포맷터 (컨텍스트 dict → 프롬프트 텍스트).

chat_context.py에서 분리 (2026-03-29).
"""
from __future__ import annotations

from datetime import date

from .chat_context_utils import _fmt_sec, seconds_to_pace


def _format_chat_context(ctx: dict, message: str,
                         chat_history: list[dict] | None = None) -> str:
    """컨텍스트 dict → 프롬프트 텍스트."""
    lines: list[str] = [f"## 러너 현재 상태 ({ctx['date']})"]

    # 주요 지표
    metrics = []
    for name in ["UTRS", "CIRS", "ACWR", "DI", "RTTI"]:
        v = ctx.get(name)
        if v is not None:
            metrics.append(f"{name}={v}")
    if ctx.get("ctl"):
        metrics.append(f"CTL={ctx['ctl']}")
    if ctx.get("tsb") is not None:
        metrics.append(f"TSB={ctx['tsb']:+.1f}")
    if ctx.get("vo2max"):
        metrics.append(f"VO2Max={ctx['vo2max']}")
    if metrics:
        lines.append("주요 지표: " + " | ".join(metrics))

    # 웰니스
    w = ctx.get("wellness")
    if w:
        parts = []
        if w.get("bb") is not None:
            parts.append(f"바디배터리={w['bb']}")
        if w.get("sleep") is not None:
            parts.append(f"수면={w['sleep']}")
        if w.get("hrv") is not None:
            parts.append(f"HRV={int(w['hrv'])}ms")
        if w.get("stress") is not None:
            parts.append(f"스트레스={int(w['stress'])}")
        if w.get("rhr") is not None:
            parts.append(f"안정심박={int(w['rhr'])}")
        if parts:
            lines.append("오늘 컨디션: " + " | ".join(parts))

    # 러너 프로필
    rp = ctx.get("runner_profile", {})
    if rp:
        rp_parts = []
        if rp.get("weekly_avg_km"):
            rp_parts.append(f"주간 평균 {rp['weekly_avg_km']}km/{rp.get('weekly_avg_runs', '?')}회")
        if rp.get("avg_pace"):
            rp_parts.append(f"평균 페이스 {rp['avg_pace']}/km")
        if rp.get("vo2max"):
            rp_parts.append(f"VO2Max={rp['vo2max']}")
        if rp.get("vdot_adj"):
            rp_parts.append(f"VDOT={rp['vdot_adj']}")
        if rp.get("goal"):
            dday = f" D-{rp['race_dday']}" if rp.get("race_dday") else ""
            rp_parts.append(f"목표: {rp['goal']}{dday}")
        if rp_parts:
            lines.append("프로필: " + " | ".join(rp_parts))

    # 30일 전체 활동 (Gemini)
    acts_30d = ctx.get("activities_30d", [])
    if acts_30d:
        lines.append(f"\n### 최근 30일 활동 ({len(acts_30d)}개)")
        for a in acts_30d:
            dur = _fmt_sec(a.get("sec")) if a.get("sec") else "-"
            name = a.get("name") or "러닝"
            lines.append(f"- {a['date']} {name}: {a.get('km', '-')}km, "
                        f"{a.get('pace', '-')}/km, HR {a.get('avg_hr', '-')}, {dur}")

    # 14일 활동 (Claude/OpenAI)
    acts_14d = ctx.get("activities_14d", [])
    if acts_14d and not acts_30d:
        lines.append(f"\n### 최근 14일 활동 ({len(acts_14d)}개)")
        for a in acts_14d:
            lines.append(f"- {a['date']}: {a.get('km', '-')}km, "
                        f"{a.get('pace', '-')}/km, HR {a.get('avg_hr', '-')}")

    # 최근 활동 3개 (Groq/rule)
    if not acts_30d and not acts_14d:
        recent = ctx.get("recent_activities", [])
        if recent:
            lines.append("\n### 최근 활동")
            for a in recent:
                pace = seconds_to_pace(a["pace"]) if a.get("pace") else "-"
                lines.append(f"- {a['date']}: {a.get('km', '-')}km, {pace}/km, HR {a.get('hr', '-')}")

    # 30일 일별 메트릭 (Gemini)
    dm_30d = ctx.get("daily_metrics_30d", {})
    if dm_30d:
        lines.append(f"\n### 30일 메트릭 추세 ({len(dm_30d)}일)")
        for d in sorted(dm_30d.keys()):
            vals = dm_30d[d]
            parts = [f"{k}={v}" for k, v in vals.items()]
            lines.append(f"- {d}: {', '.join(parts)}")

    # 30일 웰니스 (Gemini)
    w30 = ctx.get("wellness_30d", [])
    if w30:
        lines.append(f"\n### 30일 웰니스 ({len(w30)}일)")
        for d in w30:
            lines.append(f"- {d['date']}: BB={d.get('bb', '-')} 수면={d.get('sleep', '-')} "
                        f"HRV={d.get('hrv', '-')} 스트레스={d.get('stress', '-')} RHR={d.get('rhr', '-')}")

    # 14일 웰니스 (Claude/OpenAI)
    w14 = ctx.get("wellness_14d", [])
    if w14 and not w30:
        lines.append(f"\n### 14일 웰니스 ({len(w14)}일)")
        for d in w14:
            lines.append(f"- {d['date']}: BB={d.get('bb', '-')} 수면={d.get('sleep', '-')} "
                        f"HRV={d.get('hrv', '-')} 스트레스={d.get('stress', '-')}")

    # 30일 피트니스 (Gemini)
    f30 = ctx.get("fitness_30d", [])
    if f30:
        lines.append(f"\n### 30일 피트니스 ({len(f30)}일)")
        for d in f30[-10:]:
            lines.append(f"- {d['date']}: CTL={d.get('ctl', '-')} ATL={d.get('atl', '-')} "
                        f"TSB={d.get('tsb', '-')}")
        if len(f30) > 10:
            lines.append(f"  (이전 {len(f30)-10}일 데이터 포함)")

    # 레이스 이력
    rh = ctx.get("race_history", [])
    if rh:
        lines.append(f"\n### 레이스 이력 ({len(rh)}개)")
        for r in rh:
            dur = _fmt_sec(r.get("sec")) if r.get("sec") else "-"
            lines.append(f"- {r['date']} {r.get('name', '레이스')}: "
                        f"{r.get('km', '-')}km, {r.get('pace', '-')}/km, {dur}")

    # 같은 유형 과거 활동
    sim = ctx.get("similar_activities")
    if sim:
        lines.append(f"\n### 오늘과 같은 유형({sim['type']}) 과거 활동")
        for a in sim["history"]:
            lines.append(f"- {a['date']}: {a.get('km', '-')}km, "
                        f"{a.get('pace', '-')}/km, HR {a.get('hr', '-')}")

    # 오늘 활동 상세
    td = ctx.get("today_detail")
    if td:
        lines.append(f"\n### 오늘 활동 상세")
        lines.append(f"- {td.get('distance_km', '-')}km, {td.get('pace', '-')}/km, "
                     f"HR {td.get('avg_hr', '-')}/{td.get('max_hr', '-')}")
        if td.get("workout_type"):
            lines.append(f"- 분류: {td['workout_type']}")
        if td.get("metrics"):
            m = td["metrics"]
            for k, v in m.items():
                lines.append(f"- {k}: {v}")
    elif ctx.get("intent") == "today":
        lines.append("\n### 오늘 활동: 아직 없음")

    # 레이스 준비
    if ctx.get("darp_trend"):
        lines.append("\n### DARP/VDOT 12주 추세")
        for d in ctx["darp_trend"][-6:]:
            ts = d.get("time_sec")
            vd = d.get("vdot")
            time_str = _fmt_sec(ts) if ts else "-"
            lines.append(f"- {d['date']}: 하프 예측 {time_str}, VDOT {vd or '-'}")
    if ctx.get("di_trend"):
        recent_di = ctx["di_trend"][-3:]
        lines.append("DI 추세: " + ", ".join(f"{d['date']}={d['value']}" for d in recent_di))
    if ctx.get("goal"):
        g = ctx["goal"]
        days_left = ""
        if g.get("race_date"):
            try:
                dl = (date.fromisoformat(g["race_date"]) - date.today()).days
                days_left = f" (D-{dl})"
            except ValueError:
                pass
        lines.append(f"\n### 목표 레이스: {g.get('name', '-')} {g.get('distance_km', '')}km{days_left}")

    # 장기 비교
    if ctx.get("past_snapshots"):
        lines.append("\n### 과거 비교")
        for label, snap in ctx["past_snapshots"].items():
            parts = []
            for k in ["UTRS", "CIRS", "DI", "ctl", "vo2max"]:
                v = snap.get(k)
                if v is not None:
                    parts.append(f"{k}={v}")
            if snap.get("weekly_km"):
                parts.append(f"주간={snap['weekly_km']}km")
            if snap.get("avg_pace"):
                parts.append(f"페이스={snap['avg_pace']}")
            lines.append(f"- {label}: {' | '.join(parts) if parts else '데이터 없음'}")

    # 훈련 계획
    if ctx.get("week_plan"):
        lines.append("\n### 이번 주 계획")
        for p in ctx["week_plan"]:
            lines.append(f"- {p.get('date', '-')}: {p.get('workout_type', '-')} "
                        f"{p.get('distance_km', '')}km")
    if ctx.get("wellness_3d"):
        lines.append("\n### 웰니스 3일")
        for d in ctx["wellness_3d"]:
            lines.append(f"- {d['date']}: BB={d.get('bb', '-')} 수면={d.get('sleep', '-')} "
                        f"HRV={d.get('hrv', '-')}")

    # 날짜 지정 활동 조회
    if ctx.get("lookup_activities") is not None:
        ld = ctx.get("lookup_date", "")
        acts = ctx["lookup_activities"]
        if acts:
            lines.append(f"\n### {ld} 활동 ({len(acts)}개)")
            for a in acts:
                dur = _fmt_sec(a.get("duration_sec")) if a.get("duration_sec") else "-"
                lines.append(f"- {a.get('name', '러닝')}: {a.get('distance_km', '-')}km, "
                            f"{a.get('pace', '-')}/km, HR {a.get('avg_hr', '-')}/{a.get('max_hr', '-')}, "
                            f"{dur}")
                if a.get("workout_type"):
                    lines.append(f"  분류: {a['workout_type']}")
                if a.get("metrics"):
                    m_parts = [f"{k}={v}" for k, v in a["metrics"].items()]
                    if len(m_parts) > 8:
                        m_parts = m_parts[:8] + [f"외 {len(m_parts)-8}개"]
                    lines.append(f"  메트릭: {', '.join(m_parts)}")
        else:
            lines.append(f"\n### {ld}: 활동 기록 없음")

        dm = ctx.get("lookup_day_metrics", {})
        if dm:
            dm_parts = [f"{k}={v}" for k, v in list(dm.items())[:10]]
            lines.append(f"일별 메트릭: {', '.join(dm_parts)}")

        lw = ctx.get("lookup_wellness")
        if lw:
            lines.append(f"컨디션: BB={lw.get('bb', '-')} 수면={lw.get('sleep', '-')} "
                        f"HRV={lw.get('hrv', '-')} 스트레스={lw.get('stress', '-')}")

    # 회복 상세
    if ctx.get("wellness_7d"):
        lines.append("\n### 웰니스 7일 추세")
        for d in ctx["wellness_7d"]:
            lines.append(f"- {d['date']}: BB={d.get('bb', '-')} 수면={d.get('sleep', '-')} "
                        f"HRV={d.get('hrv', '-')} 스트레스={d.get('stress', '-')}")
    if ctx.get("hrv_baseline"):
        bl = ctx["hrv_baseline"]
        lines.append(f"HRV 기준선: {bl.get('low', '-')}~{bl.get('high', '-')} ms")
    if ctx.get("cirs_7d"):
        lines.append("CIRS 7일: " + ", ".join(f"{d['date'][-5:]}={d['value']}" for d in ctx["cirs_7d"]))

    # 대화 이력
    if chat_history:
        lines.append("\n### 최근 대화")
        for msg in chat_history[-3:]:
            role = "사용자" if msg.get("role") == "user" else "코치"
            content = msg.get("content", "")[:200]
            lines.append(f"- {role}: {content}")

    return "\n".join(lines)

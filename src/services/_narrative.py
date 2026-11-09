"""내러티브 생성 헬퍼 — today_service.get_today_narrative() 전용.

분리 이유: today_service.py 300줄 캡(coding-rules.md) 초과 방지.
외부에서 직접 import하지 않는다 — today_service → today_narrative 경로로만 사용.
"""
from __future__ import annotations

import calendar
import datetime
import sqlite3


def month_date_range(year: int, month: int) -> tuple[str, str]:
    """(month_start, date_end) — 이번 달이면 오늘, 과거 달이면 말일."""
    month_start = f"{year}-{month:02d}-01"
    today = datetime.date.today()
    if year == today.year and month == today.month:
        return month_start, today.isoformat()
    last_day = calendar.monthrange(year, month)[1]
    return month_start, f"{year}-{month:02d}-{last_day:02d}"


def peak_ctl_in_range(conn: sqlite3.Connection, month_start: str, date: str) -> float | None:
    """지정 기간의 CTL 최댓값. 데이터 없으면 None."""
    row = conn.execute(
        "SELECT MAX(numeric_value) FROM metric_store"
        " WHERE scope_type='daily' AND metric_name='ctl' AND is_primary=1"
        " AND scope_id >= ? AND scope_id <= ?",
        (month_start, date),
    ).fetchone()
    return float(row[0]) if row and row[0] is not None else None


def query_metric(conn: sqlite3.Connection, scope_type: str, scope_id: str, name: str) -> float | None:
    """metric_store에서 단일 메트릭의 numeric_value 조회."""
    row = conn.execute(
        "SELECT numeric_value FROM metric_store"
        " WHERE scope_type=? AND scope_id=? AND metric_name=? AND is_primary=1",
        (scope_type, scope_id, name),
    ).fetchone()
    if row and row[0] is not None:
        return float(row[0])
    return None


def sleep_trend(conn: sqlite3.Connection, date: str) -> tuple[float | None, float | None]:
    """최근 7일 sleep_score 평균과 이전 7일 평균. 데이터 없으면 None."""
    row1 = conn.execute(
        "SELECT AVG(sleep_score) FROM daily_wellness"
        " WHERE date <= ? AND date > DATE(?, '-7 days') AND sleep_score IS NOT NULL",
        (date, date),
    ).fetchone()
    recent = float(row1[0]) if row1 and row1[0] is not None else None

    row2 = conn.execute(
        "SELECT AVG(sleep_score) FROM daily_wellness"
        " WHERE date <= DATE(?, '-7 days') AND date > DATE(?, '-14 days') AND sleep_score IS NOT NULL",
        (date, date),
    ).fetchone()
    prev = float(row2[0]) if row2 and row2[0] is not None else None

    return recent, prev


def build_evidence(
    ctl_now: float | None,
    ctl_start: float | None,
    month_dist_km: float,
    month_count: int,
    sleep_recent: float | None,
    sleep_prev: float | None,
    period_label: str,
) -> list[dict]:
    """get_today_narrative() evidence 조립 — 데이터 있는 항목만."""
    evidence: list[dict] = []
    if ctl_now is not None:
        ctl_label = f"CTL {ctl_now:.1f}"
        if ctl_start is not None:
            diff = ctl_now - ctl_start
            ctl_label += f" (월초 {ctl_start:.1f}, {diff:+.1f})"
        evidence.append({"type": "metric", "metric": "ctl", "value": ctl_now, "label": ctl_label})
    if month_count > 0:
        evidence.append({
            "type": "metric",
            "metric": "monthly_distance",
            "value": month_dist_km,
            "label": f"{period_label} {month_dist_km}km ({month_count}회)",
        })
    if sleep_recent is not None:
        sleep_label = f"수면 점수 최근 7일 {sleep_recent:.0f}"
        if sleep_prev is not None:
            diff = sleep_recent - sleep_prev
            sleep_label += f" (이전 7일 {sleep_prev:.0f}, {diff:+.0f})"
        evidence.append({
            "type": "metric", "metric": "sleep_score", "value": sleep_recent,
            "label": sleep_label,
        })
    return evidence


def build_narrative_prompt(
    date: str,
    ctl_now: float | None,
    ctl_start: float | None,
    month_dist_km: float,
    month_count: int,
    sleep_recent: float | None,
    sleep_prev: float | None,
    month_label: str | None = None,
    weeks: list[dict] | None = None,
    other_line: str = "",
) -> str:
    """AI 내러티브 생성 프롬프트 — 제공된 수치만 나열(환각 방지)."""
    period = month_label or "이번 달"
    lines = [
        f"기준 날짜: {date}",
        f"아래 훈련 데이터를 기반으로 {period} 훈련 흐름을 한국어 2~3문장으로 요약하라.",
        "반드시 아래 제공된 수치만 사용하고, 데이터에 없는 수치는 절대 언급하지 마라.",
        # T-06: 앱 전체 문체(해요체)·용어 통일. 기간은 아래 '기간' 표기를 그대로 쓴다(과거 달에 '이번 달' 금지).
        f"문체는 해요체(~해요, ~였어요)로 쓰고, 기간은 '{period}'로 부른다.",
        "'롱런'이라는 말 대신 '최장 러닝'을 쓰고, 괄호 안에 괄호를 겹쳐 쓰지 마라.",
        "",
    ]
    if ctl_now is not None:
        if ctl_start is not None:
            diff = ctl_now - ctl_start
            lines.append(f"- CTL: 월초 {ctl_start:.1f} → 현재 {ctl_now:.1f} ({diff:+.1f})")
        else:
            lines.append(f"- CTL: {ctl_now:.1f}")
    if month_count > 0:
        lines.append(f"- {period} 누적 러닝 거리: {month_dist_km}km ({month_count}회 훈련)")
    if other_line:
        lines.append(f"- {other_line}")
    if sleep_recent is not None:
        if sleep_prev is not None:
            lines.append(f"- 수면 점수: 최근 7일 평균 {sleep_recent:.0f} (이전 7일 {sleep_prev:.0f})")
        else:
            lines.append(f"- 수면 점수: 최근 7일 평균 {sleep_recent:.0f}")
    if weeks:
        from src.services.week_digest import digest_prompt_lines
        lines.append("주별 요약(근거를 인용할 때는 \"(W2 최장 28km)\" 형식으로 주 번호와 함께 쓴다):")
        lines.extend(digest_prompt_lines(weeks))
    if not any(ln.startswith("- ") for ln in lines):
        lines.append("- (데이터 없음)")
    return "\n".join(lines)


def empty_month_text(conn: sqlite3.Connection, period: str) -> str:
    """그 달 활동이 하나도 없을 때의 중립 문구(T-26·T-21) — 미수집과 미실행을 구분하고 평가하지 않는다."""
    any_row = conn.execute("SELECT 1 FROM v_canonical_activities LIMIT 1").fetchone()
    if any_row is None:
        return "아직 수집된 활동이 없어요. 기기를 연결해 동기화하면 이 달의 흐름을 정리해 드려요."
    return f"{period}에는 기록된 활동이 없어요."


def attach_drill(conn: sqlite3.Connection, evidence: list[dict], scope_date: str) -> list[dict]:
    """각 evidence 항목에 drill 참조를 붙인다.

    metric_store에 해당 날짜의 대표 행이 있는 항목만 드릴 가능(drill dict),
    없으면 None — 프론트는 None인 칩을 비대화형 span으로 렌더링한다.
    """
    from src.utils.db_helpers import get_primary_metric
    for ev in evidence:
        drillable = (
            ev.get("type") == "metric"
            and get_primary_metric(conn, "daily", scope_date, ev["metric"]) is not None
        )
        ev["drill"] = {"scope_type": "daily", "scope_id": scope_date} if drillable else None
    return evidence


def _cache_key(month_start: str, date: str, label: str | None) -> str:
    """r3: 해요체 프롬프트(T-06) + 기간 표기 구분 — 말일에 '이번 달'로 만든 캐시가
    다음 달에 과거 달 조회('2026년 10월')로 재사용되지 않게 한다."""
    return f"{month_start}:{date}:{'cur' if label is None else 'named'}:r3"


def get_narrative_cache(conn: sqlite3.Connection, month_start: str, date: str,
                        label: str | None = None) -> dict | None:
    """캐시된 AI 내러티브 조회. 유효하면 dict, 아니면 None."""
    from src.ai import ai_cache
    return ai_cache.get_cached(conn, "today_narrative", _cache_key(month_start, date, label))


def set_narrative_cache(conn: sqlite3.Connection, month_start: str, date: str, result: dict,
                        label: str | None = None) -> None:
    """AI 내러티브 결과 캐시 저장 (AI 성공 시에만 호출할 것). 실패는 삼킴."""
    from src.ai import ai_cache
    try:
        ai_cache.set_cached(conn, "today_narrative", _cache_key(month_start, date, label), result)
    except Exception:
        pass


def rule_narrative(
    ctl_now: float | None,
    ctl_start: float | None,
    month_dist_km: float,
    month_count: int,
    sleep_recent: float | None,
    sleep_prev: float | None,
    month_label: str | None = None,
) -> str:
    """규칙 기반 한국어 내러티브 템플릿 — AI 실패 시 fallback."""
    period = month_label or "이번 달"
    parts: list[str] = []

    if month_count > 0:
        parts.append(f"{period} {month_dist_km}km를 {month_count}회 달렸어요.")
    else:
        parts.append(f"{period}에는 기록된 러닝이 없어요.")

    if ctl_now is not None and ctl_start is not None:
        diff = ctl_now - ctl_start
        if diff > 2:
            parts.append(f"훈련 부하(CTL)가 {ctl_start:.0f}→{ctl_now:.0f}로 꾸준히 높아지고 있어요.")
        elif diff < -2:
            parts.append(f"훈련 부하(CTL)가 {ctl_start:.0f}→{ctl_now:.0f}로 줄었어요.")
        else:
            parts.append(f"훈련 부하(CTL)가 {ctl_now:.0f}으로 안정적으로 유지되고 있어요.")
    elif ctl_now is not None:
        parts.append(f"현재 훈련 부하(CTL)는 {ctl_now:.0f}이에요.")

    if sleep_recent is not None and sleep_prev is not None:
        diff = sleep_recent - sleep_prev
        if diff >= 5:
            parts.append("최근 수면 질이 좋아지고 있어요.")
        elif diff <= -5:
            parts.append("최근 수면 질이 다소 나빠졌으니 회복에 신경 써 주세요.")

    return " ".join(parts) if parts else "데이터 수집 중이에요."

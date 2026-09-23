"""내러티브 생성 헬퍼 — today_service.get_today_narrative() 전용.

분리 이유: today_service.py 300줄 캡(coding-rules.md) 초과 방지.
외부에서 직접 import하지 않는다 — today_service를 통해서만 사용.
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
) -> str:
    """AI 내러티브 생성 프롬프트 — 제공된 수치만 나열(환각 방지)."""
    period = month_label or "이번 달"
    lines = [
        f"기준 날짜: {date}",
        f"아래 훈련 데이터를 기반으로 {period} 훈련 흐름을 한국어 2~3문장으로 요약하라.",
        "반드시 아래 제공된 수치만 사용하고, 데이터에 없는 수치는 절대 언급하지 마라.",
        "",
    ]
    if ctl_now is not None:
        if ctl_start is not None:
            diff = ctl_now - ctl_start
            lines.append(f"- CTL: 월초 {ctl_start:.1f} → 현재 {ctl_now:.1f} ({diff:+.1f})")
        else:
            lines.append(f"- CTL: {ctl_now:.1f}")
    if month_count > 0:
        lines.append(f"- 이번 달 누적 거리: {month_dist_km}km ({month_count}회 훈련)")
    if sleep_recent is not None:
        if sleep_prev is not None:
            lines.append(f"- 수면 점수: 최근 7일 평균 {sleep_recent:.0f} (이전 7일 {sleep_prev:.0f})")
        else:
            lines.append(f"- 수면 점수: 최근 7일 평균 {sleep_recent:.0f}")
    if not any(ln.startswith("- ") for ln in lines):
        lines.append("- (데이터 없음)")
    return "\n".join(lines)


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
        parts.append(f"{period} {month_dist_km}km를 {month_count}회 훈련했습니다.")
    else:
        parts.append(f"{period} 훈련 기록이 아직 없습니다.")

    if ctl_now is not None and ctl_start is not None:
        diff = ctl_now - ctl_start
        if diff > 2:
            parts.append(f"훈련 부하(CTL)가 {ctl_start:.0f}→{ctl_now:.0f}로 꾸준히 높아지고 있습니다.")
        elif diff < -2:
            parts.append(f"훈련 부하(CTL)가 {ctl_start:.0f}→{ctl_now:.0f}로 줄었습니다.")
        else:
            parts.append(f"훈련 부하(CTL)가 {ctl_now:.0f}으로 안정적으로 유지되고 있습니다.")
    elif ctl_now is not None:
        parts.append(f"현재 훈련 부하(CTL)는 {ctl_now:.0f}입니다.")

    if sleep_recent is not None and sleep_prev is not None:
        diff = sleep_recent - sleep_prev
        if diff >= 5:
            parts.append("최근 수면 질이 개선되고 있습니다.")
        elif diff <= -5:
            parts.append("최근 수면 질이 다소 나빠졌으니 회복에 주의하세요.")

    return " ".join(parts) if parts else "데이터 수집 중입니다."

"""훈련 계획 ICS 빌더 — RFC 5545 준수, 구조화 열만 노출(자유 텍스트·생체값 제외).

구독 피드(/feeds/cal/<token>.ics)와 /training/export.ics 다운로드가 공유한다.
설계: v0.3/data/phase-7-ui-renewal/ux-review-2026-09/DESIGN-ICS-SUBSCRIBE.md §5
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import date, datetime, timedelta

from src.utils.format_ko import workout_ko

MAX_EVENTS = 500
MAX_FUTURE_DAYS = 370
PAST_DAYS = 28
CALNAME = "RunPulse 훈련 계획"


def escape_text(s: str) -> str:
    return (s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")
            .replace("\r\n", "\\n").replace("\n", "\\n").replace("\r", "\\n"))


def fold_line(line: str) -> str:
    """75옥텟 초과 줄을 CRLF+공백으로 접는다 (UTF-8 문자 경계 유지)."""
    out, cur, cur_len, limit = [], "", 0, 75
    for ch in line:
        n = len(ch.encode("utf-8"))
        if cur_len + n > limit:
            out.append(cur)
            cur, cur_len, limit = " " + ch, 1 + n, 75
        else:
            cur += ch
            cur_len += n
    out.append(cur)
    return "\r\n".join(out)


def _pace(sec) -> str:
    s = int(round(sec))
    return f"{s // 60}:{s % 60:02d}"


def _zone(z) -> str | None:
    if z is None or z == "":
        return None
    digits = "".join(c for c in str(z) if c.isdigit())
    return f"Z{digits}" if digits else None


def _interval_text(raw) -> str | None:
    try:
        rx = json.loads(raw) if isinstance(raw, str) else raw
        if rx and rx.get("sets") and rx.get("rep_m"):
            return f"{int(rx['rep_m'])}m × {int(rx['sets'])}"
    except (ValueError, TypeError, AttributeError):
        pass
    return None


def _summary(w: sqlite3.Row) -> str:
    label = workout_ko(w["workout_type"])
    dist = w["distance_km"]
    if w["workout_type"] == "race":
        return f"RunPulse · 대회 {dist:.1f}km" if dist else "RunPulse · 대회"
    return f"RunPulse · {label} {dist:.1f}km" if dist else f"RunPulse · {label}"


def _description(w: sqlite3.Row) -> str:
    parts = []
    rx = _interval_text(w["interval_prescription"])
    if rx:
        parts.append(rx)
    lo, hi = w["target_pace_min"], w["target_pace_max"]
    if lo and hi:
        a, b = sorted((lo, hi))
        parts.append(f"목표 {_pace(a)}–{_pace(b)}/km" if _pace(a) != _pace(b) else f"목표 {_pace(a)}/km")
    elif lo or hi:
        parts.append(f"목표 {_pace(lo or hi)}/km")
    z = _zone(w["target_hr_zone"])
    if z:
        parts.append(z)
    return " · ".join(parts)


def _dtstamp(updated_at, day: str) -> str:
    try:
        dt = datetime.fromisoformat(str(updated_at).replace("Z", "").replace(" ", "T")[:19])
        return dt.strftime("%Y%m%dT%H%M%SZ")
    except (ValueError, TypeError):
        return day.replace("-", "") + "T000000Z"


def default_range(conn: sqlite3.Connection, today: date | None = None) -> tuple[str, str]:
    today = today or date.today()
    frm = today - timedelta(days=PAST_DAYS)
    cap = today + timedelta(days=MAX_FUTURE_DAYS)
    row = conn.execute("SELECT MAX(date) FROM planned_workouts WHERE date>=?", (frm.isoformat(),)).fetchone()
    end = min(date.fromisoformat(row[0]), cap) if row and row[0] else today
    return frm.isoformat(), end.isoformat()


def _overlaid_rows(conn: sqlite3.Connection, frm: str, to: str) -> list[dict]:
    """frm~to 계획 행에 수락된 조정을 겹쳐 적용(이동·휴식 반영). move 가 범위 밖에서 들어오는 경우를 위해 ±7일 넓게 읽는다."""
    from src.training.plan_overlay import apply, live_adjustments
    lo = (date.fromisoformat(frm) - timedelta(days=7)).isoformat()
    hi = (date.fromisoformat(to) + timedelta(days=8)).isoformat()
    prev = conn.row_factory
    conn.row_factory = sqlite3.Row
    try:
        raw = [dict(r) for r in conn.execute(
            "SELECT id, date, workout_type, distance_km, target_pace_min, target_pace_max, "
            "target_hr_zone, interval_prescription, updated_at FROM planned_workouts "
            "WHERE date>=? AND date<? ORDER BY date, id", (lo, hi)).fetchall()]
    finally:
        conn.row_factory = prev
    rows = apply(raw, live_adjustments(conn, lo, hi))
    rows = [w for w in rows if frm <= w["date"] <= to and w["workout_type"] != "rest"]
    rows.sort(key=lambda w: (w["date"], w["id"]))
    return rows[:MAX_EVENTS]


def build_ics(conn: sqlite3.Connection, frm: str, to: str, uid_salt: str = "") -> str:
    """frm~to(포함) 계획을 ICS 문자열로. 결정적(같은 입력 → 같은 바이트)."""
    rows = _overlaid_rows(conn, frm, to)
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//RunPulse//Training Plan//KO",
             "CALSCALE:GREGORIAN", "METHOD:PUBLISH", f"X-WR-CALNAME:{CALNAME}"]
    slots: dict[str, int] = {}
    for w in rows:
        d = w["date"]
        slot = slots[d] = slots.get(d, -1) + 1
        uid = hashlib.sha256(f"{uid_salt}|{d}|{slot}".encode()).hexdigest()[:12]
        nxt = (date.fromisoformat(d) + timedelta(days=1)).strftime("%Y%m%d")
        lines += ["BEGIN:VEVENT", f"UID:{d}-{slot}-{uid}@runpulse",
                  f"DTSTAMP:{_dtstamp((w.get('adjustment') or {}).get('decided_at') or w['updated_at'], d)}",
                  f"DTSTART;VALUE=DATE:{d.replace('-', '')}", f"DTEND;VALUE=DATE:{nxt}",
                  f"SUMMARY:{escape_text(_summary(w))}"]
        desc = _description(w)
        if desc:
            lines.append(f"DESCRIPTION:{escape_text(desc)}")
        lines += ["TRANSP:TRANSPARENT", "END:VEVENT"]
    lines.append("END:VCALENDAR")
    return "\r\n".join(fold_line(x) for x in lines) + "\r\n"

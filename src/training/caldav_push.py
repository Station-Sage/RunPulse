"""CalDAV 캘린더 연동 — 훈련 계획을 외부 캘린더에 등록·갱신·삭제 (ADR-036).

네이버·Apple iCloud·Synology 등 앱 비밀번호 방식 CalDAV 서버용. Google 은 OAuth 전용이라 지원하지 않는다.
이벤트 UID 는 날짜+슬롯 규칙(ICS 피드와 같은 겹침 적용 행)이라 다시 보내면 덮어쓰고, 사라진 일정은 지운다.
전송 기록은 caldav_pushes 테이블. 설정: config.json "caldav": {url, username, password, calendar_name}.
"""
from __future__ import annotations

import logging
import sqlite3
from datetime import date, timedelta

from src.services.calendar_feed_service import _description, _overlaid_rows, _summary, escape_text, fold_line

log = logging.getLogger(__name__)


class CalDavUnavailable(Exception):
    """caldav 패키지가 설치되지 않음."""


def _calendar(cfg: dict):
    """설정으로 대상 캘린더 객체를 연다. 실패 사유는 예외로 전달."""
    try:
        import caldav
    except ImportError as exc:
        raise CalDavUnavailable("캘린더 연동 모듈이 설치되지 않았어요") from exc
    client = caldav.DAVClient(url=cfg["url"], username=cfg.get("username", ""), password=cfg.get("password", ""))
    calendars = client.principal().calendars()
    if not calendars:
        raise LookupError("계정에 캘린더가 없어요")
    name = cfg.get("calendar_name", "")
    return next((c for c in calendars if name and c.name == name), calendars[0])


def _uid(day: str, slot: int) -> str:
    return f"{day}-{slot}@runpulse-caldav"


def _vcal(w: dict, uid: str) -> str:
    d = w["date"]
    nxt = (date.fromisoformat(d) + timedelta(days=1)).strftime("%Y%m%d")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//RunPulse//Training Plan//KO", "BEGIN:VEVENT",
             f"UID:{uid}", f"DTSTAMP:{date.today().strftime('%Y%m%d')}T000000Z",
             f"DTSTART;VALUE=DATE:{d.replace('-', '')}", f"DTEND;VALUE=DATE:{nxt}",
             f"SUMMARY:{escape_text(_summary(w))}"]
    desc = _description(w)
    if desc:
        lines.append(f"DESCRIPTION:{escape_text(desc)}")
    lines += ["TRANSP:TRANSPARENT", "END:VEVENT", "END:VCALENDAR"]
    return "\r\n".join(fold_line(x) for x in lines) + "\r\n"


def _slots(conn: sqlite3.Connection, frm: str, to: str) -> list[tuple[str, int, dict]]:
    out, seen = [], {}
    for w in _overlaid_rows(conn, frm, to):
        slot = seen[w["date"]] = seen.get(w["date"], -1) + 1
        out.append((w["date"], slot, w))
    return out


def _retry(fn):
    """1회 재시도 후 실패하면 예외 전달."""
    try:
        return fn()
    except CalDavUnavailable:
        raise
    except Exception:
        return fn()


def push_range(config: dict, conn: sqlite3.Connection, frm: str, to: str) -> int:
    """frm~to 계획을 캘린더에 등록(같은 UID 는 덮어씀)하고 계획에서 빠진 옛 일정은 지운다. 등록 성공 수 반환."""
    cfg = config.get("caldav", {})
    if not cfg.get("url"):
        return 0
    cal = _calendar(cfg)
    wanted = _slots(conn, frm, to)
    count = 0
    for d, slot, w in wanted:
        try:
            _retry(lambda: cal.save_event(_vcal(w, _uid(d, slot))))
        except Exception as exc:
            log.warning("[caldav] 등록 실패 %s#%s: %s", d, slot, exc)
            continue
        conn.execute("INSERT INTO caldav_pushes(date, slot, uid) VALUES (?, ?, ?) ON CONFLICT(date, slot) "
                     "DO UPDATE SET pushed_at=datetime('now')", (d, slot, _uid(d, slot)))
        count += 1
    keep = {(d, s) for d, s, _ in wanted}
    for d, slot, uid in conn.execute("SELECT date, slot, uid FROM caldav_pushes WHERE date>=? AND date<=?",
                                     (frm, to)).fetchall():
        if (d, slot) in keep:
            continue
        try:
            _retry(lambda: cal.event_by_uid(uid).delete())
        except Exception as exc:
            log.warning("[caldav] 삭제 실패 %s: %s", uid, exc)
            continue
        conn.execute("DELETE FROM caldav_pushes WHERE date=? AND slot=?", (d, slot))
    conn.commit()
    return count


def push_weekly_plan_to_caldav(config: dict, conn: sqlite3.Connection, week_offset: int = 0) -> int:
    """이번 주(+offset) 계획을 등록. 등록 성공 수."""
    start = date.today() - timedelta(days=date.today().weekday()) + timedelta(weeks=week_offset)
    return push_range(config, conn, start.isoformat(), (start + timedelta(days=6)).isoformat())


def sync_after_replan(config: dict, conn: sqlite3.Connection, frm: str, to: str) -> dict | None:
    """재계획 적용 직후 호출. 이미 보낸 일정이 범위에 있을 때만 동기화하며 실패해도 예외를 던지지 않는다."""
    if not config.get("caldav", {}).get("url"):
        return None
    if not conn.execute("SELECT 1 FROM caldav_pushes WHERE date>=? AND date<=? LIMIT 1", (frm, to)).fetchone():
        return None
    try:
        return {"synced": push_range(config, conn, frm, to)}
    except Exception as exc:
        log.warning("[caldav] 재계획 동기화 실패: %s", exc)
        return {"synced": 0, "error": str(exc)[:80]}


def test_connection(config: dict) -> tuple[bool, str]:
    """CalDAV 연결 테스트 (성공 여부, 사유 메시지)."""
    cfg = config.get("caldav", {})
    if not cfg.get("url"):
        return False, "CalDAV URL이 설정되지 않았어요."
    try:
        import caldav
    except ImportError:
        return False, "캘린더 연동 모듈이 설치되지 않았어요."
    try:
        calendars = caldav.DAVClient(url=cfg["url"], username=cfg.get("username", ""),
                                     password=cfg.get("password", "")).principal().calendars()
    except Exception as exc:
        name = type(exc).__name__
        if "Authorization" in name or "401" in str(exc):
            return False, "사용자명 또는 앱 비밀번호가 맞지 않아요."
        return False, f"서버에 연결하지 못했어요. URL을 확인하세요. ({name})"
    if not calendars:
        return False, "연결은 됐지만 계정에 캘린더가 없어요."
    return True, f"연결 성공! 캘린더 {len(calendars)}개: {', '.join(str(c.name) for c in calendars)}"

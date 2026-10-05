"""활동의 원본 서비스 페이지 링크 — 그룹 구성원마다 (source, source_id)로 URL 구성. 외부 호출 없음(ADR-022)."""
from __future__ import annotations

import sqlite3

from src.utils.canonical import group_activity_ids

_TEMPLATES = {
    "garmin": ("https://connect.garmin.com/modern/activity/{sid}", "Garmin Connect에서 열기"),
    "strava": ("https://www.strava.com/activities/{sid}", "Strava에서 열기"),
    "intervals": ("https://intervals.icu/activities/{sid}", "Intervals.icu에서 열기"),
    "runalyze": ("https://runalyze.com/activity/{sid}", "Runalyze에서 열기"),
}


def source_links(conn: sqlite3.Connection, activity_id: int) -> list[dict]:
    ids = group_activity_ids(conn, activity_id)
    rows = conn.execute(
        f"SELECT source, source_id FROM activity_summaries WHERE id IN ({','.join('?' * len(ids))}) ORDER BY id",
        ids).fetchall()
    links, seen = [], set()
    for source, sid in rows:
        tpl = _TEMPLATES.get(source or "")
        sid = str(sid or "").strip()
        if not tpl or not sid or source in seen or not sid.replace("-", "").replace("_", "").isalnum():
            continue
        seen.add(source)
        links.append({"provider": source, "url": tpl[0].format(sid=sid), "label_ko": tpl[1]})
    return links

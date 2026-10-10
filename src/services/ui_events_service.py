"""UI 이벤트 기록·집계 — v2 방문(일 1행)과 v1 복귀 클릭(클릭당 1행), G5 게이트 복귀율 산출."""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from pathlib import Path

REASONS = ("missing_feature", "hard_to_use", "slow_or_error", "just_looking")
NOTE_MAX = 200
MIN_SAMPLE = 10
PASS_RATE = 0.10


def record_visit(conn: sqlite3.Connection, today: str | None = None) -> bool:
    cur = conn.execute(
        "INSERT OR IGNORE INTO ui_events(kind, day) VALUES ('v2_visit', ?)",
        (today or date.today().isoformat(),),
    )
    conn.commit()
    return cur.rowcount > 0


def record_rollback(conn: sqlite3.Connection, reason: str | None = None,
                    note: str | None = None, today: str | None = None) -> None:
    if reason is not None and reason not in REASONS:
        raise ValueError(f"reason must be one of {REASONS}")
    note = " ".join(note.split())[:NOTE_MAX] if isinstance(note, str) else None
    conn.execute(
        "INSERT INTO ui_events(kind, reason, reason_note, day) VALUES ('v1_rollback', ?, ?, ?)",
        (reason, note or None, today or date.today().isoformat()),
    )
    conn.commit()


def _window(days: int, today: str | None) -> tuple[str, str]:
    end = date.fromisoformat(today) if today else date.today()
    return (end - timedelta(days=days - 1)).isoformat(), end.isoformat()


def summarize(conn: sqlite3.Connection, days: int = 14, today: str | None = None) -> dict:
    frm, to = _window(days, today)
    visits = conn.execute(
        "SELECT COUNT(*) FROM ui_events WHERE kind='v2_visit' AND day BETWEEN ? AND ?", (frm, to)
    ).fetchone()[0]
    by_reason: dict[str, int] = {r: 0 for r in REASONS}
    by_reason["skipped"] = 0
    total = 0
    for reason, n in conn.execute(
        "SELECT reason, COUNT(*) FROM ui_events WHERE kind='v1_rollback' "
        "AND day BETWEEN ? AND ? GROUP BY reason", (frm, to)
    ):
        by_reason[reason or "skipped"] += n
        total += n
    return {"window_days": days, "from": frm, "to": to, "v2_visit_days": visits,
            "rollback_count": total, "rollback_by_reason": by_reason, "rolled_back": total > 0}


def summarize_all_users(root: str | Path, days: int = 14, today: str | None = None) -> dict:
    frm, to = _window(days, today)
    active = rolled = 0
    by_reason: dict[str, int] = {r: 0 for r in REASONS}
    by_reason["skipped"] = 0
    notes: list[dict] = []
    orphan = 0
    for db in sorted(Path(root).glob("*/running.db")):
        try:
            conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        except sqlite3.Error:
            continue
        try:
            if not conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='ui_events'"
            ).fetchone():
                continue
            s = summarize(conn, days, to)
            has_visit = s["v2_visit_days"] > 0
            active += has_visit
            if s["rolled_back"]:
                rolled += 1
                orphan += not has_visit
                for k, v in s["rollback_by_reason"].items():
                    by_reason[k] += v
            for n, d in conn.execute(
                "SELECT reason_note, day FROM ui_events WHERE kind='v1_rollback' "
                "AND reason_note IS NOT NULL AND day BETWEEN ? AND ?", (frm, to)
            ):
                notes.append({"day": d, "note": n})
        finally:
            conn.close()
    notes.sort(key=lambda x: x["day"], reverse=True)
    rate = (rolled / active) if active else None
    verdict = "미판정" if rate is None else ("통과" if rate < PASS_RATE else "미달")
    return {"window_days": days, "from": frm, "to": to, "active_users": active,
            "rolled_back_users": rolled, "rate": rate, "verdict": verdict,
            "small_sample": active < MIN_SAMPLE, "rollback_by_reason": by_reason,
            "recent_notes": notes[:20], "orphan_rollback_users": orphan}

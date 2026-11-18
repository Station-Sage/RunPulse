"""능동 인사이트 사건 저장·갱신·조회 (V2-REPAIR D) — 규칙은 insight_rules, 여기는 upsert·해소·억제만.

refresh(conn, day): 규칙을 평가해 사건을 upsert 한다. 같은 dedupe_key 는 열린(open/seen) 사건 1개만,
조건이 풀리면 resolved, 사용자가 dismiss 한 키는 7일간 재생성하지 않는다. 화면은 저장된 사건만 읽는다.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from datetime import date as _date, timedelta

from src.services import insight_rules

log = logging.getLogger(__name__)

DISMISS_DAYS = 7
OPEN_STATES = ("open", "seen")
_SEV_RANK = {"act": 0, "watch": 1, "info": 2}
SIGNAL_KINDS = ("load_spike", "recovery_low", "pain_flag")
_COLS = "id, kind, severity, as_of, dedupe_key, signals_json, text, action_json, state, created_at, resolved_at, text_ai, text_src"


def _row(r: sqlite3.Row | tuple) -> dict:
    d = dict(zip(_COLS.replace(" ", "").split(","), r))
    d["signals"] = json.loads(d.pop("signals_json") or "[]")
    d["action"] = json.loads(d.pop("action_json") or "null")
    ai, src = d.pop("text_ai"), d.pop("text_src")
    d["polished"] = bool(ai and src == d["text"])
    if d["polished"]:
        d["text"] = ai
    return d


def _suppressed(conn, key: str, day: str) -> bool:
    cutoff = (_date.fromisoformat(day) - timedelta(days=DISMISS_DAYS)).isoformat()
    return conn.execute("SELECT 1 FROM insight_events WHERE dedupe_key=? AND state='dismissed' "
                        "AND date(dismissed_at) >= ? LIMIT 1", (key, cutoff)).fetchone() is not None


def _default_last_success() -> dict[str, str | None]:
    from src.utils.config import enabled_sources, load_config
    from src.utils.sync_ledger_query import last_success_at
    out = {}
    for src in enabled_sources(load_config()):
        t = last_success_at(src)
        out[src] = t.date().isoformat() if t else None
    return out


def _apply(conn, day: str, cands: list[dict], kinds: set[str]) -> None:
    keys = {c["dedupe_key"] for c in cands}
    for c in cands:
        key = c["dedupe_key"]
        if _suppressed(conn, key, day):
            continue
        sig, act = json.dumps(c["signals"], ensure_ascii=False), json.dumps(c["action"], ensure_ascii=False)
        cur = conn.execute("UPDATE insight_events SET severity=?, as_of=?, signals_json=?, text=?, action_json=? "
                           "WHERE dedupe_key=? AND state IN ('open','seen')",
                           (c["severity"], day, sig, c["text"], act, key))
        if cur.rowcount == 0:
            conn.execute("INSERT INTO insight_events(kind, severity, as_of, dedupe_key, signals_json, text, action_json)"
                         " VALUES (?,?,?,?,?,?,?)", (c["kind"], c["severity"], day, key, sig, c["text"], act))
    for oid, key, kind in conn.execute("SELECT id, dedupe_key, kind FROM insight_events WHERE state IN ('open','seen')").fetchall():
        if kind in kinds and key not in keys:
            conn.execute("UPDATE insight_events SET state='resolved', resolved_at=datetime('now') WHERE id=?", (oid,))


def refresh(conn: sqlite3.Connection, day: str, *, signals: list[dict] | None = None,
            last_success: dict[str, str | None] | None = None) -> None:
    """day 기준 사건 갱신. 규칙군 평가가 실패하면 그 종류는 건드리지 않는다(오탐 해소 방지)."""
    try:
        if signals is None:
            from src.services.adjustment_signals import collect
            signals = collect(conn, day)
        _apply(conn, day, insight_rules.evaluate_signal_rules(signals), set(SIGNAL_KINDS))
    except Exception:
        log.warning("insight signal rules failed", exc_info=True)
    try:
        ls = last_success if last_success is not None else _default_last_success()
        _apply(conn, day, insight_rules.evaluate_data_gap(day, ls), {"data_gap"})
    except Exception:
        log.warning("insight data_gap rule failed", exc_info=True)
    conn.commit()


def list_events(conn: sqlite3.Connection, state: str = "open", limit: int = 20) -> list[dict]:
    """state: 'open'(open+seen, 심각도→최신순) | 'all'. 저장된 사건만 읽는다."""
    where = "state IN ('open','seen')" if state == "open" else "1=1"
    rows = conn.execute(f"SELECT {_COLS} FROM insight_events WHERE {where} ORDER BY id DESC").fetchall()
    ev = sorted((_row(r) for r in rows), key=lambda e: (_SEV_RANK.get(e["severity"], 9), -e["id"]))
    return ev[:limit]


def _set_state(conn, event_id: int, state: str, extra: str = "") -> bool:
    cur = conn.execute(f"UPDATE insight_events SET state=?{extra} WHERE id=? AND state IN ('open','seen')", (state, event_id))
    conn.commit()
    return cur.rowcount > 0


def mark_seen(conn, event_id: int) -> bool:
    return _set_state(conn, event_id, "seen") if conn.execute(
        "SELECT 1 FROM insight_events WHERE id=? AND state='open'", (event_id,)).fetchone() else False


def dismiss(conn, event_id: int) -> bool:
    return _set_state(conn, event_id, "dismissed", ", dismissed_at=datetime('now')")

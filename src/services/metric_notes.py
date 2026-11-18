"""지표 안내 문구 사전 생성 (Claude 큐) — 규칙 힌트를 haiku 로 미리 다듬어 ai_outputs(kind='metric_note')에 캐시한다.

화면은 캐시가 있고 규칙 문구가 안 바뀌었으면(src_hash 일치) 다듬은 문구를, 아니면 규칙 문구를 그대로 쓴다.
요청 스레드에서는 큐를 부르지 않고(조회만), 생성은 백그라운드 워밍업에서 한다.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import sqlite3
import threading
from pathlib import Path

from src.services.insight_polish import parse_batch, validate

log = logging.getLogger(__name__)
KIND = "metric_note"
_TEMPLATE = Path(__file__).resolve().parents[1] / "ai" / "prompt_templates" / "metric_note.txt"


def _hash(rule: str) -> str:
    return hashlib.sha1(rule.encode("utf-8")).hexdigest()[:16]


def cached_note(conn: sqlite3.Connection, metric: str, band: str, rule: str) -> str | None:
    """캐시된 다듬은 문구. 규칙 문구가 바뀌었거나 없으면 None."""
    try:
        r = conn.execute("SELECT src_hash, body_json FROM ai_outputs WHERE kind=? AND scope_key=?",
                         (KIND, f"{metric}:{band}")).fetchone()
    except sqlite3.Error:
        return None
    if not r or r[0] != _hash(rule):
        return None
    try:
        return json.loads(r[1]).get("text") or None
    except (ValueError, AttributeError):
        return None


def _pending(conn: sqlite3.Connection) -> list[dict]:
    from src.utils.metric_labels import METRIC_LABELS
    items = []
    for name, lab in sorted(METRIC_LABELS.items()):
        for band, rule in (lab.action_hint or {}).items():
            if band.startswith("level_") or cached_note(conn, name, band, rule):
                continue
            items.append({"id": f"{name}:{band}", "metric": name, "band": band, "text": rule})
    return items


def warm(conn: sqlite3.Connection, config: dict | None, chunk: int = 30) -> int:
    """캐시가 없거나 낡은 문구를 큐로 다듬어 저장하고 성공 건수를 반환. 큐 불가·실패는 0."""
    from src.ai import provider_claude_queue as pcq
    if not pcq.available(conn, config):
        return 0
    items, done = _pending(conn), 0
    for i in range(0, len(items), chunk):
        part = items[i:i + chunk]
        prompt = _TEMPLATE.read_text(encoding="utf-8").replace("{{ITEMS}}", json.dumps(part, ensure_ascii=False))
        out = pcq.try_complete(conn, config, kind="insight_polish", prompt=prompt)
        if not out:
            break
        src = {p["id"]: p["text"] for p in part}
        for it in parse_batch(out):
            rule = src.get(it.get("id"))
            text = validate(rule, it.get("text")) if rule else None
            if text and not re.search(r"\d", text):
                conn.execute("INSERT OR REPLACE INTO ai_outputs(kind, scope_key, src_hash, body_json, created_at) "
                             "VALUES (?,?,?,?,datetime('now'))",
                             (KIND, it["id"], _hash(rule), json.dumps({"text": text}, ensure_ascii=False)))
                done += 1
        conn.commit()
    return done


def warm_in_background(db_path: str, config: dict | None) -> None:
    def _run() -> None:
        try:
            with sqlite3.connect(db_path, timeout=30) as c:
                warm(c, config)
        except Exception:  # noqa: BLE001
            log.warning("metric note warm failed", exc_info=True)
    threading.Thread(target=_run, daemon=True, name="metric-note-warm").start()

"""사용자 UI 설정 key-value 저장소(user_settings, ADR-023) — 화이트리스트 키만 허용."""
from __future__ import annotations

import json
import sqlite3

ALLOWED: dict[str, tuple[str, ...]] = {"ui_default": ("v1", "v2")}
FALLBACK_UI = "v1"


def get_setting(conn: sqlite3.Connection, key: str, default=None):
    row = conn.execute("SELECT value_json FROM user_settings WHERE key=?", (key,)).fetchone()
    if row is None:
        return default
    try:
        return json.loads(row[0])
    except ValueError:
        return default


def set_setting(conn: sqlite3.Connection, key: str, value) -> None:
    if key not in ALLOWED:
        raise ValueError(f"허용되지 않은 설정 키: {key}")
    if value not in ALLOWED[key]:
        raise ValueError(f"{key}는 {', '.join(ALLOWED[key])} 중 하나여야 해요")
    conn.execute(
        "INSERT INTO user_settings(key, value_json, updated_at) VALUES (?, ?, datetime('now')) "
        "ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json, updated_at=excluded.updated_at",
        (key, json.dumps(value)),
    )
    conn.commit()


def global_ui_default(config: dict) -> str:
    value = (config or {}).get("ui_default_global")
    return value if value in ALLOWED["ui_default"] else FALLBACK_UI


def resolve_ui_default(conn: sqlite3.Connection, config: dict) -> str:
    """사용자 값 → config["ui_default_global"] → "v1"."""
    value = get_setting(conn, "ui_default")
    return value if value in ALLOWED["ui_default"] else global_ui_default(config)

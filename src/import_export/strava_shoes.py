"""Strava export shoes.csv → gear(source='strava_export') 적재 + 활동 CSV 신발 이름 링크 (V2-SHOES T3).

v1 `shoes` 테이블은 v0.3 DDL 에 없어 조용히 실패하던 경로를 소스 미러 `gear` 로 옮겼다.
`source_gear_id` 는 정규화 이름(소문자·공백 제거) — activities.csv `Activity Gear` 값과 같은 규칙으로 맞춘다.
"""
from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

from src.import_export.strava_row import _clean

EXPORT_SOURCE = "strava_export"


def gear_key(name: str | None) -> str | None:
    """신발 표시 이름 → gear.source_gear_id(정규화 이름). 빈 값은 None."""
    key = "".join((name or "").lower().split())
    return key or None


def _display_name(name: str | None, brand: str | None, model: str | None) -> str | None:
    return name or " ".join(p for p in (brand, model) if p) or None


def import_strava_shoes(
    conn: sqlite3.Connection,
    shoes_csv: Path,
) -> dict[str, int]:
    """shoes.csv → gear 적재(재임포트 멱등 — 같은 이름은 갱신만, gear.shoe_id 연결은 유지).

    Returns:
        {"inserted": n, "skipped": n}
    """
    inserted = skipped = 0

    with open(shoes_csv, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    for raw in rows:
        brand = _clean(raw.get("Shoe Brand"))
        model = _clean(raw.get("Shoe Model"))
        name = _display_name(_clean(raw.get("Shoe Name")), brand, model)
        key = gear_key(name)
        if not key:
            skipped += 1
            continue
        try:
            exists = conn.execute("SELECT 1 FROM gear WHERE source=? AND source_gear_id=?",
                                  (EXPORT_SOURCE, key)).fetchone()
            conn.execute(
                """INSERT INTO gear (source, source_gear_id, name, brand, model, gear_type)
                   VALUES (?, ?, ?, ?, ?, 'shoes')
                   ON CONFLICT(source, source_gear_id) DO UPDATE SET
                       name = excluded.name, brand = excluded.brand, model = excluded.model,
                       updated_at = datetime('now')""",
                (EXPORT_SOURCE, key, name, brand, model),
            )
            if exists:
                skipped += 1
            else:
                inserted += 1
        except sqlite3.Error as e:
            print(f"[strava_csv] shoes 삽입 오류: {e}")
            skipped += 1

    conn.commit()
    return {"inserted": inserted, "skipped": skipped}


def link_activity_gear(conn: sqlite3.Connection, activity_id: int | None, gear_name: str | None) -> bool:
    """activities.csv `Activity Gear` → activity_summaries.gear_id(비어 있을 때만 — API gear id 우선)."""
    key = gear_key(gear_name)
    if not activity_id or not key:
        return False
    cur = conn.execute("UPDATE activity_summaries SET gear_id=? WHERE id=? AND gear_id IS NULL", (key, activity_id))
    return cur.rowcount > 0

"""Strava shoes.csv → shoes 테이블 적재 — strava_csv 에서 분리 (300줄 규칙)."""
from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

from src.import_export.strava_row import _clean


def import_strava_shoes(
    conn: sqlite3.Connection,
    shoes_csv: Path,
) -> dict[str, int]:
    """shoes.csv → shoes 테이블 적재.

    Returns:
        {"inserted": n, "skipped": n}
    """
    inserted = skipped = 0

    with open(shoes_csv, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    for raw in rows:
        brand = _clean(raw.get("Shoe Brand"))
        model = _clean(raw.get("Shoe Model"))
        name = _clean(raw.get("Shoe Name"))
        sport = _clean(raw.get("Shoe Default Sport Types"))

        if not brand and not model:
            skipped += 1
            continue

        try:
            cursor = conn.execute(
                """INSERT OR IGNORE INTO shoes
                   (source, brand, model, name, default_sport_types)
                   VALUES ('strava', ?, ?, ?, ?)""",
                (brand, model, name, sport),
            )
            if cursor.rowcount == 0:
                skipped += 1
            else:
                inserted += 1
        except sqlite3.Error as e:
            print(f"[strava_csv] shoes 삽입 오류: {e}")
            skipped += 1

    conn.commit()
    return {"inserted": inserted, "skipped": skipped}



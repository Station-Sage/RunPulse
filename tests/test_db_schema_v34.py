"""스키마 v34 caldav_pushes: 멱등, (date, slot) 유일."""
import sqlite3

import pytest

from src.db_schema_v34 import ensure_v34
from src.db_setup import APP_TABLES, SCHEMA_VERSION


def test_ensure_idempotent_and_unique():
    c = sqlite3.connect(":memory:")
    ensure_v34(c)
    ensure_v34(c)
    c.execute("INSERT INTO caldav_pushes(date, slot, uid) VALUES ('2026-01-01', 0, 'a')")
    with pytest.raises(sqlite3.IntegrityError):
        c.execute("INSERT INTO caldav_pushes(date, slot, uid) VALUES ('2026-01-01', 0, 'b')")
    assert SCHEMA_VERSION >= 34 and "caldav_pushes" in APP_TABLES

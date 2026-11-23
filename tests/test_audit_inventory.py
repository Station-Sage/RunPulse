"""scripts/audit/inventory.py — 화면 추출·셀 생성·원장·diff."""
import json

import pytest

from scripts.audit import inventory as inv


def _routes(tmp_path):
    for rel in ("today", "library/[id]", "(app)/coach", "x"):
        d = tmp_path / rel
        d.mkdir(parents=True)
        if rel != "x":
            (d / "+page.svelte").write_text("")
    return tmp_path


def test_frontend_screens_handles_dynamic_and_groups(tmp_path):
    assert inv.frontend_screens(_routes(tmp_path)) == ["/coach", "/library/[id]", "/today"]


def test_real_routes_nonempty():
    assert "/today" in inv.frontend_screens()


def test_cells_and_coverage(tmp_path):
    i = inv.build(["/a", "/b"], [])
    cells = inv.cell_ids(i)
    assert len(cells) == 2 * len(inv.STATES) * len(inv.VIEWPORTS)
    ledger_path = tmp_path / "l.json"
    inv.record(cells[0], "확인", path=ledger_path)
    inv.record(cells[1], "이슈", "깨짐", path=ledger_path)
    inv.record("/gone|empty|390", "확인", path=ledger_path)
    c = inv.coverage(i, inv.load_ledger(ledger_path))
    assert (c["checked"], c["issues"], c["stale"]) == (2, [cells[1]], ["/gone|empty|390"])
    assert len(c["unchecked"]) == len(cells) - 2


def test_record_rejects_bad_status(tmp_path):
    with pytest.raises(ValueError):
        inv.record("a|b|c", "ok", path=tmp_path / "l.json")


def test_diff_detects_added_removed():
    old = {"screens": ["/a", "/b"], "apis": [{"rule": "/api/x", "methods": ["GET"]}]}
    new = {"screens": ["/a", "/c"], "apis": [{"rule": "/api/x", "methods": ["GET", "POST"]}]}
    d = inv.diff(old, new)
    assert d["screens"] == {"added": ["/c"], "removed": ["/b"]}
    assert d["apis"]["added"] == ["/api/x GET,POST"] and d["apis"]["removed"] == ["/api/x GET"]


def test_committed_inventory_matches_live():
    committed = json.loads(inv.INVENTORY_PATH.read_text(encoding="utf-8"))
    d = inv.diff(committed, inv.build())
    assert not any(v["added"] or v["removed"] for v in d.values()), d

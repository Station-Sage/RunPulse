"""scripts/synth_smoke/export_demo_milestones — /demo 마일스톤 전체 이력 스냅샷(ADR-057)."""
from __future__ import annotations

import json
from datetime import date

from scripts.synth_smoke import export_demo_milestones as X


def test_shift_dates_moves_items_and_cursor():
    h = {"items": [{"id": 3, "date": "2026-11-19"}, {"id": 1, "date": "2026-11-01"}],
         "next_before": "2026-11-01:1", "type_counts": []}
    out = X.shift_dates(h, -40)
    assert [m["date"] for m in out["items"]] == ["2026-10-10", "2026-09-22"]
    assert out["next_before"] == "2026-09-22:1"
    assert X.shift_dates({**h, "next_before": None}, 1)["next_before"] is None


def test_build_history_anchors_to_snapshot_day_and_hides_internal():
    h = X.build_history(date(2026, 10, 10))
    assert h["items"][0]["date"] == "2026-10-10"          # 목표 설정(시드 당일) = 기준일
    assert len(h["items"]) >= 10
    types = {c["type"] for c in h["type_counts"]}
    assert {"pb", "race_finish", "longest_run", "illness_start", "recovery"} <= types
    assert "metric_recompute" not in types
    dates = [(m["date"], m["id"]) for m in h["items"]]
    assert dates == sorted(dates, reverse=True)


def test_main_writes_key_preserving_other_keys(tmp_path):
    p = tmp_path / "snapshot.json"
    p.write_text(json.dumps({"/today": {"data": {"as_of": {"date": "2026-10-10"}}}, "/x": {"data": 1}}), encoding="utf-8")
    assert X.main(p) == 0
    snap = json.loads(p.read_text(encoding="utf-8"))
    assert snap["/x"] == {"data": 1}
    assert snap[X.KEY]["data"]["items"][0]["date"] == "2026-10-10"

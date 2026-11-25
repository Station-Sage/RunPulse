"""A2 — 구조화 결정함(pending_decisions.json) build/append/choose."""
from scripts.audit import decisions

F = {"kind": "tap"}
D = {"why": "교차 검토 disagree", "design": {"summary": "s", "recommendation": "A",
     "options": [{"name": "x", "pros": "p", "cons": "c"}, {"name": "y"}]}}


def test_build_fields():
    r = decisions.build("AUD-1", F, D)
    assert r["status"] == "open" and [o["key"] for o in r["options"]] == ["A", "B"] and r["revert"]


def test_append_dedup_and_load(tmp_path):
    p = tmp_path / "d.json"
    r = decisions.build("AUD-1", F, D)
    decisions.append([r], p)
    decisions.append([r], p)
    assert len(decisions.load(p)) == 1
    assert decisions.load(tmp_path / "none.json") == []


def test_choose(tmp_path):
    p = tmp_path / "d.json"
    decisions.append([decisions.build("AUD-1", F, D)], p)
    assert decisions.choose("AUD-1", "A", p)["status"] == "chosen"
    assert decisions.choose("AUD-1", "redo", p)["status"] == "redo"
    assert decisions.choose("nope", "A", p) is None


def test_build_fallback_fills_summary_and_default_options():
    f = {"kind": "tap", "impact": "작은 버튼", "fix": "패딩", "perspective": "ui", "cells": ["a|b|390"]}
    r = decisions.build("AUD-2", f, {"tier": "user", "why": "등급 분류 미사용", "design": {}})
    assert r["summary"] == "tap: 작은 버튼"
    assert [o["key"] for o in r["options"]] == ["A", "B"] and r["options"][1]["name"] == "보류·무시"
    assert r["finding"]["perspective"] == "ui" and r["finding"]["cells"] == ["a|b|390"]


def test_tests_do_not_touch_live_decisions_store():
    from pathlib import Path
    assert decisions.DECISIONS_PATH != Path(".claude/autopilot/pending_decisions.json")

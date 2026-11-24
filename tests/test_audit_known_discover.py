"""audit.known(알려진 이슈 원장·재검증) 와 audit.discover(도구 사용 발견 감사·라운드 상한) 단위 테스트."""
import json

from scripts.audit import discover, known
from scripts.autopilot import settings


def _f(kind="tap-target", cells=("a", "b")):
    return {"kind": kind, "verdict": "real", "impact": "x", "cells": list(cells), "perspective": "ui"}


def test_key_stable_and_distinct():
    assert known.key(_f()) == known.key(_f(cells=("b", "a")))
    assert known.key(_f()) != known.key(_f(kind="no-h1"))


def test_filter_new_skips_open_only(tmp_path):
    p = tmp_path / "k.json"
    data = known.record([_f()], 1, p)
    assert known.filter_new([_f()], data) == []
    data[known.key(_f())]["status"] = "resolved"
    assert known.filter_new([_f()], data) == [_f()]


def test_record_marks_reopened(tmp_path):
    p = tmp_path / "k.json"
    known.record([_f()], 1, p)
    known.reverify({}, p)
    d = known.record([_f()], 3, p)
    rec = d[known.key(_f())]
    assert rec["reopened"] and rec["first_round"] == 1 and rec["status"] == "open"


def test_reverify_resolves_and_keeps(tmp_path):
    p = tmp_path / "k.json"
    known.record([_f(), _f(kind="no-h1")], 1, p)
    out = known.reverify({"tap-target": [{}]}, p)
    assert len(out["still_open"]) == 1 and len(out["resolved"]) == 1
    assert "no-h1" not in known.render(known.load(p))


def test_current_round_reads_state(tmp_path, monkeypatch):
    monkeypatch.setattr(known, "KNOWN_PATH", tmp_path / "k.json")
    assert known.current_round() == 1
    (tmp_path / "cycle_state.json").write_text(json.dumps({"round": 7}))
    assert known.current_round() == 7


def test_tunable_override(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "STATE_DIR", tmp_path)
    assert settings.tunable("AUDIT_TOOL_CALLS_PER_ROUND") == 8
    (tmp_path / "tunables.json").write_text(json.dumps({"AUDIT_TOOL_CALLS_PER_ROUND": 2}))
    assert settings.tunable("AUDIT_TOOL_CALLS_PER_ROUND") == 2


def test_discover_respects_cap_and_round_reset(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "STATE_DIR", tmp_path)
    (tmp_path / "tunables.json").write_text(json.dumps({"AUDIT_TOOL_CALLS_PER_ROUND": 2}))
    calls = []
    monkeypatch.setattr(discover.agents, "ask", lambda prompt, model, tools="": calls.append(tools) or
                        json.dumps([{"kind": "k%d" % len(calls), "verdict": "real", "cells": ["f:1"]}]))
    bp, kp = tmp_path / "b.json", tmp_path / "k.json"
    out = discover.run(1, path=bp, known_path=kp)
    assert len(calls) == 2 and calls[0] == discover.TOOLS and len(out) == 2
    assert discover.remaining(1, bp) == 0 and discover.remaining(2, bp) == 2
    assert discover.run(1, path=bp, known_path=kp) == [] and len(calls) == 2


def test_discover_drops_already_known(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "STATE_DIR", tmp_path)
    kp = tmp_path / "k.json"
    known.record([{"kind": "dup", "cells": ["f:1"], "perspective": "x"}], 1, kp)
    monkeypatch.setattr(discover.agents, "ask", lambda *a, **k: json.dumps([{"kind": "dup", "verdict": "real", "cells": ["f:1"]}]))
    assert discover.run(1, path=tmp_path / "b.json", known_path=kp) == []

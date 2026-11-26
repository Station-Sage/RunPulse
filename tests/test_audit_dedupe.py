"""등록 전 중복 필터(dedupe) — kind·위치 근접 판정과 propose 연동."""
from types import SimpleNamespace

from scripts.audit import decisions, dedupe, propose

D = {"why": "w", "design": {"summary": "s", "options": [{"name": "x"}, {"name": "y"}]}}


def _rec(iid, kind, cells, status="open"):
    r = decisions.build(iid, {"kind": kind, "cells": cells}, D)
    r["status"] = status
    return r


def test_same_kind_open_is_duplicate():
    assert dedupe.duplicate_of({"kind": "a", "cells": ["x.py:1"]}, [_rec("AUD-1", "a", ["y.py:9"])]) == "AUD-1"


def test_applied_kind_only_not_duplicate_but_near_cell_is():
    recs = [_rec("AUD-1", "a", ["x.py:10"], "applied")]
    assert dedupe.duplicate_of({"kind": "a", "cells": ["z.py:3"]}, recs) is None
    assert dedupe.duplicate_of({"kind": "b", "cells": ["x.py:14"]}, recs) == "AUD-1"
    assert dedupe.duplicate_of({"kind": "b", "cells": ["x.py:30"]}, recs) is None


def test_runtime_cell_match_and_queue_item():
    recs = [_rec("AUD-1", "a", ["/plan|empty|390"])]
    assert dedupe.duplicate_of({"kind": "b", "cells": ["/plan|empty|390"]}, recs) == "AUD-1"
    it = SimpleNamespace(stage="queued", resolution="", item_id="AUD-9", text="kind-q: 설명")
    assert dedupe.duplicate_of({"kind": "kind-q", "cells": []}, [], [it]) == "AUD-9"
    it.resolution = "dropped"
    assert dedupe.duplicate_of({"kind": "kind-q", "cells": []}, [], [it]) is None


def test_propose_skips_duplicate(tmp_path, monkeypatch):
    decisions.append([_rec("AUD-1", "dup-kind", ["a.py:1"], "chosen")])
    monkeypatch.setattr(propose, "PENDING_PATH", tmp_path / "pending.md")
    b = tmp_path / "BACKLOG.md"
    b.write_text("# B\n", encoding="utf-8")
    out = propose.propose([{"kind": "dup-kind", "verdict": "real", "perspective": "p", "impact": "i", "fix": "f", "cells": ["q.py:2"]}], b)
    assert out == []

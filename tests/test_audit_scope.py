"""테스트 범위 축소(scope) — 변경 파일→스윕 화면 매핑, 루프 test 단계 분기, 라운드 종료 전체 스윕."""
import json

from scripts.audit import loop, scope
from scripts.autopilot import notify, queue

ALL = ["/", "/activities", "/activities/[id]", "/plan", "/plan/edit"]
R = "frontend/src/routes/"


def test_page_maps_to_its_screen():
    assert scope.screens_for([R + "(app)/plan/+page.svelte"], ALL) == ["/plan"]


def test_layout_maps_to_subtree():
    assert scope.screens_for([R + "plan/+layout.svelte"], ALL) == ["/plan", "/plan/edit"]
    assert scope.screens_for([R + "+layout.svelte"], ALL) == ALL


def test_shared_frontend_code_means_all():
    assert scope.screens_for([R + "plan/+page.svelte", "frontend/src/lib/Card.svelte"], ALL) is None


def test_backend_only_is_empty():
    assert scope.screens_for(["src/foo.py", "tests/test_x.py", "frontend/README.md"], ALL) == []


def test_unit_screens_falls_back_to_all_on_git_error(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("git")
    monkeypatch.setattr(scope, "changed_files", boom)
    assert scope.unit_screens() is None


def _p(tmp_path):
    p = tmp_path / "B.md"
    meta = {"stage": "queued", "mode": "auto", "attempts": 0, "deps": [], "kind": "code"}
    p.write_text(f"- **[U1]** 단위\n  <!-- autopilot: {json.dumps(meta)} -->\n", encoding="utf-8")
    return p


def _st():
    return {"phase": "test", "unit": "U1", "round": 1, "units_done": 0, "fails": 0, "fix": {}}


def test_test_phase_scope_branches(tmp_path, monkeypatch):
    monkeypatch.setattr(notify, "send", lambda *a, **k: True)
    calls = []

    def sw(screens=None):
        calls.append(screens)
        return 6, None

    for sc, want in ((None, [None]), ([], []), (["/plan"], [["/plan"]])):
        calls.clear()
        p = _p(tmp_path)
        st = _st()
        loop.step(st, path=p, act={"sweep": sw, "scope": lambda sc=sc: sc, "deploy": lambda n: {"ran": False}})
        assert calls == want
        assert queue.parse(p)[0].stage == "done"


def test_end_round_runs_full_sweep_and_holds_deploy_on_failure(monkeypatch):
    monkeypatch.setattr(notify, "send", lambda *a, **k: True)
    shipped = []
    st = {"round": 1, "units_done": 2, "phase": "develop", "unit": None, "fails": 0, "fix": {}}
    loop._end_round(st, lambda n: shipped.append(n) or {"ran": True, "outcome": "done"}, "x", None, full_sweep=lambda: (282, None))
    assert shipped == [2]
    st = {"round": 1, "units_done": 2, "phase": "develop", "unit": None, "fails": 0, "fix": {}}
    loop._end_round(st, lambda n: shipped.append(n) or {"ran": True, "outcome": "done"}, "x", None, full_sweep=lambda: (10, "overflow"))
    assert shipped == [2]

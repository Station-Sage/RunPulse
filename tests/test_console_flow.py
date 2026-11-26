"""진행 흐름(flow.build) 계산 + 루프 이벤트 기록."""
import time

from scripts.audit import loop, progress
from scripts.console import flow

Q = ('- **[A-1]** t\n  <!-- autopilot: {"stage":"queued","mode":"auto","attempts":0,"deps":[]} -->\n'
     '- **[A-2]** u\n  <!-- autopilot: {"stage":"queued","mode":"auto","attempts":0,"deps":[]} -->\n')


def _ev(kind, ts, **kw):
    return {"kind": kind, "ts": ts, **kw}


def test_build_from_events(tmp_path):
    q = tmp_path / "B.md"
    q.write_text(Q)
    evs = [_ev("phase", 100, round=3, phase="audit"), _ev("sub", 110, step="sweep", state="start"),
           _ev("sub", 150, step="sweep", state="end"), _ev("sub", 160, step="audit", state="start"),
           _ev("phase", 300, round=3, phase="design"), _ev("design", 310, new=3, auto=2, user=1),
           _ev("phase", 320, round=3, phase="develop"), _ev("unit_start", 330, unit="A-1")]
    p = flow.build({"round": 3, "phase": "develop", "units_done": 1, "unit": None}, 400, q, evs)
    assert p["stage"] == 3 and p["round_started"] == 100 and p["phase_started"] == 320
    assert p["design"] == {"new": 3, "auto": 2, "user": 1}
    assert p["units"]["done"] == 1 and p["units"]["total"] == 3 and p["units"]["started"] == 330
    a = flow.build({"round": 3, "phase": "audit"}, 200, q, evs[:4])
    assert a["stage"] == 1 and a["subs"]["sweep"]["state"] == "done" and a["subs"]["audit"]["state"] == "active"


def test_design_batches_are_summed(tmp_path):
    q = tmp_path / "B.md"
    q.write_text(Q)
    evs = [_ev("phase", 100, round=3, phase="design"), _ev("design", 110, new=3, auto=2, user=1),
           _ev("design", 120, new=6, auto=0, user=7)]
    p = flow.build({"round": 3, "phase": "design"}, 200, q, evs)
    assert p["design"] == {"new": 9, "auto": 2, "user": 8}


def test_deploy_stage_and_old_round_ignored(tmp_path):
    q = tmp_path / "B.md"
    q.write_text("")
    evs = [_ev("phase", 10, round=2, phase="audit"), _ev("phase", 100, round=3, phase="develop"),
           _ev("deploy_start", 200, round=3, units=2)]
    p = flow.build({"round": 3, "phase": "develop", "units_done": 2}, 210, q, evs)
    assert p["stage"] == 4 and p["deploy"]["active"] and p["round_started"] == 100


def test_fallback_from_progress_log(tmp_path):
    q = tmp_path / "B.md"
    q.write_text("")
    log = tmp_path / "p.log"
    now = time.time()
    t = time.strftime("%H:%M:%S", time.localtime(now - 60))
    log.write_text(f"{t} [루프] 라운드 7 · audit 단계 시작\n")
    p = flow.build({"round": 7, "phase": "audit"}, now, q, [], log)
    assert p["inferred"] and p["stage"] == 1 and 50 < now - p["round_started"] < 70


def test_loop_records_events(tmp_path, monkeypatch):
    monkeypatch.setattr(loop, "agents_confirmed", lambda: [])
    q = tmp_path / "B.md"
    q.write_text("")
    st = {"phase": "design", "unit": None, "round": 4, "units_done": 0, "fails": 0, "fix": {}, "stop_reason": None}
    loop.step(st, path=q, force=True, act={})
    kinds = [e["kind"] for e in progress.read_events()]
    assert kinds[:2] == ["phase", "design"]


def test_event_trims_large_file(tmp_path, monkeypatch):
    p = tmp_path / "e.jsonl"
    monkeypatch.setattr(progress, "EVENTS_MAX_BYTES", 200)
    for i in range(30):
        progress.event("phase", p, round=i, phase="audit")
    rounds = [e["round"] for e in progress.read_events(p)]
    assert rounds[-1] == 29 and len(rounds) < 30


def test_sub_states_reset_on_new_audit_pass():
    evs = [
        {"ts": 1, "kind": "sub", "step": "sweep", "state": "start"},
        {"ts": 2, "kind": "sub", "step": "review", "state": "end"},
        {"ts": 9, "kind": "sub", "step": "sweep", "state": "start"},
        {"ts": 10, "kind": "sub", "step": "sweep", "state": "end"},
        {"ts": 10, "kind": "sub", "step": "audit", "state": "start"},
    ]
    st = flow._sub_states(evs)
    assert st["review"]["state"] == "pending"
    assert st["sweep"]["state"] == "done" and st["audit"]["state"] == "active"


def test_steps_only_current_phase_with_failures(tmp_path):
    q = tmp_path / "B.md"
    q.write_text(Q)
    evs = [_ev("phase", 100, round=3, phase="audit"), _ev("sub", 110, step="audit", state="start"),
           _ev("phase", 200, round=3, phase="test"), _ev("sub", 210, step="sweep", state="start"),
           _ev("step", 220, text="1/6 a 시작", bad=False), _ev("step", 230, text="1/6 a 실패 (3s)", bad=True)]
    p = flow.build({"round": 3, "phase": "test"}, 300, q, evs)
    assert [s["text"] for s in p["steps"]] == ["스윕 시작", "1/6 a 시작", "1/6 a 실패 (3s)"]
    assert [s["bad"] for s in p["steps"]] == [False, False, True]


def test_sweep_stream_emits_step_events(tmp_path, monkeypatch):
    from scripts.audit import cycle
    got = []
    monkeypatch.setattr(progress, "event", lambda kind, **kw: got.append((kind, kw)))
    class P:
        stdout = iter(["[sweep] 1/2 s vp 시작\n", "noise\n", "[sweep] 1/2 s vp 실패 (1s): x\n"])
        stderr = None
        def wait(self): return 1
    monkeypatch.setattr(cycle.subprocess, "Popen", lambda *a, **k: P())
    try:
        cycle._sweep_once(1)
    except Exception:
        pass
    assert [k for k, _ in got] == ["step", "step"] and got[1][1]["bad"] is True

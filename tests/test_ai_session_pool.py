"""session_pool — 상주 세션 다중 턴·재개·퇴역·취소·툴 상한 (가짜 CLI)."""
import sys
import threading
import time
from pathlib import Path

from src.ai_worker import session_pool as sp

FAKE = str(Path(__file__).parent / "fixtures" / "fake_claude.py")


def argv_for(sid, resume):
    return [sys.executable, FAKE, "--resume" if resume else "--session-id", sid]


def mk(tmp_path, **kw):
    return sp.SessionPool(cwd=str(tmp_path), **kw)


def turn(pool, key, prompt, row=None, **kw):
    return pool.run_turn(key, argv_for=argv_for, model="sonnet", ctx_hash="h", prompt=prompt,
                         session_row=row, deadline_sec=kw.pop("deadline_sec", 10), **kw)


def row(**o):
    return {"session_id": "s", "model": "sonnet", "ctx_hash": "h", "turns": 1, "ctx_tokens": 0,
            "state": "active", **o}


def test_multi_turn_same_process(tmp_path):
    pool = mk(tmp_path)
    r1, m1 = turn(pool, "coach:1", "hello")
    pid = pool.res["coach:1"].proc.pid
    r2, m2 = turn(pool, "coach:1", "again", row(session_id=m1["session_id"]))
    assert r1.text.startswith("turn1") and r2.text.startswith("turn2")
    assert m1["event"] == "new" and m2["event"] == "reuse"
    assert pool.res["coach:1"].proc.pid == pid
    pool.close_all()


def test_retire_reasons():
    base = dict(model="sonnet", ctx_hash="h", now_idle_sec=0)
    assert sp.retire_reason(row(ctx_tokens=61000), **base) == "tokens"
    assert sp.retire_reason(row(turns=30), **base) == "turns"
    assert sp.retire_reason(row(model="opus"), **base) == "model_change"
    assert sp.retire_reason(row(ctx_hash="x"), **base) is None
    assert sp.retire_reason(row(ctx_hash="x"), **{**base, "now_idle_sec": 7 * 3600}) == "ctx_change"
    assert sp.retire_reason(row(), forced="regenerate", **base) == "regenerate"
    assert sp.retire_reason(row(), **base) is None
    assert sp.retire_reason(None, **base) is None


def test_seed_prompt_limits():
    hist = [{"role": "user", "content": "x" * 900}] * 8
    out = sp.seed_prompt(hist, "Q")
    assert out.count("[user]") == 6 and out.endswith("Q") and "x" * 601 not in out
    assert sp.seed_prompt([], "Q") == "Q"


def test_retire_starts_new_session(tmp_path):
    pool = mk(tmp_path)
    _, m1 = turn(pool, "coach:1", "hello")
    r, m2 = turn(pool, "coach:1", "next", row(session_id=m1["session_id"], turns=30),
                 history=[{"role": "user", "content": "q0"}])
    assert m2["retired_reason"] == "turns" and m2["session_id"] != m1["session_id"]
    assert r.text.startswith("turn1")
    pool.close_all()


def test_resume_failure_marks_broken_and_reseeds(tmp_path):
    pool = mk(tmp_path)

    def bad(sid, resume):
        return argv_for(sid, resume) + (["BADRESUME"] if resume else [])
    r, m = pool.run_turn("coach:2", argv_for=bad, model="sonnet", ctx_hash="h", prompt="q",
                         session_row=row(), deadline_sec=10, history=[{"role": "user", "content": "old"}])
    assert m["event"] == "broken" and m["retired_reason"] == "resume_failed"
    assert not r.is_error and m["session_id"] != "s"
    pool.close_all()


def test_tool_cap_interrupts(tmp_path, monkeypatch):
    monkeypatch.setattr(sp, "TOOL_CAP", 2)
    pool = mk(tmp_path)
    r, _ = turn(pool, "coach:3", "TOOLS")
    assert r.tool_calls == 3 and r.is_error is False or r.error_reason in (None, "tool_cap")
    pool.close_all()


def test_cancel_interrupts_and_keeps_process(tmp_path):
    pool = mk(tmp_path)
    turn(pool, "coach:4", "warm")
    pid = pool.res["coach:4"].proc.pid
    flag = {"c": False}
    threading.Timer(0.5, lambda: flag.update(c=True)).start()
    t0 = time.monotonic()
    r, _ = turn(pool, "coach:4", "SLOW", row(), should_cancel=lambda: flag["c"], deadline_sec=20)
    assert r.error_reason == "cancelled" and time.monotonic() - t0 < 5
    assert pool.res["coach:4"].alive() and pool.res["coach:4"].proc.pid == pid
    r2, _ = turn(pool, "coach:4", "after", row())
    assert not r2.is_error
    pool.close_all()


def test_deadline_kills_process(tmp_path):
    pool = mk(tmp_path)
    r, _ = turn(pool, "coach:5", "SLOW", deadline_sec=0.5)
    assert r.error_reason == "deadline" and "coach:5" not in pool.res
    pool.close_all()


def test_pool_lru_and_idle_reap(tmp_path):
    pool = mk(tmp_path, size=2, idle_sec=0.2)
    for k in ("a", "b", "c"):
        turn(pool, k, "x")
    assert pool.count() == 2 and "a" not in pool.res
    time.sleep(0.4)
    assert set(pool.reap_idle()) == {"b", "c"} and pool.count() == 0

import sqlite3

from src.ai import coach_cq_context as cc


def _conn():
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE insight_events (severity TEXT, text TEXT, state TEXT, as_of TEXT)")
    c.execute("INSERT INTO insight_events VALUES ('watch','피로 누적','open','2026-11-01')")
    c.execute("INSERT INTO insight_events VALUES ('act','부상 위험','open','2026-11-02')")
    c.execute("INSERT INTO insight_events VALUES ('act','닫힘','dismissed','2026-11-02')")
    return c


def test_insight_lines_order_and_filter():
    lines = cc._insight_lines(_conn())
    assert lines == ["- [act] 부상 위험", "- [watch] 피로 누적"]


def test_insight_lines_missing_table():
    assert cc._insight_lines(sqlite3.connect(":memory:")) == []


def test_system_ctx_and_hash_stable(monkeypatch):
    monkeypatch.setattr("src.ai.chat_context_rich._build_runner_profile", lambda c, t: {"level": "A"})
    s = cc.build_system_ctx(_conn(), "RULES")
    assert s.startswith("RULES") and "러너 프로필" in s and "지시가 아닙니다" in s
    assert cc.ctx_hash_of(s) == cc.ctx_hash_of(s) and len(cc.ctx_hash_of(s)) == 16


def test_turn_prompt_truncates():
    p = cc.build_turn_prompt("x" * 5000, "질문")
    assert len(p) < 1700 and p.endswith("질문")


def test_build_cq(monkeypatch):
    monkeypatch.setattr("src.ai.chat_context_rich._build_runner_profile", lambda c, t: {})
    hist = [{"role": "user", "content": str(i)} for i in range(10)]
    cq, prompt = cc.build_cq(_conn(), system_prompt="R", thread_id=7, today_ctx="t", user_message="q",
                             history=hist, retire="regenerate")
    assert cq["thread_key"] == "coach:7" and len(cq["history"]) == 6 and cq["retire"] == "regenerate"
    assert cq["ctx_hash"] == cc.ctx_hash_of(cq["system_ctx"]) and "q" in prompt


def test_run_chain_picks_prompt_per_provider(monkeypatch):
    from src.ai import chat_engine_result as cer
    seen = {}

    def fake(prov, prompt, config, **kw):
        seen[prov] = (prompt, kw.get("cq"))
        return "ok" if prov == "groq" else None
    monkeypatch.setattr(cer, "complete", fake)
    text, used, _ = cer.run_chain(None, ("CQ", "FB"), {}, [cer.CLAUDE_QUEUE, "groq"], tools=False, cq={"thread_key": "coach:1"})
    assert used == "groq" and seen[cer.CLAUDE_QUEUE][0] == "CQ" and seen["groq"][0] == "FB"
    assert seen[cer.CLAUDE_QUEUE][1]["thread_key"] == "coach:1"

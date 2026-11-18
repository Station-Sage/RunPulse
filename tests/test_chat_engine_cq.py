

def test_trailing_reco_line_stripped():
    from src.ai.chat_engine import _TRAILING_RECO
    assert _TRAILING_RECO.sub("", "답변입니다.\n\n[추천: a | b | c]") == "답변입니다."
    assert _TRAILING_RECO.sub("", "[추천] 본문") == "[추천] 본문"


def test_complete_coach_passes_allowed_tools(monkeypatch):
    from src.ai import provider_claude_queue as pq
    got = {}
    monkeypatch.setattr(pq, "complete", lambda conn, config, **kw: got.update(kw) or "ok")
    assert pq.complete_coach(object(), "q", {}, {}, None, {}) == "ok"
    assert "get_activity_laps" in got["allowed_tools"] and got["tools"] == "read"

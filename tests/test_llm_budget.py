"""llm_budget(T7) — 200회째 허용·201회째 quota_user, 전역 합산 거부, usage 추정, KST 자정 경계, 세마포어 busy, 단일 호출 지점."""
import re
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.ai import llm_budget as B
from src.ai.provider_common import ProviderError
from src.ops.store import default_store

DAY = "2026-11-06"


@pytest.fixture(autouse=True)
def _clock(monkeypatch):
    monkeypatch.setattr(B, "now_kst", lambda: datetime(2026, 11, 6, 15, 0, tzinfo=B.KST))


def _call(uid="u", feature="coach", resp=None):
    with B.scope(uid, feature):
        t = B.admit("gemini")
        B.settle(t, resp if resp is not None else {"usage": {"prompt_tokens": 1, "completion_tokens": 1}}, 0, 0)


def test_user_calls_limit_200_then_refuse(monkeypatch):
    monkeypatch.setenv("LLM_LIMITS_JSON", '{"user_per_min": 1000}')
    default_store().add_usage(DAY, "u", "coach", calls=199)
    _call()                                   # 200번째 허용
    with pytest.raises(ProviderError) as e:
        _call()
    assert e.value.reason == "quota_user"
    assert default_store().usage(DAY, "u")["refused"] == 1


def test_user_tokens_limit():
    default_store().add_usage(DAY, "u", "coach", calls=1, tokens_in=300_000)
    with pytest.raises(ProviderError, match="quota_user"):
        _call()


def test_global_sum_refuses_other_user():
    default_store().add_usage(DAY, "a", "coach", calls=2000)
    default_store().add_usage(DAY, "b", "coach", calls=2000)
    with pytest.raises(ProviderError) as e:
        _call("c")
    assert e.value.reason == "quota_global"


def test_global_warning_once(caplog):
    import logging
    default_store().add_usage(DAY, "a", "coach", calls=3300)
    with caplog.at_level(logging.WARNING, logger="runpulse.llm"):
        _call("c")
        _call("c")
    assert sum("80%" in r.message for r in caplog.records) == 1


def test_usage_estimate_when_missing():
    with B.scope("u", "warm"):
        t = B.admit("claude")
        B.settle(t, {"content": []}, prompt_chars=100, out_chars=41)
    assert default_store().usage(DAY, "u")["tokens"] == 50 + 20


def test_claude_usage_fields():
    _call(resp={"usage": {"input_tokens": 7, "output_tokens": 3}})
    assert default_store().usage(DAY, "u")["tokens"] == 10


def test_kst_midnight_boundary(monkeypatch):
    monkeypatch.setattr(B, "now_kst", lambda: datetime(2026, 11, 6, 23, 59, tzinfo=B.KST))
    default_store().add_usage(DAY, "u", "coach", calls=200)
    with pytest.raises(ProviderError):
        _call()
    monkeypatch.setattr(B, "now_kst", lambda: datetime(2026, 11, 7, 0, 0, tzinfo=B.KST))
    _call()
    assert B.day_of(datetime(2026, 11, 6, 15, 30, tzinfo=B.ZoneInfo("UTC"))) == "2026-11-07"


def test_resets_at_next_midnight():
    assert B.resets_at() == "2026-11-07T00:00+09:00"


def test_semaphore_three_then_busy(monkeypatch):
    monkeypatch.setenv("LLM_LIMITS_JSON", '{"acquire_wait_sec": 0.05}')
    held = []
    with B.scope("u", "coach"):
        for _ in range(3):
            held.append(B.admit("gemini"))
        with pytest.raises(ProviderError) as e:
            B.admit("gemini")
        assert e.value.reason == "busy"
        B.settle(held[0], None, 0, 0)
        held.append(B.admit("gemini"))       # 반납 후 다시 허용
    for t in held[1:]:
        B.settle(t, None, 0, 0)


def test_per_minute_limit_busy():
    for _ in range(10):
        _call()
    with pytest.raises(ProviderError, match="busy"):
        _call()


def test_unscoped_measured_not_blocked(monkeypatch):
    monkeypatch.setattr("src.utils.user_context.resolve_user_id", lambda user_id=None: "default")
    default_store().add_usage(DAY, "default", "coach", calls=999)
    t = B.admit("gemini")
    assert t.feature == "unscoped" and not t.held
    B.settle(t, None, 10, 0)
    assert default_store().usage(DAY, "default")["calls"] == 1000


def test_env_override_and_bad_json(monkeypatch):
    monkeypatch.setenv("LLM_LIMITS_JSON", '{"user_calls": 5, "nope": 1}')
    assert B.limits()["user_calls"] == 5 and "nope" not in B.limits()
    monkeypatch.setenv("LLM_LIMITS_JSON", "{bad")
    assert B.limits() == B.LIMITS


def test_ensure_scope_keeps_outer_and_uid_from_db():
    with B.scope("w", "warm"):
        with B.ensure_scope("narrative") as sc:
            assert (sc.uid, sc.feature) == ("w", "warm")
    with B.ensure_scope("narrative", "x") as sc:
        assert sc.feature == "narrative"
    assert B.current() is None
    assert B.uid_from_db("/r/data/users/a@x.com/running.db") == "a@x.com"
    assert B.uid_from_db("/tmp/x.db") is None


def test_usage_today_and_global_ratio():
    default_store().add_usage(DAY, "u", "coach", calls=3, tokens_in=10)
    assert B.usage_today("u") == {"calls": 3, "tokens": 10, "limit_calls": 200, "limit_tokens": 300000,
                                  "resets_at": "2026-11-07T00:00+09:00"}
    assert B.global_ratio() == pytest.approx(3 / 4000)
    assert B.chars_of({"a": "가"}) > 0 and B.chars_of(None) == 0


def test_post_meters_through_single_point():
    from src.ai import chat_engine_providers as P
    resp = MagicMock(status_code=200)
    resp.json.return_value = {"choices": [{"message": {"content": "hi"}}], "usage": {"prompt_tokens": 4,
                                                                                    "completion_tokens": 2}}
    with patch("httpx.post", return_value=resp), B.scope("u", "test"):
        P._post("http://x", {}, {"messages": []}, None, "gemini")
    assert default_store().usage(DAY, "u") == {"calls": 1, "tokens": 6, "refused": 0}


def test_post_refused_makes_no_http():
    from src.ai import chat_engine_providers as P
    default_store().add_usage(DAY, "u", "coach", calls=200)
    with patch("httpx.post") as hp, B.scope("u", "coach"), pytest.raises(ProviderError):
        P._post("http://x", {}, {"messages": []}, None, "gemini")
    assert not hp.called


def test_httpx_post_single_call_site():
    root = Path(__file__).resolve().parent.parent / "src"
    hits = [p for p in root.rglob("*.py") if re.search(r"httpx\.post\(", p.read_text(encoding="utf-8"))]
    assert [p.name for p in hits] == ["chat_engine_providers.py"]

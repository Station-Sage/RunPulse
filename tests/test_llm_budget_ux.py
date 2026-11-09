"""LLM 한도 초과 UX(T8) — Coach 규칙 답변+reason+resets_at, 설정 usage_today, Today reason, 워밍 uid 락·80% 중단."""
import threading
from datetime import datetime
from unittest.mock import patch

import httpx
import pytest

from src.ai import llm_budget as B
from src.ai.chat_engine import chat_result
from src.ops.store import default_store
from src.services import narrative_warm as nw

CFG = {"ai": {"provider": "gemini", "gemini_api_key": "k", "groq_api_key": "k2"}}
CONSENT = {"provider": "gemini", "exclude_notes": False, "tools_enabled": False, "fallback_enabled": True}
DAY = "2026-11-06"


@pytest.fixture(autouse=True)
def _clock(monkeypatch):
    monkeypatch.setattr(B, "now_kst", lambda: datetime(2026, 11, 6, 9, 0, tzinfo=B.KST))


def test_coach_quota_falls_back_to_rule_with_reason(db_conn, monkeypatch):
    posted = []
    monkeypatch.setattr(httpx, "post", lambda *a, **k: posted.append(a) or pytest.fail("호출 금지"))
    default_store().add_usage(DAY, "u", "coach", calls=200)
    with B.scope("u", "coach"):
        r = chat_result(db_conn, "안녕", CFG, consent=CONSENT, require_consent=True)
    assert r.engine.status == "fallback" and r.engine.fallback_reason == "quota_user"
    assert r.engine.resets_at == "2026-11-07T00:00+09:00"
    assert len(r.engine.attempts) == 1          # 다음 provider 시도 안 함
    assert r.text and posted == []
    assert default_store().usage(DAY, "u")["refused"] == 1


def test_reason_labels_and_engine_view():
    import json
    from src.ai.provider_common import REASON_LABELS
    from src.services.coach_engine_health import message_engine_view
    assert REASON_LABELS["quota_user"] == "오늘 AI 사용 한도"
    assert REASON_LABELS["quota_global"] == "AI 사용량 일시 제한" and REASON_LABELS["busy"] == "AI 요청 혼잡"
    v = message_engine_view(json.dumps({"status": "fallback", "fallback_reason": "quota_user",
                                        "resets_at": "2026-11-07T00:00+09:00"}), "rule", "fallback")
    assert v["reason"] == "quota_user" and v["resets_at"] == "2026-11-07T00:00+09:00"


def test_settings_view_has_usage_today(db_conn):
    from src.services import ai_settings_service as svc
    default_store().add_usage(DAY, "u", "coach", calls=5, tokens_in=100, tokens_out=20)
    view = svc.build_view(db_conn, CFG, user_id="u")
    assert view["usage_today"] == {"calls": 5, "tokens": 120, "limit_calls": 200, "limit_tokens": 300000,
                                   "resets_at": "2026-11-07T00:00+09:00"}


def test_connection_test_scoped_and_refused(monkeypatch):
    from src.services import ai_settings_service as svc
    monkeypatch.setattr("src.utils.user_context.resolve_user_id", lambda user_id=None: "t")
    default_store().add_usage(DAY, "t", "coach", calls=200)
    out = svc.test_connection("gemini", CFG)
    assert out["ok"] is False and out["reason"] == "quota_user" and out["label"] == "오늘 AI 사용 한도"


def test_today_narrative_rule_with_reason(db_conn, monkeypatch):
    from src.services import today_service
    monkeypatch.setattr(httpx, "post", lambda *a, **k: pytest.fail("호출 금지"))
    default_store().add_usage(DAY, "n", "coach", calls=200)
    # 활동 0건인 달은 AI 를 부르지 않으므로(T-26) 이번 달 러닝 1건을 둔다.
    db_conn.execute("INSERT INTO activity_summaries (id, source, source_id, name, activity_type, start_time, "
                    "distance_m, duration_sec) VALUES (1, 'garmin', '1', 'Run', 'running', date('now'), 5000, 1800)")
    with B.scope("n", "narrative"):
        out = today_service.get_today_narrative(db_conn, config=CFG)
    assert out["source"] == "rule" and out["reason"] == "quota_user"


def test_warm_lock_is_per_user(db_conn):
    other = nw._user_lock("other")
    other.acquire()
    try:
        with patch("src.services.today_service.get_today_narrative", return_value={"source": "ai"}):
            assert nw.warm_month_narrative(db_conn, DAY, consent_ok=True, user_id="me") == "warmed"
            mine = nw._user_lock("me")
            mine.acquire()
            try:
                assert nw.warm_month_narrative(db_conn, "2026-11-07", consent_ok=True, user_id="me") == "failed"
            finally:
                mine.release()
    finally:
        other.release()
    assert isinstance(nw._user_lock(None), type(threading.Lock()))


def test_warm_scoped_as_warm(db_conn):
    seen = []
    with patch("src.services.today_service.get_today_narrative",
               side_effect=lambda *a, **k: seen.append(B.current()) or {"source": "ai"}):
        nw.warm_month_narrative(db_conn, DAY, consent_ok=True, user_id="me")
    assert (seen[0].uid, seen[0].feature) == ("me", "warm")


def test_warm_stops_at_global_80pct(db_conn):
    default_store().add_usage(DAY, "x", "coach", calls=3200)
    with patch("src.services.today_service.get_today_narrative") as m:
        assert nw.warm_month_narrative(db_conn, DAY, consent_ok=True, user_id="me") == "capped"
    assert not m.called


def test_coach_async_scopes_uid_from_db_path(monkeypatch, tmp_path):
    from src.services import coach_async, coach_service
    seen = []
    monkeypatch.setattr(coach_service, "generate_reply", lambda *a, **k: seen.append(B.current()))
    monkeypatch.setattr(coach_async, "replay_events", lambda conn, mid: [])
    db = tmp_path / "data" / "users" / "c@x.com" / "running.db"
    db.parent.mkdir(parents=True)

    class Run:
        cancel = threading.Event()

        def emit(self, *a):
            pass

        def finish(self):
            pass
    coach_async._execute(Run(), str(db), CFG, 1, 2, "hi", None)
    assert (seen[0].uid, seen[0].feature) == ("c@x.com", "coach")

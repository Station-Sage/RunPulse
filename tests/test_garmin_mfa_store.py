"""garmin_mfa_store(T1) + worker_count(T9) — TTL·uid 바인딩·사용자당 1개·오답 폐기·이중 제출·워커 감지."""
from __future__ import annotations

import logging

import pytest

from src.services import garmin_mfa_store as store
from src.utils.worker_count import check_single_worker, detect_worker_count


@pytest.fixture(autouse=True)
def _clean():
    store.reset()
    store.set_multi_worker(False)
    yield
    store.reset()
    store.set_multi_worker(False)


def test_put_get_roundtrip_and_hash_only():
    t = store.put("a", object(), "a@x.com", now=0)
    p = store.get("a", t, now=1)
    assert p is not None and p.email == "a@x.com" and p.tries == 0
    assert t not in p.ticket_hash and len(t) >= 40


def test_ttl_expiry_with_injected_clock():
    t = store.put("a", object(), "e", now=100)
    assert store.get("a", t, now=100 + store.TTL_S - 1) is not None
    assert store.get("a", t, now=100 + store.TTL_S) is None


def test_other_user_ticket_rejected_and_logged(caplog):
    t = store.put("a", object(), "e", now=0)
    with caplog.at_level(logging.WARNING, logger="runpulse.security"):
        assert store.get("b", t, now=1) is None
    assert "다른 사용자" in caplog.text
    assert store.get("a", t, now=1) is not None


def test_wrong_ticket_rejected():
    store.put("a", object(), "e", now=0)
    assert store.get("a", "nope", now=1) is None
    assert store.get("a", "", now=1) is None


def test_one_pending_per_user():
    t1 = store.put("a", object(), "e", now=0)
    t2 = store.put("a", object(), "e", now=1)
    assert store.get("a", t1, now=2) is None and store.get("a", t2, now=2) is not None


def test_five_failures_discard():
    t = store.put("a", object(), "e")
    lefts = [store.record_failure("a") for _ in range(store.MAX_TRIES)]
    assert lefts == [4, 3, 2, 1, 0]
    assert store.get("a", t) is None
    assert store.record_failure("a") == 0


def test_claim_blocks_double_submit_until_release():
    t = store.put("a", object(), "e")
    assert store.claim("a", t) is not None
    assert store.claim("a", t) is None
    store.release("a")
    assert store.claim("a", t) is not None


def test_sweep_and_discard():
    store.put("a", object(), "e", now=0)
    store.put("b", object(), "e", now=200)
    assert store.sweep(now=store.TTL_S + 1) == 1
    store.discard("b")
    assert store.sweep(now=0) == 0


def test_remaining_seconds():
    store.put("a", object(), "e", now=0)
    p = store._items["a"]
    assert store.remaining_s(p, now=100) == store.TTL_S - 100
    assert store.remaining_s(p, now=10_000) == 0


@pytest.mark.parametrize("env,argv,expected", [
    ({}, ["gunicorn", "--workers", "1"], 1),
    ({}, ["gunicorn", "-w", "3"], 3),
    ({}, ["gunicorn", "--workers=2"], 2),
    ({}, ["gunicorn", "-w4"], 4),
    ({"GUNICORN_CMD_ARGS": "--workers 5"}, ["gunicorn"], 5),
    ({"WEB_CONCURRENCY": "2"}, ["python"], 2),
    ({"WEB_CONCURRENCY": "x"}, ["python"], 1),
    ({}, ["pytest"], 1),
])
def test_detect_worker_count(env, argv, expected):
    assert detect_worker_count(env, argv) == expected


def test_check_single_worker_disables_mfa(caplog):
    with caplog.at_level(logging.WARNING):
        assert check_single_worker({"WEB_CONCURRENCY": "2"}, ["gunicorn"]) is False
    assert store.is_available() is False and "워커 2개" in caplog.text
    assert check_single_worker({}, ["gunicorn", "--workers", "1"]) is True
    assert store.is_available() is True

"""calendar_feed_index — 발급/재발급/해제/조회, 평문 토큰 미저장."""
from __future__ import annotations

import sqlite3

import pytest
from cryptography.fernet import Fernet

from src.services import calendar_feed_index as idx


@pytest.fixture(autouse=True)
def _env(monkeypatch, tmp_path):
    monkeypatch.setattr(idx, "index_path", lambda: tmp_path / "calendar_feeds.db")
    monkeypatch.setenv("CREDENTIAL_ENCRYPTION_KEY", Fernet.generate_key().decode())
    return tmp_path


def test_issue_lookup_and_status():
    t = idx.issue("u1")
    assert t.startswith("rpcal_") and len(t) > 40
    assert idx.lookup(t)[0] == "u1"
    st = idx.get_status("u1")
    assert st["token"] == t and st["last_access_at"] is None
    assert idx.get_status("nobody") is None


def test_rotate_invalidates_old_token():
    old = idx.issue("u1")
    new = idx.issue("u1")
    assert old != new and idx.lookup(old) is None and idx.lookup(new)[0] == "u1"


def test_revoke():
    t = idx.issue("u1")
    assert idx.revoke("u1") is True and idx.revoke("u1") is False
    assert idx.lookup(t) is None


def test_no_plaintext_token_on_disk(_env):
    t = idx.issue("u1")
    raw = b"".join(p.read_bytes() for p in _env.glob("calendar_feeds.db*"))
    assert t.encode() not in raw


def test_not_revealable_without_key(monkeypatch):
    monkeypatch.delenv("CREDENTIAL_ENCRYPTION_KEY")
    t = idx.issue("u1")
    assert idx.lookup(t)[0] == "u1" and idx.get_status("u1")["token"] is None


def test_lookup_rejects_bad_format():
    assert idx.lookup("abc") is None and idx.lookup("rpcal_" + "x" * 200) is None


def test_touch_throttled():
    t = idx.issue("u1")
    h = idx.lookup(t)[1]
    idx.touch(h, "google")
    first = idx.get_status("u1")
    assert first["last_client"] == "google" and first["last_access_at"]
    idx.touch(h, "apple")
    assert idx.get_status("u1")["last_client"] == "google"
    c = sqlite3.connect(idx.index_path())
    c.execute("UPDATE calendar_feeds SET last_access_at=datetime('now','-20 minutes')")
    c.commit()
    c.close()
    idx.touch(h, "apple")
    assert idx.get_status("u1")["last_client"] == "apple"

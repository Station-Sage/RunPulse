"""mcp_remote.token_index / scripts.mcp_token — 해시 저장, 폐기·만료, 상한, 사용자 검증."""
from __future__ import annotations

import sqlite3

import pytest

from src.mcp_remote import token_index as ti


@pytest.fixture
def env(monkeypatch, tmp_path):
    monkeypatch.setattr(ti, "index_path", lambda: tmp_path / "mcp_tokens.db")
    users = tmp_path / "users"

    def gdp(uid=None, *, create=True):
        return users / (uid or "default") / "running.db"

    monkeypatch.setattr(ti, "get_db_path", gdp)
    for u in ("a", "b"):
        (users / u).mkdir(parents=True)
        (users / u / "running.db").write_bytes(b"")
    return tmp_path


def test_issue_format_and_plaintext_not_stored(env):
    tok, meta = ti.issue("a", "genspark")
    assert ti.TOKEN_RE.match(tok) and meta["last4"] == tok[-4:] and meta["expires_at"]
    assert tok.encode() not in (env / "mcp_tokens.db").read_bytes()
    wal = env / "mcp_tokens.db-wal"
    if wal.exists():
        assert tok.encode() not in wal.read_bytes()


def test_lookup_ok_and_malformed(env):
    tok, meta = ti.issue("a", "x")
    assert ti.lookup(tok) == {"token_id": meta["token_id"], "user_id": "a"}
    assert ti.lookup(tok[:-1]) is None
    assert ti.lookup("rpmcp_" + "A" * 43) is None
    assert ti.lookup("x" * 500) is None
    assert ti.lookup(None) is None  # type: ignore[arg-type]


def test_revoke_is_immediate_and_user_scoped(env):
    tok, meta = ti.issue("a", "x")
    assert ti.revoke(meta["token_id"], "b") is False
    assert ti.lookup(tok)
    assert ti.revoke(meta["token_id"], "a") is True
    assert ti.lookup(tok) is None
    assert ti.revoke(meta["token_id"]) is False


def test_expiry(env):
    tok, meta = ti.issue("a", "x")
    c = sqlite3.connect(env / "mcp_tokens.db")
    c.execute("UPDATE mcp_tokens SET expires_at=datetime('now','-1 minutes')")
    c.commit()
    c.close()
    assert ti.lookup(tok) is None
    assert ti.list_tokens("a") == []
    assert len(ti.list_tokens("a", include_inactive=True)) == 1


def test_active_cap_and_revoke_frees_slot(env):
    metas = [ti.issue("a", f"t{i}")[1] for i in range(ti.MAX_ACTIVE_PER_USER)]
    with pytest.raises(ti.TokenError):
        ti.issue("a", "over")
    ti.issue("b", "other-user-ok")
    ti.revoke(metas[0]["token_id"])
    ti.issue("a", "again")


def test_unknown_user_and_bad_input_rejected(env):
    with pytest.raises(ti.TokenError):
        ti.issue("nobody", "x")
    with pytest.raises(ti.TokenError):
        ti.issue("a", "")
    with pytest.raises(ti.TokenError):
        ti.issue("a", "x" * 41)
    with pytest.raises(ti.TokenError):
        ti.issue("a", "x", days=0)
    assert not (env / "users" / "nobody").exists()


def test_lookup_fails_when_user_db_missing(env):
    tok, _ = ti.issue("a", "x")
    (env / "users" / "a" / "running.db").unlink()
    assert ti.lookup(tok) is None


def test_touch_throttled(env):
    tok, meta = ti.issue("a", "x")
    ti.touch(meta["token_id"], "claude-code")
    first = ti.list_tokens("a")[0]
    assert first["last_used_at"] and first["last_client"] == "claude-code"
    ti.touch(meta["token_id"], "other")
    assert ti.list_tokens("a")[0]["last_client"] == "claude-code"


def test_revoke_all(env):
    ti.issue("a", "1")
    ti.issue("a", "2")
    ti.issue("b", "3")
    assert ti.revoke_all("a") == 2
    assert ti.list_tokens("a") == [] and len(ti.list_tokens("b")) == 1


def test_cli_issue_list_revoke(env, capsys):
    import scripts.mcp_token as cli

    assert cli.main(["issue", "--user", "a", "--label", "gs"]) == 0
    out = capsys.readouterr().out.strip().splitlines()
    tid, tok = out[0].split()[0], out[1]
    assert ti.lookup(tok)
    assert cli.main(["list", "--user", "a"]) == 0
    assert tid in capsys.readouterr().out
    assert cli.main(["revoke", tid]) == 0
    assert ti.lookup(tok) is None
    assert cli.main(["issue", "--user", "nobody", "--label", "x"]) == 1

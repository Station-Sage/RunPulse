"""context_episodes·illness_consent 서비스 단위 테스트 (NEW-1~3·9·13·19·22·12~17)."""
import pytest

from tests.helpers_pred import mem_conn
from src.services import context_episodes as E
from src.services import illness_consent as C


@pytest.fixture
def conn():
    return mem_conn()


def test_open_confirmed_and_idempotent(conn):
    a = E.open_episode(conn, "illness", start_date="2026-10-10", severity=2)
    assert E.open_episode(conn, "illness", start_date="2026-10-12") == a
    assert len(E.list_active(conn)) == 1


def test_invalid_kind(conn):
    with pytest.raises(ValueError):
        E.open_episode(conn, "flu")


def test_close_not_before_start(conn):
    a = E.open_episode(conn, "travel", start_date="2026-10-10")
    assert E.close(conn, a, "2026-10-01") is True
    assert conn.execute("SELECT end_date FROM context_episodes").fetchone()[0] == "2026-10-10"
    assert E.close(conn, a) is False


def test_candidate_expires_after_two_days(conn):
    a = E.open_episode(conn, "altitude", origin="auto", status="candidate")
    conn.execute("UPDATE context_episodes SET created_at=datetime('now','-3 days') WHERE id=?", (a,))
    assert E.expire_candidates(conn) == 1
    assert conn.execute("SELECT status FROM context_episodes").fetchone()[0] == "dismissed"


def test_fresh_candidate_stays_and_confirm(conn):
    a = E.open_episode(conn, "travel", origin="auto", status="candidate")
    assert E.list_active(conn)[0]["status"] == "candidate"
    assert E.confirm(conn, a) and E.list_active(conn)[0]["status"] == "confirmed"


def test_dismiss_only_candidate(conn):
    a = E.open_episode(conn, "illness")
    assert E.dismiss(conn, a) is False


def test_illness_reconfirm_boundary(conn):
    today = E._today(conn)
    a = E.open_episode(conn, "illness", start_date=today)
    for days, expect in ((6, False), (7, True)):
        conn.execute("UPDATE context_episodes SET last_confirmed_date=date(?, ?) WHERE id=?", (today, f"-{days} days", a))
        assert (E.illness_reconfirm(conn) is not None) is expect
    E.confirm(conn, a)
    assert E.illness_reconfirm(conn) is None


def test_list_all_hides_dismissed(conn):
    E.open_episode(conn, "travel", origin="auto", status="candidate")
    conn.execute("UPDATE context_episodes SET status='dismissed'")
    assert E.list_all(conn) == [] and len(E.list_all(conn, include_dismissed=True)) == 1


def test_consent_state_machine(conn):
    assert C.needs_first_prompt(conn) and not C.has_consent(conn)
    C.record(conn, "decline", "first_input")
    assert not C.needs_first_prompt(conn) and not C.has_consent(conn)
    C.record(conn, "grant", "settings")
    assert C.has_consent(conn)
    C.record(conn, "revoke", "settings")
    assert not C.has_consent(conn) and C.current_action(conn) == "revoke"
    with pytest.raises(ValueError):
        C.record(conn, "maybe", "settings")


def test_redact_without_consent(conn):
    sigs = [{"signal": "illness", "value": True, "detail": {"severity": 2}, "provider": "context_episodes"},
            {"signal": "crs", "value": 1}]
    out = C.redact_illness_for_ai(conn, sigs)
    assert out[0]["signal"] == "condition" and out[0]["detail"] is None and "illness" not in str(out[0])
    assert out[1] == sigs[1]
    C.record(conn, "grant", "settings")
    assert C.redact_illness_for_ai(conn, sigs) == sigs

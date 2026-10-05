"""sync_errors 분류·SyncResult 전파 테스트."""
import pytest
import requests

from src.sync.sync_errors import SyncSourceError, classify_exception, from_result, MESSAGES_KO, ERROR_CODES
from src.sync.sync_result import SyncResult


def _http(status):
    r = requests.Response()
    r.status_code = status
    return requests.HTTPError(response=r)


@pytest.mark.parametrize("status,code", [
    (401, "auth_expired"), (403, "subscription_required"), (429, "rate_limited"),
    (503, "upstream_5xx"), (404, "unknown"),
])
def test_classify_http(status, code):
    assert classify_exception(_http(status)) == (code, status)


def test_classify_non_http():
    assert classify_exception(requests.Timeout())[0] == "timeout"
    assert classify_exception(requests.ConnectionError())[0] == "network"
    assert classify_exception(ValueError("x"))[0] == "parse"
    assert classify_exception(RuntimeError("x"))[0] == "unknown"


def test_messages_cover_all_codes():
    assert set(MESSAGES_KO) == set(ERROR_CODES)


def test_from_result_only_for_total_failure():
    r = SyncResult(source="strava", job_type="activity", status="failed",
                   error_code="auth_expired", http_status=401, last_error="x")
    err = from_result(r)
    assert isinstance(err, SyncSourceError) and err.code == "auth_expired" and err.http_status == 401
    r.synced_count = 2
    assert from_result(r) is None
    assert from_result(SyncResult(source="s", job_type="activity")) is None


def test_merge_and_job_dict_carry_error_code():
    a = SyncResult(source="s", job_type="activity")
    b = SyncResult(source="s", job_type="wellness", status="failed", error_code="rate_limited", http_status=429)
    a.merge(b)
    d = a.to_sync_job_dict()
    assert d["error_code"] == "rate_limited" and d["http_status"] == 429


def test_strava_wrapper_raises_on_403(monkeypatch):
    import src.sync.strava as st

    def fake_sync(*a, **k):
        return SyncResult(source="strava", job_type="activity", status="failed",
                          error_code="subscription_required", http_status=403)
    monkeypatch.setattr(st._act_sync, "sync", fake_sync)
    with pytest.raises(SyncSourceError) as ei:
        st.sync_activities({}, None, 7)
    assert ei.value.code == "subscription_required"

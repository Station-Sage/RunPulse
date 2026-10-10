"""bg_sync — 일반 예외로 끝난 배치는 전체 0건일 때 failed로 마감한다."""
from __future__ import annotations

from types import SimpleNamespace

from src.web import bg_sync


class _Timeout(Exception):
    pass


_Timeout.__name__ = "ReadTimeout"


def _thread(monkeypatch, calls, counts, tmp_path):
    monkeypatch.setattr(bg_sync, "update_job", lambda jid, **kw: calls.append(kw))
    monkeypatch.setattr(bg_sync, "wait_sec", lambda s: 0)
    monkeypatch.setattr(bg_sync.BgSyncThread, "_interruptible_sleep", lambda self, s: None)
    seq = iter(counts)

    def one_batch(self, *a, **k):
        c = next(seq)
        if c is None:
            self._batch_error = self._batch_error or bg_sync.SyncSourceError("timeout", "t", None)
            return 0, 0, False
        return c, 0, False

    monkeypatch.setattr(bg_sync.BgSyncThread, "_run_one_batch", one_batch)
    monkeypatch.setattr(bg_sync, "get_db_path", lambda uid=None: tmp_path / "r.db")
    t = bg_sync.BgSyncThread("job-1234567", {}, "u")
    # 메트릭 후처리는 별도 검증 대상이 아니므로 생략
    monkeypatch.setattr("src.metrics.engine.run_for_date_range", lambda *a, **k: None, raising=False)
    return t


def _job():
    return SimpleNamespace(
        service="intervals", from_date="2026-09-01", to_date="2026-10-05",
        window_days=30, current_from=None, synced_count=0, req_count=0,
    )


def test_all_batches_failed_marks_failed(monkeypatch, tmp_path):
    calls: list = []
    t = _thread(monkeypatch, calls, [None, None], tmp_path)
    t._run_batches(_job())
    assert calls[-1]["status"] == "failed"
    assert calls[-1]["error_code"] == "timeout"


def test_partial_success_stays_completed(monkeypatch, tmp_path):
    calls: list = []
    t = _thread(monkeypatch, calls, [None, 3], tmp_path)
    t._run_batches(_job())
    statuses = [c.get("status") for c in calls]
    assert "completed" in statuses and "failed" not in statuses


def test_exception_in_batch_is_classified(monkeypatch):
    from src.sync.sync_errors import classify_exception

    assert classify_exception(_Timeout("x"))[0] == "timeout"

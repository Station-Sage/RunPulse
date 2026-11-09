"""스케줄러 연결(T6) — legacy 무회귀, multi 골든(사용자 1명 due·trigger 인자 = legacy), patch_auto→poke, run_user."""
import random
from datetime import date, datetime, timedelta

import pytest

from src.ops.store import OpsStore
from src.sync import auto_sync, scheduler_run as R
from src.sync.bg_sync_wait import WaitResult, reset_services
from src.sync.scheduler import MultiUserScheduler, RunResult

CFG = {"garmin": {"email": "a"}, "strava": {"refresh_token": "t"}, "sync_sources": ["garmin", "strava"],
       "auto_sync": {"enabled": True, "interval_hours": 4, "days": 2}}


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    reset_services()
    monkeypatch.setattr(R, "_instance", None)
    yield
    reset_services()


def _patch_env(monkeypatch, config=CFG, gates=None, busy=(), statuses=None):
    import src.utils.config as cfg
    import src.utils.sync_gates as g
    import src.utils.sync_jobs as sj
    import src.utils.sync_ledger_query as q
    monkeypatch.setattr(cfg, "load_config", lambda user_id=None: dict(config))
    monkeypatch.setattr(g, "wait_sec", lambda svc, uid=None: (gates or {}).get(svc))
    monkeypatch.setattr(q, "is_busy", lambda svc, uid=None: svc in busy)
    st = statuses or {}

    class J:
        def __init__(self, s):
            self.status = s
    monkeypatch.setattr(sj, "get_job", lambda jid: J(st.get(jid, "completed")))


# ── legacy 무회귀 ────────────────────────────────────────────
def test_mode_default_is_legacy(monkeypatch):
    assert auto_sync.scheduler_mode() == "legacy"
    monkeypatch.setenv("SYNC_SCHEDULER", "weird")
    assert auto_sync.scheduler_mode() == "legacy"
    monkeypatch.setenv("SYNC_SCHEDULER", "MULTI")
    assert auto_sync.scheduler_mode() == "multi"


def test_legacy_start_uses_single_thread_not_scheduler(monkeypatch):
    called = []
    monkeypatch.setattr(auto_sync, "_loop", lambda *a: called.append(a) or auto_sync._stop_event.wait(5))
    monkeypatch.setattr(R, "start_multi", lambda: pytest.fail("multi 기동 금지"))
    auto_sync.stop()                      # 다른 테스트(create_app 등)가 띄운 스레드 정리
    if auto_sync._thread is not None:
        auto_sync._thread.join(timeout=5)
    auto_sync.start(CFG, "u1")
    try:
        assert auto_sync._thread.is_alive() and R.instance() is None
        assert auto_sync.status("u1")["running"] is True
    finally:
        auto_sync.stop()
        auto_sync._thread.join(timeout=5)
    assert called[0][1:] == ("u1", 4, 2)


def test_legacy_patch_auto_restarts(monkeypatch):
    from src.services import data_settings_service as d
    got = []
    monkeypatch.setattr(d, "save_config", lambda c, user_id=None: None)
    monkeypatch.setattr(auto_sync, "restart", lambda c, uid: got.append(("restart", uid)))
    monkeypatch.setattr(R, "poke", lambda uid: got.append(("poke", uid)))
    d.patch_auto({}, "u1", {"interval_hours": 6})
    assert got == [("restart", "u1")]


def test_multi_patch_auto_pokes_not_restart(monkeypatch):
    from src.services import data_settings_service as d
    monkeypatch.setenv("SYNC_SCHEDULER", "multi")
    got = []
    monkeypatch.setattr(d, "save_config", lambda c, user_id=None: None)
    monkeypatch.setattr(auto_sync, "restart", lambda c, uid: got.append(("restart", uid)))
    monkeypatch.setattr(R, "poke", lambda uid: got.append(("poke", uid)))
    out = d.patch_auto({}, "u2", {"interval_hours": 6})
    assert got == [("poke", "u2")] and out["interval_h"] == 6


def test_multi_start_boots_scheduler(monkeypatch):
    monkeypatch.setenv("SYNC_SCHEDULER", "multi")
    booted = []
    monkeypatch.setattr(R, "start_multi", lambda: booted.append(1))
    auto_sync.start(CFG, "ignored")
    assert booted == [1]


def test_poke_without_instance_is_false():
    assert R.poke("u") is False


# ── multi 골든: 사용자 1명이면 legacy 와 같은 시각·인자 ─────────
@pytest.mark.parametrize("ago,due", [(timedelta(hours=4), True), (timedelta(hours=3, minutes=59), False),
                                     (None, True)])
def test_golden_due_matches_legacy(tmp_path, ago, due):
    now = datetime(2026, 11, 6, 12, 0, 0)
    last = now - ago if ago else None
    legacy_fires = last is None or (now - last) >= timedelta(hours=4)
    sent = []
    s = MultiUserScheduler(clock=lambda: now, wait=lambda x: True,
                           executor=type("E", (), {"submit": lambda self, fn, *a: sent.append(a)})(),
                           rng=random.Random(0), users=lambda: ["op"], trigger=lambda u: None,
                           store=OpsStore(tmp_path / "o.db"), last_auto_run=lambda u: last,
                           user_interval=lambda u: 4)
    s.tick()
    assert bool(sent) is legacy_fires is due


def test_golden_trigger_args_match_legacy(monkeypatch):
    _patch_env(monkeypatch)
    legacy, multi = [], []
    import src.sync.bg_sync as bg
    monkeypatch.setattr(bg, "start_basic_sync", lambda *a, **k: legacy.append((a, k)) or {})
    auto_sync._trigger(CFG, "op", 2)
    R.run_user("op", start_sync=lambda *a, **k: multi.append((a, k)) or {"garmin": "j1", "strava": "j2"},
               wait=lambda uid, ids, t: WaitResult(True))
    assert legacy == multi
    assert legacy[0][0][2] == date.today().isoformat()


# ── run_user ────────────────────────────────────────────────
def _run(monkeypatch, **kw):
    started = []
    res = R.run_user("u", start_sync=lambda *a, **k: started.append(a[0]) or {s: f"j-{s}" for s in a[0]},
                     wait=kw.pop("wait", lambda uid, ids, t: WaitResult(True)))
    return res, started


def test_run_user_ok(monkeypatch):
    _patch_env(monkeypatch)
    res, started = _run(monkeypatch)
    assert res.result == "ok" and started == [["garmin", "strava"]] and res.interval_h == 4


def test_run_user_disabled_and_no_source(monkeypatch):
    _patch_env(monkeypatch, config={**CFG, "auto_sync": {"enabled": False}})
    assert _run(monkeypatch)[0].result == "skipped_disabled"
    _patch_env(monkeypatch, config={"auto_sync": {}})
    assert _run(monkeypatch)[0].result == "skipped_no_source"


def test_run_user_gated_sources_excluded(monkeypatch):
    _patch_env(monkeypatch, gates={"garmin": 600})
    res, started = _run(monkeypatch)
    assert started == [["strava"]]
    _patch_env(monkeypatch, gates={"garmin": 600, "strava": 300})
    res, started = _run(monkeypatch)
    assert res.result == "skipped_gated" and started == []
    assert 299 <= (res.retry_at - datetime.now()).total_seconds() <= 301


def test_run_user_busy(monkeypatch):
    _patch_env(monkeypatch, busy=("strava",))
    res, started = _run(monkeypatch)
    assert res.result == "skipped_busy" and started == []


def test_run_user_slot_taken(monkeypatch):
    from src.sync.bg_sync_wait import acquire_services
    _patch_env(monkeypatch)
    acquire_services(["garmin"])
    res, started = _run(monkeypatch)
    assert res.result == "skipped_slot" and started == []


def test_run_user_timeout_releases_tokens(monkeypatch):
    from src.sync.bg_sync_wait import acquire_services
    _patch_env(monkeypatch)
    res, _ = _run(monkeypatch, wait=lambda uid, ids, t: WaitResult(False, ["j-garmin"]))
    assert res.result == "timeout" and res.detail == "j-garmin"
    assert acquire_services(["garmin"]) == ["garmin"]


def test_run_user_auth(monkeypatch):
    _patch_env(monkeypatch, statuses={"j-garmin": "auth_required", "j-strava": "auth_required"})
    assert _run(monkeypatch)[0].result == "auth"


def test_default_users_drop_default(monkeypatch):
    import src.utils.user_context as uc
    monkeypatch.setattr(uc, "list_user_ids", lambda **k: ["a@x.com", "default"])
    assert R.default_users() == ["a@x.com"]
    monkeypatch.setattr(uc, "list_user_ids", lambda **k: [])
    assert R.default_users() == ["default"]


def test_default_users_registry(monkeypatch, tmp_path):
    from src.auth import registry
    monkeypatch.setenv("AUTH_MODE", "registry")
    monkeypatch.setattr(registry, "db_path", lambda: tmp_path / "auth.db")
    conn = registry.connect()
    with conn:
        conn.execute("INSERT INTO accounts (uid, email_norm, status) VALUES ('a@x.com','a@x.com','active')")
        conn.execute("INSERT INTO accounts (uid, email_norm, status) VALUES ('p@x.com','p@x.com','pending')")
    conn.close()
    assert R.default_users() == ["a@x.com"]


def test_suspend_source_blocks_gate(monkeypatch):
    got = []
    import src.utils.sync_gates as g
    monkeypatch.setattr(g, "block", lambda svc, sec, reason, user_id=None: got.append((svc, sec, reason, user_id)))
    R.suspend_source("u", "garmin")
    assert got == [("garmin", 30 * 86400, "auth_suspended", "u")]


def test_release_user_clears_thread_local():
    from src.utils import user_context as uc
    uc.set_current_user("zz")
    R.release_user()
    assert getattr(uc._LOCAL, "user_id") is None


def test_config_interval_and_last_run(monkeypatch):
    _patch_env(monkeypatch, config={"auto_sync": {"interval_hours": 12}})
    assert R.config_interval("u") == 12
    assert R.ledger_last_auto_run("u") is None


def test_start_multi_singleton(monkeypatch, tmp_path):
    monkeypatch.setattr(MultiUserScheduler, "start", lambda self: None)
    a = R.start_multi()
    assert R.start_multi() is a and R.instance() is a
    assert R.poke("u") is True and "u" in a._poked


def test_auto_settings_state(monkeypatch):
    from src.services import data_settings_service as d
    import src.utils.sync_gates as g
    from src.ops.store import default_store
    monkeypatch.setattr(g, "gate", lambda svc, uid=None: type("G", (), {"reason_code": "auth_suspended"})())
    out = d.auto_settings(CFG, None, user_id="u")
    assert out["state"] == "auth_suspended"
    monkeypatch.setattr(g, "gate", lambda svc, uid=None: None)
    assert d.auto_settings(CFG, None, user_id="u")["state"] == "active"
    monkeypatch.setenv("SYNC_SCHEDULER", "multi")
    due = datetime.now() + timedelta(hours=2)
    default_store().put_state("u", next_due_at=due)
    assert d.auto_settings(CFG, None, user_id="u")["next_run_at"] == due.isoformat(timespec="seconds")
    default_store().put_state("u", next_due_at=due, state="dormant")
    out = d.auto_settings(CFG, None, user_id="u")
    assert out["state"] == "dormant" and out["next_run_at"] is None

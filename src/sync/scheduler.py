"""MultiUserScheduler — 단일 스레드 tick 루프로 활성 사용자 전원을 자동 동기화한다(multiuser-sync §3.1·§3.2, T5).

동시 사용자 2, 사용자별 in-flight 중복 0, 한 사용자의 예외는 루프·다른 사용자에 전파하지 않는다.
의존(clock·wait·executor·rng·users·trigger·store)은 모두 주입 — 테스트는 `tick()`을 직접 부른다.
실제 사용자 작업(run_user)·기본 의존은 scheduler_run.py.
"""
from __future__ import annotations

import logging
import random
import threading
from collections import Counter
from concurrent.futures import Executor
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable

from src.sync import scheduler_policy as P

log = logging.getLogger("runpulse.sched")


@dataclass
class RunResult:
    result: str                                   # ok|fail|auth|timeout|skipped_*
    interval_h: int = P.DEFAULT_INTERVAL_H
    sources: list[str] = field(default_factory=list)
    job_ids: list[str] = field(default_factory=list)
    statuses: dict[str, str | None] = field(default_factory=dict)
    retry_at: datetime | None = None              # skipped_gated 일 때 min(retry_after)
    detail: str | None = None


@dataclass
class SchedCfg:
    max_concurrent: int = P.MAX_CONCURRENT_USERS
    tick_sec: float = 60.0
    start_grace_sec: float = 120.0
    log_every_sec: float = 600.0
    pinned: frozenset[str] = frozenset()


@dataclass
class TickReport:
    due: int = 0
    dispatched: int = 0
    inflight: int = 0
    skipped: dict[str, int] = field(default_factory=dict)

    def key(self) -> tuple:
        return (self.due, self.dispatched, self.inflight, tuple(sorted(self.skipped.items())))


class MultiUserScheduler:
    def __init__(self, *, clock: Callable[[], datetime], wait: Callable[[float], bool] | None,
                 executor: Executor, rng: random.Random, users: Callable[[], list[str]],
                 trigger: Callable[[str], RunResult], store, cfg: SchedCfg | None = None,
                 last_auto_run: Callable[[str], datetime | None] | None = None,
                 user_interval: Callable[[str], int] | None = None,
                 suspend: Callable[[str, str], None] | None = None,
                 release_user: Callable[[], None] | None = None):
        from src.sync import scheduler_run as R
        self.clock, self.executor, self.rng = clock, executor, rng
        self.users, self.trigger, self.store = users, trigger, store
        self.cfg = cfg or SchedCfg()
        self._stop = threading.Event()
        self.wait = wait or self._stop.wait
        self.last_auto_run = last_auto_run or R.ledger_last_auto_run
        self.user_interval = user_interval or R.config_interval
        self.suspend = suspend or R.suspend_source
        self.release_user = release_user or R.release_user
        self._lock = threading.Lock()
        self._inflight: set[str] = set()
        self._poked: set[str] = set()
        self._skips: Counter = Counter()
        self._overdue_warned: set[str] = set()
        self._thread: threading.Thread | None = None
        self._last_log: tuple[tuple, datetime] | None = None

    # ── 제어 ──────────────────────────────────────────────────
    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="sync-scheduler")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def poke(self, uid: str) -> None:
        """다음 tick 에 원장 기준으로 due 를 다시 계산한다(설정 변경·휴면 해제)."""
        with self._lock:
            self._poked.add(uid)

    def inflight(self) -> set[str]:
        with self._lock:
            return set(self._inflight)

    def _loop(self) -> None:
        log.info("scheduler start tick=%ss max_concurrent=%d", self.cfg.tick_sec, self.cfg.max_concurrent)
        if self.wait(self.cfg.start_grace_sec):
            return
        last_purge: datetime | None = None
        while True:
            try:
                self._log_tick(self.tick())
                now = self.clock()
                if last_purge is None or now - last_purge >= timedelta(days=1):
                    last_purge = now
                    self.store.purge(now)  # sched_runs 14일·llm_usage_daily 90일 보존
            except Exception:  # noqa: BLE001 — 루프는 죽지 않는다
                log.exception("tick 실패")
            if self.wait(self.cfg.tick_sec):
                break
        log.info("scheduler stop")

    # ── tick ──────────────────────────────────────────────────
    def tick(self) -> TickReport:
        now = self.clock()
        states = self.store.all_states()
        activity = self.store.all_activity()
        with self._lock:
            poked, self._poked = self._poked, set()
            inflight = set(self._inflight)
            skipped, self._skips = self._skips, Counter()
        due: dict[str, datetime] = {}
        for uid in self.users():
            st = states.get(uid)
            tier = P.activity_tier(activity.get(uid), now, pinned=uid in self.cfg.pinned)
            if tier == "dormant":
                if st is None or st["state"] != "dormant":
                    self._put(uid, st, next_due_at=(st or {}).get("next_due_at") or now, state="dormant")
                skipped["dormant"] += 1
                continue
            if st is None or uid in poked or st["state"] == "dormant":
                st = self._init_state(uid, st, now)
            if uid in inflight:
                continue
            due[uid] = st["next_due_at"]
        cands = P.order_candidates(due, now)
        self._warn_overdue(cands, due, now)
        slots = max(0, self.cfg.max_concurrent - len(inflight))
        dispatched = cands[:slots]
        for uid in dispatched:
            self._overdue_warned.discard(uid)
            with self._lock:
                self._inflight.add(uid)
            try:
                self.executor.submit(self._execute, uid)
            except Exception:  # noqa: BLE001
                log.exception("dispatch 실패 uid=%s", self._mask(uid))
                with self._lock:
                    self._inflight.discard(uid)
        with self._lock:
            n_inflight = len(self._inflight)
        return TickReport(len(cands), len(dispatched), n_inflight, dict(skipped))

    def _init_state(self, uid: str, st: dict | None, now: datetime) -> dict:
        try:
            interval = self.user_interval(uid)
            d = P.initial_due(self.last_auto_run(uid), interval, now)
        except Exception:  # noqa: BLE001
            log.warning("상태 초기화 실패 uid=%s — 즉시 due", self._mask(uid), exc_info=True)
            d = now
        return self._put(uid, st, next_due_at=d, state="active")

    def _put(self, uid: str, st: dict | None, **changes) -> dict:
        cur = {"next_due_at": None, "state": "active", "fail_streak": 0, "auth_streak": {},
               "last_result": None, **(st or {}), **changes}
        self.store.put_state(uid, next_due_at=cur["next_due_at"], state=cur["state"],
                             fail_streak=cur["fail_streak"], auth_streak=cur["auth_streak"],
                             last_result=cur["last_result"])
        return cur

    # ── 사용자 작업 ───────────────────────────────────────────
    def _execute(self, uid: str) -> None:
        started = self.clock()
        try:
            try:
                res = self.trigger(uid)
            except Exception as exc:  # noqa: BLE001 — 다른 사용자·루프로 전파 금지
                log.warning("run 예외 uid=%s: %s", self._mask(uid), type(exc).__name__, exc_info=True)
                res = RunResult("fail", detail=type(exc).__name__)
            finally:
                try:
                    self.release_user()
                except Exception:  # noqa: BLE001
                    pass
            self._finish(uid, res, started)
        except Exception:  # noqa: BLE001
            log.exception("run 마감 실패 uid=%s", self._mask(uid))
        finally:
            with self._lock:
                self._inflight.discard(uid)

    def _finish(self, uid: str, res: RunResult, started: datetime) -> None:
        if res.result.startswith("skipped_"):
            with self._lock:
                self._skips[res.result[len("skipped_"):]] += 1
        if res.result == "skipped_slot":
            return  # due 유지 — 다음 tick 재시도
        now = self.clock()
        st = self.store.get_state(uid) or {}
        if res.result == "timeout" and st.get("last_result") == "timeout":
            log.warning("timeout 2회 연속 uid=%s", self._mask(uid))
        streak = int(st.get("fail_streak") or 0)
        auth = dict(st.get("auth_streak") or {})
        state = "active"
        if res.result == "skipped_busy":
            nxt = now + timedelta(seconds=P.BUSY_DEFER_SEC)
        elif res.result == "skipped_gated":
            nxt = res.retry_at or now + timedelta(seconds=P.BUSY_DEFER_SEC)
        elif res.result in ("skipped_disabled", "skipped_no_source"):
            state = "disabled" if res.result == "skipped_disabled" else "active"
            nxt = now + timedelta(hours=res.interval_h)
        else:
            streak = P.next_fail_streak(res.result, streak)
            auth, suspend = P.update_auth_streak(auth, res.statuses)
            for svc in suspend:
                try:
                    self.suspend(uid, svc)
                    log.warning("auth_suspended uid=%s source=%s streak=%d", self._mask(uid), svc, auth[svc])
                except Exception:  # noqa: BLE001
                    log.warning("인증 중지 기록 실패 uid=%s source=%s", self._mask(uid), svc, exc_info=True)
            tier = P.activity_tier(self.store.last_active(uid), now, pinned=uid in self.cfg.pinned)
            nxt = P.next_due(now, res.interval_h, fail_streak=streak, tier=tier, rng=self.rng)
        self._put(uid, st or None, next_due_at=nxt, state=state, fail_streak=streak, auth_streak=auth,
                  last_result=res.result)
        self.store.add_run(uid, started_at=started, finished_at=now, result=res.result, sources=res.sources,
                           job_ids=res.job_ids, detail=res.detail)
        log.info("run uid=%s result=%s dur=%.0fs sources=%s streak=%d", self._mask(uid), res.result,
                 (now - started).total_seconds(), ",".join(res.sources), streak)

    # ── 관측 ──────────────────────────────────────────────────
    def _warn_overdue(self, cands: list[str], due: dict[str, datetime], now: datetime) -> None:
        """연체가 2×interval 을 넘은 사용자 WARNING(사용자당 1회, 디스패치되면 해제)."""
        for uid in cands:
            late_h = (now - due[uid]).total_seconds() / 3600
            if late_h < 2 or uid in self._overdue_warned:
                continue
            try:
                interval = self.user_interval(uid)
            except Exception:  # noqa: BLE001
                continue
            if late_h > 2 * interval:
                self._overdue_warned.add(uid)
                log.warning("overdue uid=%s late=%.1fh interval=%dh", self._mask(uid), late_h, interval)

    def _log_tick(self, rep: TickReport) -> None:
        now = self.clock()
        last = self._last_log
        if last and last[0] == rep.key() and (now - last[1]).total_seconds() < self.cfg.log_every_sec:
            return
        self._last_log = (rep.key(), now)
        sk = ",".join(f"{k}={v}" for k, v in sorted(rep.skipped.items())) or "-"
        log.info("tick due=%d dispatched=%d inflight=%d skipped={%s}", rep.due, rep.dispatched, rep.inflight, sk)

    @staticmethod
    def _mask(uid: str) -> str:
        from src.utils.user_context import mask_uid
        return mask_uid(uid)

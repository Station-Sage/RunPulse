"""AI 워커 진입점 — preflight, 큐 폴링·실행, 하트비트, 쿼터 일시정지, 연속 오류 자가정지 (host systemd 용)."""
from __future__ import annotations

import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from src.ai_worker import cli_runner as cr
from src.ai_worker import queue_store as qs

DEADLINE_SEC = {"coach": 120, "insight_polish": 60, "narrative": 90, "adherence": 90,
                "plan_draft": 240, "deep_analysis": 240, "ping": 60}
HEARTBEAT_SEC = 5
POLL_SEC = 1.0
SELF_PAUSE_AFTER = 5
SELF_PAUSE_SEC = 600
ALLOWED_CLI_MAJORS = {2}
_VER = re.compile(r"(\d+)\.(\d+)\.(\d+)")


class Worker:
    def __init__(self, uid: str, db_path, *, state_dir: Path, work_dir: Path, pythonpath: str,
                 claude_bin: str = "claude", concurrency: int = 2, runner=cr.run):
        self.uid, self.db_path = uid, str(db_path)
        self.state_dir, self.work_dir, self.pythonpath = Path(state_dir), Path(work_dir), pythonpath
        self.claude_bin, self.concurrency, self.runner = claude_bin, concurrency, runner
        self.worker_id = f"w{os.getpid()}-{int(time.time())}"
        self.cli_version = ""
        self.active: set[int] = set()
        self.consec_errors = 0
        self.stop = threading.Event()
        self.started_at = qs.now_iso()
        self._lock = threading.Lock()

    # --- preflight -------------------------------------------------------
    def preflight(self) -> str | None:
        """문제가 있으면 사유 문자열, 없으면 None."""
        try:
            out = subprocess.run([self.claude_bin, "--version"], capture_output=True, text=True, timeout=20).stdout
        except (OSError, subprocess.TimeoutExpired) as e:
            return f"cli_missing:{e}"
        m = _VER.search(out)
        if not m or int(m.group(1)) not in ALLOWED_CLI_MAJORS:
            return f"cli_version_unsupported:{out.strip()}"
        self.cli_version = m.group(0)
        for suffix in ("", "-wal", "-shm"):
            p = self.db_path + suffix
            if os.path.exists(p) and not os.access(p, os.W_OK):
                return f"db_not_writable:{p}"
        self.work_dir.mkdir(parents=True, exist_ok=True)
        if any(self.work_dir.iterdir()):
            return f"work_dir_not_empty:{self.work_dir}"
        return None

    # --- job 실행 --------------------------------------------------------
    def _prepare(self, job: dict) -> tuple[list[str], str]:
        inp = json.loads(job["input_json"] or "{}")
        sys_file = None
        if job.get("system_ctx"):
            h = job.get("ctx_hash") or hashlib.sha256(job["system_ctx"].encode()).hexdigest()[:16]
            d = self.state_dir / "ctx"
            d.mkdir(parents=True, exist_ok=True)
            sys_file = d / f"{h}.txt"
            if not sys_file.exists():
                sys_file.write_text(job["system_ctx"], encoding="utf-8")
        mcp_file, allowed = None, None
        if job["tools"] == "read":
            cfg = cr.build_mcp_config(user_id=self.uid, pythonpath=self.pythonpath,
                                      home=str(Path.home()))
            d = self.state_dir / "mcp"
            d.mkdir(parents=True, exist_ok=True)
            mcp_file = d / f"{self.worker_id}.json"
            mcp_file.write_text(json.dumps(cfg), encoding="utf-8")
            allowed = [f"mcp__runpulse__{t}" for t in inp.get("allowed_tools", [])]
        argv = cr.build_argv(model=job["model"], system_prompt_file=str(sys_file) if sys_file else None,
                             mcp_config=str(mcp_file) if mcp_file else None, allowed_tools=allowed,
                             partial=True, claude_bin=self.claude_bin)
        return argv, str(inp.get("prompt", ""))

    def run_job(self, job: dict) -> None:
        conn = qs.connect(self.db_path)
        jid = job["id"]
        try:
            try:
                argv, prompt = self._prepare(job)
            except Exception as e:  # 잘못된 입력은 재시도 없이 실패
                qs.finish(conn, jid, "failed", error_reason=f"bad_job:{type(e).__name__}")
                return
            env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(Path.home())}
            res = self.runner(
                argv, prompt=prompt, cwd=str(self.work_dir), env=env,
                deadline_sec=DEADLINE_SEC.get(job["kind"], 90),
                should_cancel=lambda: qs.cancel_requested(conn, jid),
                on_progress=lambda r: qs.update_progress(conn, jid, None, r.partial_text))
            self._settle(conn, job, res)
        except Exception as e:
            qs.finish(conn, jid, "failed", error_reason=f"worker_exc:{type(e).__name__}")
            self._count_error()
        finally:
            with self._lock:
                self.active.discard(jid)
            conn.close()

    def _settle(self, conn, job: dict, res: cr.RunResult) -> None:
        jid = job["id"]
        common = dict(session_id=res.session_id, tokens_in=res.tokens_in, tokens_out=res.tokens_out,
                      cache_read=res.cache_read, tool_calls=res.tool_calls)
        if res.error_reason == "cancelled":
            qs.finish(conn, jid, "cancelled", error_reason="cancelled", **common)
        elif res.quota:
            until = res.quota_reset_at or cr.fallback_pause_until()
            qs.set_paused(conn, self.worker_id, until, "quota")
            qs.finish(conn, jid, "failed", error_reason="quota_sub", **common)
        elif res.is_error:
            qs.finish(conn, jid, "failed", error_reason=res.error_reason or "cli_error", **common)
            self._count_error()
        else:
            self.consec_errors = 0
            qs.finish(conn, jid, "done", result_text=res.text, **common)

    def _count_error(self) -> None:
        self.consec_errors += 1
        if self.consec_errors >= SELF_PAUSE_AFTER:
            conn = qs.connect(self.db_path)
            try:
                until = qs._shift(qs.now_iso(), SELF_PAUSE_SEC)
                qs.set_paused(conn, self.worker_id, until, "consecutive_errors")
            finally:
                conn.close()
            self.consec_errors = 0

    # --- 루프 ------------------------------------------------------------
    def tick(self, conn, pool: ThreadPoolExecutor | None = None) -> int:
        """한 번의 폴링: 하트비트·회수·만료·집기. 시작한 job 수를 반환."""
        now = qs.now_iso()
        with self._lock:
            ids = list(self.active)
            n_active = len(ids)
        qs.heartbeat(conn, ids, now)
        qs.upsert_worker_state(conn, self.worker_id, pid=os.getpid(), cli_version=self.cli_version,
                               active_jobs=n_active, started_at=self.started_at, now=now)
        qs.recover_stale(conn, None, now)
        qs.expire_queued(conn, now)
        if qs.is_paused(conn, self.worker_id, now):
            return 0
        started = 0
        while n_active + started < self.concurrency:
            job = qs.claim(conn, self.worker_id, qs.now_iso())
            if not job:
                break
            with self._lock:
                self.active.add(job["id"])
            started += 1
            if pool:
                pool.submit(self.run_job, job)
            else:
                self.run_job(job)
        return started

    def serve(self) -> int:
        bad = self.preflight()
        self.started_at = qs.now_iso()
        conn = qs.connect(self.db_path)
        if bad:
            qs.upsert_worker_state(conn, self.worker_id, pid=os.getpid(), cli_version=self.cli_version,
                                   active_jobs=0, started_at=self.started_at)
            qs.set_paused(conn, self.worker_id, qs._shift(qs.now_iso(), 3600), f"preflight:{bad}")
            print(f"preflight failed: {bad}", file=sys.stderr)
            return 2
        qs.recover_stale(conn, self.worker_id)
        last_purge = 0.0
        with ThreadPoolExecutor(max_workers=self.concurrency) as pool:
            while not self.stop.is_set():
                try:
                    self.tick(conn, pool)
                    if time.monotonic() - last_purge > 3600:
                        qs.purge_bodies(conn)
                        last_purge = time.monotonic()
                except Exception as e:
                    print(f"tick error: {e}", file=sys.stderr)
                self.stop.wait(POLL_SEC if not self.active else HEARTBEAT_SEC / 2)
        return 0


def main() -> int:
    from src.db_setup import get_db_path
    uids = [u for u in os.environ.get("CQ_UIDS", "").split(",") if u]
    if len(uids) != 1:
        print("CQ_UIDS must name exactly one uid", file=sys.stderr)
        return 2
    uid = uids[0]
    root = os.environ.get("RUNPULSE_ROOT", os.getcwd())
    state = Path(os.environ.get("CQ_STATE_DIR", Path.home() / ".local/state/runpulse-ai"))
    w = Worker(uid, get_db_path(uid, create=False), state_dir=state, work_dir=state / "work",
               pythonpath=os.environ.get("PYTHONPATH", root),
               concurrency=int(os.environ.get("CQ_CONCURRENCY", "2")))
    signal.signal(signal.SIGTERM, lambda *_: w.stop.set())
    return w.serve()


if __name__ == "__main__":
    sys.exit(main())

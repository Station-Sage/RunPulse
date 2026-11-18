"""claude_queue.run_job 스레드·진행·취소 확장 (E4-a)."""
import json
import threading
import time

from src.ai import claude_queue as cq
from src.ai_worker import queue_store as qs
from src.db_schema_v48 import ensure_v48


def _db(tmp_path):
    p = str(tmp_path / "q.db")
    c = qs.connect(p)
    ensure_v48(c)
    c.close()
    return p


def _worker(p, action):
    def run():
        c = qs.connect(p)
        for _ in range(100):
            j = qs.claim(c, "w1")
            if j:
                action(c, j)
                break
            time.sleep(0.05)
        c.close()
    t = threading.Thread(target=run)
    t.start()
    return t


def test_thread_fields_and_progress(tmp_path):
    p = _db(tmp_path)
    got, prog = {}, []

    def act(c, j):
        got.update(j)
        qs.update_progress(c, j["id"], '{"stage":"tool"}', "부분")
        time.sleep(0.6)
        qs.finish(c, j["id"], "done", result_text="ok")

    t = _worker(p, act)
    r = cq.run_job(p, kind="coach", model="sonnet", prompt="q", deadline_sec=10, thread_key="coach:1",
                   ctx_hash="h1", history=[{"role": "user", "content": "a"}], retire="regenerate",
                   on_progress=lambda pj, pt: prog.append((pj, pt)), sleep=lambda s: time.sleep(0.1))
    t.join()
    assert r["ok"] and r["text"] == "ok"
    assert got["thread_key"] == "coach:1" and got["ctx_hash"] == "h1"
    inp = json.loads(got["input_json"])
    assert inp["history"][0]["content"] == "a" and inp["retire"] == "regenerate"
    assert ('{"stage":"tool"}', "부분") in prog


def test_should_cancel_queued(tmp_path):
    p = _db(tmp_path)
    r = cq.run_job(p, kind="coach", model="sonnet", prompt="q", deadline_sec=5, queue_wait=5,
                   should_cancel=lambda: True, sleep=lambda s: time.sleep(0.05))
    assert not r["ok"] and r["reason"] == "cancelled"

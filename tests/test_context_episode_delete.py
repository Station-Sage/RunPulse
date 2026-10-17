"""에피소드 삭제 연쇄 테스트 (NEW-18·28)."""
import json

from src.services import context_episodes as E
from src.services.context_episode_delete import delete_episode
from tests.helpers_pred import mem_conn


def _adj(c, source, decision, signals="[]", reasons="[]"):
    c.execute("INSERT INTO planned_workouts(date, workout_type, source) VALUES ('2026-10-20','easy','manual')")
    wid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    c.execute("INSERT INTO plan_adjustments(workout_id,date,source,before_json,after_json,reasons_json,signals_json,"
              "rule_version,decision) VALUES (?,?,?,?,?,?,?,?,?)",
              (wid, "2026-10-20", source, "{}", "{}", reasons, signals, "v3", decision))
    return c.execute("SELECT last_insert_rowid()").fetchone()[0]


def _setup():
    c = mem_conn()
    e = E.open_episode(c, "illness", severity=2)
    return c, e


def test_missing_returns_none():
    assert delete_episode(mem_conn(), 99) is None


def test_travel_keeps_history():
    c = mem_conn()
    t = E.open_episode(c, "travel")
    _adj(c, "readiness", "accepted", signals='[{"signal":"travel"}]')
    assert delete_episode(c, t)["kind"] == "travel"
    assert c.execute("SELECT COUNT(*) FROM plan_adjustments WHERE signals_json LIKE '%travel%'").fetchone()[0] == 1


def test_illness_anonymizes_and_withdraws():
    c, e = _setup()
    sig = json.dumps([{"signal": "illness", "value": 2, "detail": {"site": "목"}}])
    rea = json.dumps([{"key": "illness", "text": "감기"}])
    prop = _adj(c, "illness", "proposed", sig, rea)
    acc = _adj(c, "illness", "accepted", sig, rea)
    delete_episode(c, e)
    r = {i: c.execute("SELECT decision, source, signals_json, reasons_json FROM plan_adjustments WHERE id=?", (i,)).fetchone()
         for i in (prop, acc)}
    assert r[prop][0] == "reverted" and r[acc][0] == "accepted"
    for _, src, sj, rj in r.values():
        assert src == "readiness" and "illness" not in sj + rj and "감기" not in rj and "목" not in sj
    assert c.execute("SELECT COUNT(*) FROM context_episodes").fetchone()[0] == 0


def test_illness_clears_cache_and_chats():
    c, e = _setup()
    from src.ai.ai_cache import _ensure_table
    _ensure_table(c)
    c.execute("INSERT INTO ai_cache(tab,cache_key,content_json,generated_at,data_fingerprint) VALUES ('t','k','{}','x','f')")
    c.execute("INSERT INTO chat_threads(id,title) VALUES (1,'a'),(2,'b')")
    c.execute("INSERT INTO chat_messages(role,content,thread_id) VALUES ('user','x',1),('user','y',2),('user','z',NULL)")
    out = delete_episode(c, e, chat_thread_ids=[1])
    assert out["chat_deleted"] == 2
    assert c.execute("SELECT COUNT(*) FROM ai_cache").fetchone()[0] == 0
    assert [r[0] for r in c.execute("SELECT id FROM chat_threads")] == [2]
    assert c.execute("SELECT content FROM chat_messages").fetchall() == [("y",)]

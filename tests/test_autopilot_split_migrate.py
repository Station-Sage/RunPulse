from scripts.audit import decisions
from scripts.autopilot import queue, split_migrate

_ITEM = ('- **[SPLIT-a-py]** (후속: P7-X 에서 발견) [refactor] src/a.py 가 348줄로 300줄 상한 초과 → 분리한다.\n'
         '  <!-- autopilot: {"stage": "%s", "mode": "auto", "attempts": %d, "deps": [], "kind": "code", "scope": ["src/a.py"], "verify": []} -->\n')


def _run(tmp_path, stage="queued", attempts=0, apply=True):
    q, d = tmp_path / "B.md", tmp_path / "d.json"
    q.write_text(_ITEM % (stage, attempts), encoding="utf-8")
    return q, d, split_migrate.migrate(q, d, apply=apply)


def test_migrates_queued_split(tmp_path):
    q, d, ids = _run(tmp_path)
    assert ids == ["SPLIT-a-py"]
    assert queue.parse(q)[0].stage == "needs_decision"
    card = decisions.load(d)[0]
    assert card["kind"] == "split_decision" and card["path"] == "src/a.py" and card["lines"] == 348


def test_dry_run_changes_nothing(tmp_path):
    q, d, ids = _run(tmp_path, apply=False)
    assert ids == ["SPLIT-a-py"] and queue.parse(q)[0].stage == "queued" and decisions.load(d) == []


def test_skips_started_or_decided(tmp_path):
    assert _run(tmp_path, attempts=1)[2] == []
    q, d, _ = _run(tmp_path)
    assert split_migrate.migrate(q, d, apply=True) == []

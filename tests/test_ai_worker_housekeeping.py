"""워커 jsonl 정리."""
import os
import time

from src.ai_worker import housekeeping as hk


def test_purge_transcripts_removes_only_old_jsonl(tmp_path):
    work = tmp_path / "state" / "work"
    work.mkdir(parents=True)
    d = hk.transcript_dir(work, tmp_path)
    d.mkdir(parents=True)
    old, new, other = d / "a.jsonl", d / "b.jsonl", d / "c.txt"
    for f in (old, new, other):
        f.write_text("x")
    t = time.time() - 20 * 86400
    os.utime(old, (t, t))
    os.utime(other, (t, t))
    assert hk.purge_transcripts(work, home=tmp_path) == 1
    assert not old.exists() and new.exists() and other.exists()


def test_purge_transcripts_missing_dir(tmp_path):
    assert hk.purge_transcripts(tmp_path / "none", home=tmp_path) == 0

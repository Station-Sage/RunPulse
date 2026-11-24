import subprocess

from scripts.autopilot import trailers


def test_strip_trailers():
    msg = "feat: x\n\n본문\n\nCo-Authored-By: Claude <noreply@anthropic.com>\n🤖 Generated with [Claude Code](u)\n"
    assert trailers.strip_trailers(msg) == "feat: x\n\n본문\n"


def test_scrub_range_rewrites(tmp_path):
    def g(*a):
        return subprocess.run(["git", *a], cwd=tmp_path, capture_output=True, text=True, check=True).stdout
    g("init", "-q"); g("config", "user.email", "a@b"); g("config", "user.name", "n")
    (tmp_path / "f").write_text("1"); g("add", "f"); g("commit", "-qm", "base")
    base = g("rev-parse", "HEAD").strip()
    (tmp_path / "f").write_text("2"); g("add", "f")
    g("commit", "-qm", "feat: y\n\nCo-Authored-By: Claude <noreply@anthropic.com>")
    assert trailers.scrub_range(tmp_path, base) == 1
    assert "Co-Authored" not in g("log", "-1", "--format=%B")
    assert trailers.scrub_range(tmp_path, base) == 0

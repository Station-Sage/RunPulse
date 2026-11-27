"""누락 의존성 설치 — 허용 입력·명령 구성·결과 메시지, 결정 카드."""
import subprocess
from pathlib import Path

from scripts.autopilot import dep_install, fail_handling


def test_command_npm_and_pip(tmp_path):
    argv, cwd = dep_install.command("npm", "@a/b", tmp_path, tmp_path / "m")
    assert argv == ["npm", "install", "-D", "@a/b"] and cwd == tmp_path / "frontend"
    argv, cwd = dep_install.command("pip", "yaml", tmp_path, tmp_path / "m")
    assert argv[1:] == ["-m", "pip", "install", "yaml"] and cwd == tmp_path / "m"


def test_command_rejects_bad_input(tmp_path):
    assert dep_install.command("npm", "x; rm -rf /", tmp_path, tmp_path) is None
    assert dep_install.command("npm", "--global", tmp_path, tmp_path) is None
    assert dep_install.command("gem", "x", tmp_path, tmp_path) is None


def test_install_results(tmp_path):
    ok = lambda *a, **k: subprocess.CompletedProcess(a, 0, stdout="added 1", stderr="")
    bad = lambda *a, **k: subprocess.CompletedProcess(a, 1, stdout="", stderr="E404")
    assert dep_install.install("npm", "vitest", tmp_path, tmp_path, run=ok)[0] is True
    okf, msg = dep_install.install("npm", "vitest", tmp_path, tmp_path, run=bad)
    assert okf is False and "rc=1" in msg
    okf, msg = dep_install.install("npm", "a b", tmp_path, tmp_path, run=ok)
    assert okf is False and "허용되지" in msg

    def boom(*a, **k):
        raise OSError("no npm")
    assert dep_install.install("npm", "vitest", tmp_path, tmp_path, run=boom)[0] is False


def test_build_dep_card():
    c = fail_handling.build_dep_card("X-1", "npm", "vitest", "r", "t")
    assert [o["action"] for o in c["options"]] == ["install_dep", "retry_verify", "dropped"]
    assert c["dep"] == {"eco": "npm", "name": "vitest"} and "vitest" in c["summary"]

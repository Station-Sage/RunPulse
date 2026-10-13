"""scripts/check_user_dirs.py — 운영 점검 스크립트(S3-1) 단위 테스트."""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("check_user_dirs", ROOT / "scripts" / "check_user_dirs.py")
cud = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cud)


def test_clean_root_returns_0(tmp_path, capsys):
    for n in ("default", "alice@example.com"):
        (tmp_path / n).mkdir()
    assert cud.main(["--root", str(tmp_path)]) == 0
    assert "위반 0개" in capsys.readouterr().out


def test_violations_masked_and_exit_1(tmp_path, capsys):
    (tmp_path / "default").mkdir()
    (tmp_path / ".hidden").mkdir()
    (tmp_path / "bad name").mkdir()
    (tmp_path / "file.txt").write_text("x")
    assert cud.main(["--root", str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert "bad name" not in out and ".hidden" not in out
    assert "ba***(len=8)" in out and "위반 2개" in out and "검사 3개" in out


def test_show_names_flag(tmp_path, capsys):
    (tmp_path / "bad name").mkdir()
    cud.main(["--root", str(tmp_path), "--show-names"])
    assert "bad name" in capsys.readouterr().out


def test_symlink_escape_flagged(tmp_path, capsys):
    users = tmp_path / "users"
    users.mkdir()
    (tmp_path / "outside").mkdir()
    (users / "evil").symlink_to(tmp_path / "outside", target_is_directory=True)
    assert cud.main(["--root", str(users)]) == 1
    assert "symlink-escape" in capsys.readouterr().out


def test_read_only_and_missing_root(tmp_path, capsys):
    (tmp_path / "default").mkdir()
    before = sorted(p.name for p in tmp_path.iterdir())
    cud.main(["--root", str(tmp_path)])
    assert sorted(p.name for p in tmp_path.iterdir()) == before
    assert cud.main(["--root", str(tmp_path / "nope")]) == 2

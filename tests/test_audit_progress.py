from scripts.audit import progress


def test_mark_appends_line_and_returns_it(tmp_path, capsys):
    p = tmp_path / "a" / "progress.log"
    line = progress.mark("[루프] 시작", p)
    progress.mark("[루프] 끝", p)
    assert line.endswith("[루프] 시작")
    assert p.read_text(encoding="utf-8").splitlines()[1].endswith("[루프] 끝")
    assert "[루프] 시작" in capsys.readouterr().err

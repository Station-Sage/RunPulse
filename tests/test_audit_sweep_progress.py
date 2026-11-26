"""sweep 진행 로그 + cycle._sweep_once 스트리밍 파싱."""
from scripts.audit import cycle, sweep


def test_sweep_main_prints_progress(monkeypatch, capsys):
    monkeypatch.setattr(sweep, "sweep_state", lambda s, v, d, lim, only=None: [{"k": 1}, {"k": 2}])
    monkeypatch.setattr(sweep, "apply_results", lambda res: len(res))
    assert sweep.main(["--states", "empty,small", "--viewports", "390"]) == 0
    out = capsys.readouterr().out
    assert "[sweep] 1/2 empty 390 시작" in out
    assert "[sweep] 2/2 small 390 완료 — 2셀" in out
    assert '"swept": 4' in out


def test_sweep_main_reports_failure(monkeypatch, capsys):
    def boom(*a, **k):
        raise RuntimeError("x")
    monkeypatch.setattr(sweep, "sweep_state", boom)
    assert sweep.main(["--states", "empty", "--viewports", "390"]) == 1
    assert "실패" in capsys.readouterr().out


def test_sweep_once_streams_and_parses(monkeypatch, capsys):
    import io
    import subprocess

    class P:
        stdout = io.StringIO('[sweep] 1/1 empty 390 시작\n{"swept": 5, "failed": []}\n')
        def wait(self):
            return 0
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: P())
    assert cycle._sweep_once(None) == (5, None)
    assert "[sweep] 1/1" in capsys.readouterr().out

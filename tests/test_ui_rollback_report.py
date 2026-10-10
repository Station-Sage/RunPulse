"""scripts/ui_rollback_report.py CLI."""
import json

from scripts.ui_rollback_report import main
from tests.test_ui_events import _user


def test_empty_prints_undetermined(tmp_path, capsys):
    assert main(["--users-root", str(tmp_path)]) == 0
    assert "미판정" in capsys.readouterr().out


def test_json_output(tmp_path, capsys):
    _user(tmp_path, "a")
    main(["--users-root", str(tmp_path), "--json", "--days", "3650"])
    d = json.loads(capsys.readouterr().out)
    assert d["active_users"] == 1 and d["verdict"] == "통과"

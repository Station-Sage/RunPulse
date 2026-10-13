"""user_context — user_id 해석 우선순위."""
import threading

import pytest

from src.utils import user_context as uc


def test_argument_wins():
    uc.set_current_user("tl")
    assert uc.resolve_user_id("arg") == "arg"


def test_thread_local_fallback_is_per_thread():
    uc.set_current_user("main")
    seen = {}

    def worker():
        uc.set_current_user("worker")
        seen["w"] = uc.resolve_user_id(None)

    t = threading.Thread(target=worker)
    t.start()
    t.join()
    assert seen["w"] == "worker"
    assert uc.resolve_user_id(None) == "main"


def test_default_without_context():
    uc._LOCAL.__dict__.pop("user_id", None)
    assert uc.resolve_user_id(None) == "default"


# ── validate_uid / get_db_path (SRV-13, S3 3단계) ───────────────────────────

@pytest.mark.parametrize("uid", [
    "default", "alice@example.com", "user.name+tag@my-domain.co.kr", "a", "x" * 254, "u_1-2", "100%@x.io",
])
def test_validate_uid_accepts_existing_forms(uid):
    assert uc.validate_uid(uid) == uid


@pytest.mark.parametrize("uid", [
    "", ".", "..", "../x", "..\\x", "a/b", "a\\b", ".hidden", ".a@b.com", "a b", " a", "a ", "a\n", "é", "한글",
    "x" * 255, "a:b", "a*b", "a\x00b", None, 5, ["a"],
])
def test_validate_uid_rejects(uid):
    with pytest.raises(uc.InvalidUserId):
        uc.validate_uid(uid)


def test_invalid_uid_error_does_not_carry_raw_value():
    with pytest.raises(uc.InvalidUserId) as ei:
        uc.validate_uid("secret@evil/../x")
    assert "secret" not in str(ei.value) and "secret" not in ei.value.masked
    assert ei.value.masked == "se***(len=16)"
    assert isinstance(ei.value, ValueError)


def test_get_db_path_rejects_and_creates_no_directory(tmp_path, monkeypatch):
    import src.db_setup as dbs
    monkeypatch.setattr(dbs, "_PROJECT_ROOT", tmp_path)
    for bad in ("..", "../escape", "a/b", ".hid"):
        with pytest.raises(uc.InvalidUserId):
            dbs.get_db_path(bad)
    assert not (tmp_path / "data").exists()  # mkdir 이 일어나지 않았다
    assert not (tmp_path / "escape").exists()
    ok = dbs.get_db_path("alice@example.com")
    assert ok == tmp_path / "data" / "users" / "alice@example.com" / "running.db"
    assert ok.parent.is_dir()
    assert dbs.get_db_path(None) == tmp_path / "data" / "users" / "default" / "running.db"


def test_get_db_path_rejects_symlink_escape(tmp_path, monkeypatch):
    """이중 방어: uid 자체는 규칙에 맞아도 data/users/<uid> 가 밖을 가리키는 링크면 거부."""
    import src.db_setup as dbs
    monkeypatch.setattr(dbs, "_PROJECT_ROOT", tmp_path)
    users = tmp_path / "data" / "users"
    users.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    (users / "evil").symlink_to(outside, target_is_directory=True)
    with pytest.raises(uc.InvalidUserId):
        dbs.get_db_path("evil", create=False)


def test_get_config_path_validates_uid(tmp_path, monkeypatch):
    import src.utils.config as cfg
    monkeypatch.setattr(cfg, "_PROJECT_ROOT", tmp_path)
    with pytest.raises(uc.InvalidUserId):
        cfg.get_config_path("../x")
    assert not (tmp_path / "data").exists()
    assert cfg.get_config_path("bob").parent == tmp_path / "data" / "users" / "bob"
    assert cfg.get_config_path("default") == cfg._CONFIG_PATH


def test_list_user_ids_skips_invalid_dirs_and_logs_masked(tmp_path, monkeypatch, caplog):
    import logging
    monkeypatch.setattr(uc, "project_root", lambda: tmp_path)
    assert uc.list_user_ids() == []
    root = tmp_path / "data" / "users"
    for name in ("default", "alice@example.com", ".hidden", "bad name"):
        (root / name).mkdir(parents=True)
    (root / "afile").write_text("x")
    with caplog.at_level(logging.WARNING, logger="runpulse.security"):
        assert uc.list_user_ids() == ["alice@example.com", "default"]
    text = " ".join(r.getMessage() for r in caplog.records)
    assert "bad name" not in text and ".hidden" not in text
    assert "ba***(len=8)" in text

"""user_context — user_id 해석 우선순위."""
import threading

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

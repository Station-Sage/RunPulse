"""Garmin 연결 테스트 공용 가짜 `garminconnect.Garmin` — 실제 로그인·네트워크 호출 없음."""
from __future__ import annotations

import json
from pathlib import Path

from src.sync import garmin_auth as ga


class FakeTokenClient:
    def __init__(self, owner: "FakeGarmin"):
        self.owner = owner

    def dump(self, path: str) -> None:
        if self.owner.cfg.get("dump_error"):
            raise self.owner.cfg["dump_error"]
        p = Path(path)
        p.mkdir(parents=True, exist_ok=True)
        (p / "garmin_tokens.json").write_text(json.dumps({"di_token": "NEW", "di_refresh_token": "R"}))


class FakeGarmin:
    """cfg 키: login(반환값 또는 예외), resume(예외 목록 — 앞에서부터 하나씩 소비), dump_error."""

    def __init__(self, cfg: dict, calls: list, email=None, password=None, return_on_mfa=False):
        self.cfg, self.calls = cfg, calls
        self.username, self.password, self.return_on_mfa = email, password, return_on_mfa
        self.client = FakeTokenClient(self)
        calls.append(("init", email, return_on_mfa))

    def login(self, tokenstore=None):
        self.calls.append(("login", tokenstore))
        res = self.cfg.get("login", (None, None))
        if isinstance(res, Exception):
            raise res
        return res

    def resume_login(self, state, code):
        self.calls.append(("resume", code))
        queue = self.cfg.setdefault("resume", [])
        if queue:
            err = queue.pop(0)
            if err is not None:
                raise err
        return None, None


def install(monkeypatch, svc, cfg: dict | None = None) -> tuple[dict, list]:
    """svc._garmin_cls 를 가짜로 바꾼다. (cfg, calls) 반환 — cfg 를 바꿔 동작을 조정한다."""
    cfg = {} if cfg is None else cfg
    calls: list = []
    monkeypatch.setattr(svc, "_garmin_cls", lambda: (lambda *a, **k: FakeGarmin(cfg, calls, *a, **k)))
    return cfg, calls


AUTH = ga.GarminConnectAuthenticationError
TOO_MANY = ga.GarminConnectTooManyRequestsError
CONN = ga.GarminConnectConnectionError

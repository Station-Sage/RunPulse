"""audit/deploy.py — 운영 반영 가드·병합·빌드 분기 (git/npm 은 주입한 sh 로 대체)."""
from pathlib import Path

from scripts.audit import deploy


def _sh(answers):
    log = []

    def sh(args, cwd):
        log.append(args)
        for key, val in answers.items():
            if key in " ".join(args):
                return val
        return 0, ""
    return sh, log


BASE = {"rev-parse --abbrev-ref": (0, "renew/data-architecture"), "status --porcelain": (0, ""),
        "rev-list --count": (0, "2"), "merge-base": (0, ""), "rev-parse HEAD": (0, "abc"),
        "diff --name-only": (0, "frontend/src/a.svelte\nsrc/x.py")}


def run(units=1, **over):
    sh, log = _sh({**BASE, **over})
    return deploy.run(units, sh=sh, prod=Path("/prod")), log


def test_guards_leave_everything_untouched():
    assert not run(0)[0]["ran"]
    assert "브랜치" in run(**{"rev-parse --abbrev-ref": (0, "other")})[0]["reason"]
    assert "변경" in run(**{"status --porcelain": (0, " M a.py")})[0]["reason"]
    r, log = run(**{"rev-list --count": (0, "0")})
    assert not r["ran"] and not any("merge" == a[1] for a in log)


def test_diverged_and_merge_failure_report_failed():
    r, log = run(**{"merge-base": (1, "")})
    assert r["outcome"] == "failed" and "갈라짐" in r["reason"] and not any(a[1] == "merge" for a in log)
    assert run(**{"merge --ff-only": (1, "x")})[0]["outcome"] == "failed"


def test_merge_builds_frontend_only_when_changed():
    r, log = run()
    assert r["outcome"] == "done" and r["commits"] == 2 and r["prev"] == "abc" and ["npm", "run", "build"] in log
    r, log = run(**{"diff --name-only": (0, "src/x.py")})
    assert r["outcome"] == "done" and ["npm", "run", "build"] not in log
    assert run(**{"npm run build": (1, "err")})[0]["outcome"] == "failed"


def test_full_pytest_gates_merge_with_lf_retry():
    r, log = run(**{"pytest": (1, "F")})
    assert r["outcome"] == "failed" and "테스트" in r["reason"] and not any(a[1] == "merge" for a in log)
    assert any("--lf" in a for a in log)


def test_flaky_failure_passes_on_lf_rerun():
    calls = []

    def sh(args, cwd):
        s = " ".join(args)
        if "pytest" in s:
            calls.append(s)
            return (0, "") if "--lf" in s else (1, "F")
        return BASE.get(next((k for k in BASE if k in s), ""), (0, ""))
    r = deploy.run(1, sh=sh, prod=Path("/prod"))
    assert r["outcome"] == "done" and len(calls) == 2

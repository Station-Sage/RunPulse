"""커버리지 인벤토리 — SvelteKit 화면·Flask API 를 자동 추출해 화면×상태×뷰포트 셀 목록을 만든다.

사용:
  .venv/bin/python scripts/audit/inventory.py --write    # v0.3/data/audit/coverage_inventory.json 갱신
  .venv/bin/python scripts/audit/inventory.py --check    # 커밋된 인벤토리와 실제 라우트 일치 여부(불일치 시 exit 1)
  .venv/bin/python scripts/audit/inventory.py --report   # 원장 기준 커버리지 요약·미확인 셀 출력
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ROUTES_DIR = ROOT / "frontend" / "src" / "routes"
INVENTORY_PATH = ROOT / "v0.3" / "data" / "audit" / "coverage_inventory.json"
LEDGER_PATH = ROOT / ".claude" / "autopilot" / "coverage_ledger.json"

STATES = ("empty", "small", "large", "error")
VIEWPORTS = ("390", "desktop")
STATUSES = ("확인", "이슈")        # 원장에 없는 셀 = 미확인
_SKIP_API: tuple[str, ...] = ()   # 감사 제외 API 접두어


def frontend_screens(routes_dir: Path = ROUTES_DIR) -> list[str]:
    """`+page.svelte` 위치에서 화면 경로를 뽑는다. 동적 파라미터는 `[id]` 형태 그대로 유지."""
    out = []
    for p in routes_dir.rglob("+page.svelte"):
        parts = [s for s in p.parent.relative_to(routes_dir).parts if not (s.startswith("(") and s.endswith(")"))]
        out.append("/" + "/".join(parts))
    return sorted(out)


def flask_apis() -> list[dict]:
    """Flask url_map 에서 /api/ 엔드포인트를 뽑는다(임시 DB 로 앱 생성 — 운영 DB 를 건드리지 않음)."""
    sys.path.insert(0, str(ROOT))
    from scripts.synth_smoke.serve_synth import make_app

    with tempfile.TemporaryDirectory() as d:
        app = make_app(Path(d) / "inventory.db")
        rows = {}
        for r in app.url_map.iter_rules():
            rule = str(r.rule)
            if not rule.startswith("/api/") or rule.startswith(_SKIP_API):
                continue
            rows.setdefault(rule, set()).update(r.methods - {"HEAD", "OPTIONS"})
    return [{"rule": k, "methods": sorted(v)} for k, v in sorted(rows.items())]


def build(screens: list[str] | None = None, apis: list[dict] | None = None) -> dict:
    screens = frontend_screens() if screens is None else screens
    apis = flask_apis() if apis is None else apis
    return {"states": list(STATES), "viewports": list(VIEWPORTS), "screens": screens, "apis": apis}


def cell_ids(inv: dict) -> list[str]:
    """화면×상태×뷰포트 셀 id(`route|state|viewport`)."""
    return [f"{s}|{st}|{vp}" for s in inv["screens"] for st in inv["states"] for vp in inv["viewports"]]


def load_ledger(path: Path = LEDGER_PATH) -> dict[str, dict]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def record(cell: str, status: str, note: str = "", path: Path = LEDGER_PATH) -> None:
    """원장에 셀 결과 기록. status 는 확인/이슈."""
    if status not in STATUSES:
        raise ValueError(f"status must be one of {STATUSES}")
    ledger = load_ledger(path)
    ledger[cell] = {"status": status, "note": note}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(ledger, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")


def coverage(inv: dict, ledger: dict[str, dict]) -> dict:
    """원장 기준 요약. 인벤토리에 없는 낡은 셀은 stale 로 분리한다."""
    cells = cell_ids(inv)
    known = set(cells)
    done = [c for c in cells if c in ledger]
    return {"total": len(cells), "checked": len(done),
            "issues": [c for c in done if ledger[c]["status"] == "이슈"],
            "unchecked": [c for c in cells if c not in ledger],
            "stale": sorted(c for c in ledger if c not in known)}


def diff(committed: dict, live: dict) -> dict:
    """커밋된 인벤토리 대비 실제 라우트의 추가/삭제."""
    out = {}
    for key in ("screens",):
        a, b = set(committed.get(key, [])), set(live[key])
        out[key] = {"added": sorted(b - a), "removed": sorted(a - b)}
    ca = {(x["rule"], tuple(x["methods"])) for x in committed.get("apis", [])}
    cb = {(x["rule"], tuple(x["methods"])) for x in live["apis"]}
    out["apis"] = {"added": sorted(f"{r} {','.join(m)}" for r, m in cb - ca),
                   "removed": sorted(f"{r} {','.join(m)}" for r, m in ca - cb)}
    return out


def _dump(inv: dict) -> str:
    return json.dumps(inv, ensure_ascii=False, indent=1) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--write", action="store_true")
    g.add_argument("--check", action="store_true")
    g.add_argument("--report", action="store_true")
    a = ap.parse_args(argv)
    live = build()
    if a.write:
        INVENTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        INVENTORY_PATH.write_text(_dump(live), encoding="utf-8")
        print(f"인벤토리 기록: 화면 {len(live['screens'])}, API {len(live['apis'])}, 셀 {len(cell_ids(live))}")
        return 0
    if a.check:
        committed = json.loads(INVENTORY_PATH.read_text(encoding="utf-8")) if INVENTORY_PATH.exists() else {}
        d = diff(committed, live)
        bad = any(v["added"] or v["removed"] for v in d.values())
        for k, v in d.items():
            for x in v["added"]:
                print(f"+ {k}: {x}")
            for x in v["removed"]:
                print(f"- {k}: {x}")
        print("불일치 — `--write` 로 갱신" if bad else "일치")
        return 1 if bad else 0
    c = coverage(live, load_ledger())
    print(f"셀 {c['checked']}/{c['total']} 확인, 이슈 {len(c['issues'])}, 미확인 {len(c['unchecked'])}, stale {len(c['stale'])}")
    for x in c["unchecked"][:30]:
        print("  미확인", x)
    return 0


if __name__ == "__main__":
    sys.exit(main())

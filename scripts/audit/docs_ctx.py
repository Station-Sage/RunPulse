"""역할별 문서 컨텍스트 로더 — v0.3/data/releases 트리에서 프롬프트에 주입할 발췌를 만든다(규약은 그 폴더의 README.md)."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RELEASES = ROOT / "v0.3" / "data" / "releases"
READS = {  # 역할 → (문서 키 목록). 키: vision / retro / plan / design
    "steward": ("vision", "retro"),
    "planner": ("vision", "retro", "plan"),
    "designer": ("vision", "plan", "design"),
    "developer": ("design",),
    "verifier": ("design",),
    "auditor": ("vision", "plan"),
}
CAP = 6000  # 문서 1건 발췌 상한(문자)
_SAFE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except OSError:
        return ""


def vision_text(root: Path | None = None) -> str:
    """VISION.md 본문(헤더·인용 안내 제외). 없으면 빈 문자열."""
    body = _read((root or RELEASES) / "VISION.md")
    return "\n".join(ln for ln in body.splitlines() if not ln.startswith(("#", ">"))).strip()


def paths(version: str | None = None, ini: str | None = None, root: Path | None = None) -> dict[str, Path]:
    base = root or RELEASES
    out = {"vision": base / "VISION.md"}
    if version and _SAFE.match(version):
        out["plan"] = base / version / "PLAN.md"
        out["retro"] = base / version / "RETRO.md"
        if ini and _SAFE.match(ini):
            out["design"] = base / version / "initiatives" / ini / "DESIGN.md"
    return out


def context(role: str, version: str | None = None, ini: str | None = None, root: Path | None = None) -> str:
    """역할이 읽어야 할 문서를 '[문서 키] 경로' 머리말과 함께 이어 붙인다. 없는 문서는 건너뛴다."""
    ps = paths(version, ini, root)
    parts = []
    for key in READS.get(role, ()):
        p = ps.get(key)
        txt = _read(p).strip() if p else ""
        if txt:
            parts.append(f"[문서:{key}] {p.relative_to(root or ROOT) if (root or ROOT) in p.parents else p}\n{txt[:CAP]}")
    return "\n\n".join(parts)


def augment(prompt: str, role: str, ini: str | None = None) -> str:
    """`%`·format 치환이 끝난 프롬프트 뒤에 현재 버전 기준 역할 문서를 덧붙인다(문서가 없으면 그대로)."""
    try:
        from scripts.audit import release_plan
        ver = release_plan.current(release_plan.load())
    except Exception:  # noqa: BLE001 — 문서 주입 실패가 감사 전체를 막으면 안 된다
        ver = None
    ctx = context(role, ver, ini)
    return f"{prompt}\n\n--- 참고 문서(규약: v0.3/data/releases/README.md) ---\n{ctx}" if ctx else prompt

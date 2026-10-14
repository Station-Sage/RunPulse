"""SvelteKit 정적 빌드(`frontend/build`) 서빙 정책 — `/v2/` 경로 판정·캐시 규칙·인라인 스크립트 해시.

설계: design-2026-10/patterns/security-headers.md §2.3 (E-04, S3 7단계).
- `resolve_v2` : 요청 경로를 asset(실제 파일) / spa(클라이언트 라우트 → index.html) / missing(없는 자산 → 404)로 분류.
  지금까지는 파일이 없으면 무조건 index.html 200 이라 `_app/*.js` 오타·`favicon.ico` 요청에도 HTML 이 갔다.
- `cache_control_for` : `immutable, max-age=1y` 는 `_app/immutable/` 에만. `_app/version.json` 등은 `no-cache`
  (새 배포 감지 신호가 1년 캐시되던 문제 해소).
- `inline_script_hashes` : 빌드된 index.html 의 인라인 `<script>` sha256 (CSP script-src 용, mtime 캐시).
- `serve_v2_response` : 위 셋을 묶어 Flask 응답을 만든다. `app.py` 의 `serve_v2` 는 이 함수 호출만 한다.

Flask 에는 `send_from_directory` 만 의존한다(경로 이탈은 거기서 막히고, 여기서도 build_dir 밖은 파일로 보지 않는다).
"""
from __future__ import annotations

import base64
import hashlib
import re
import threading
from pathlib import Path

from flask import Response, make_response, send_from_directory

# 파일이 없을 때 '자산 요청'으로 간주해 404 를 돌려줄 확장자. 점(.)이 있다고 모두 자산으로 보지 않는다 —
# `/v2/activity/2026.10.01` 같은 딥링크 세그먼트를 지키기 위해서다.
ASSET_EXTENSIONS = (".js", ".css", ".map", ".ico", ".png", ".svg", ".webmanifest", ".json", ".woff2")

IMMUTABLE_PREFIX = "_app/immutable/"
IMMUTABLE_CACHE = "public, max-age=31536000, immutable"
REVALIDATE_CACHE = "no-cache"
MISSING_CACHE = "no-store"

# 실행되는 스크립트 타입만 해시 대상(JSON 데이터 블록 등은 CSP 대상이 아님).
_EXECUTABLE_TYPES = {"", "module", "text/javascript", "application/javascript"}
_SCRIPT_RE = re.compile(r"<script\b([^>]*)>(.*?)</script\s*>", re.DOTALL | re.IGNORECASE)
_SRC_RE = re.compile(r"\bsrc\s*=", re.IGNORECASE)
_TYPE_RE = re.compile(r"""\btype\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))""", re.IGNORECASE)

_hash_cache: dict[str, tuple[tuple[int, int], list[str]]] = {}
_hash_lock = threading.Lock()


def _inside(build_dir: Path, candidate: Path) -> bool:
    try:
        candidate.resolve().relative_to(build_dir.resolve())
    except ValueError:
        return False
    return True


def _is_asset_request(path: str) -> bool:
    return path.startswith("_app/") or path.lower().endswith(ASSET_EXTENSIONS)


def resolve_v2(build_dir: Path, path: str) -> tuple[str, Path | None]:
    """`/v2/<path>` 요청 분류. 반환 `(kind, file)`, kind ∈ {asset, spa, missing}.

    - asset  : build_dir 안의 실제 파일 → (asset, 그 파일)
    - missing: 파일이 없고 `_app/` 아래이거나 자산 확장자 → (missing, None) → 404
    - spa    : 그 밖(클라이언트 라우트) → (spa, build_dir/index.html)
    """
    if path:
        candidate = build_dir / path
        if _inside(build_dir, candidate) and candidate.is_file():
            return "asset", candidate
        if _is_asset_request(path):
            return "missing", None
    return "spa", build_dir / "index.html"


def cache_control_for(path: str) -> str:
    """응답 `Cache-Control` 값. immutable 은 `_app/immutable/` 전용, 나머지(version.json·index.html 등)는 no-cache."""
    if path.startswith(IMMUTABLE_PREFIX):
        return IMMUTABLE_CACHE
    return REVALIDATE_CACHE


def _script_attrs_executable(attrs: str) -> bool:
    if _SRC_RE.search(attrs):
        return False  # 외부 스크립트는 'self' 로 허용 — 해시 불필요
    m = _TYPE_RE.search(attrs)
    typ = (next((g for g in m.groups() if g is not None), "") if m else "").strip().lower()
    return typ in _EXECUTABLE_TYPES


def inline_script_hashes(index_path: Path) -> list[str]:
    """index.html 의 인라인 `<script>` 본문 sha256 해시 목록(`sha256-<base64>`, 따옴표 없음). 중복 제거·순서 유지.

    파일이 없거나 읽을 수 없으면 빈 목록. (mtime_ns, size) 를 키로 캐시한다.
    """
    index_path = Path(index_path)
    try:
        st = index_path.stat()
    except OSError:
        return []
    key = (st.st_mtime_ns, st.st_size)
    with _hash_lock:
        hit = _hash_cache.get(str(index_path))
        if hit and hit[0] == key:
            return list(hit[1])
    try:
        text = index_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    hashes: list[str] = []
    for attrs, body in _SCRIPT_RE.findall(text):
        if not body.strip() or not _script_attrs_executable(attrs):
            continue
        digest = base64.b64encode(hashlib.sha256(body.encode("utf-8")).digest()).decode("ascii")
        token = f"sha256-{digest}"
        if token not in hashes:
            hashes.append(token)
    with _hash_lock:
        _hash_cache[str(index_path)] = (key, hashes)
    return list(hashes)


def serve_v2_response(build_dir: Path, path: str) -> Response:
    """`/v2/<path>` 응답. 없는 자산 → 404(text/plain, no-store), 클라이언트 라우트 → index.html(no-cache)."""
    kind, file = resolve_v2(build_dir, path)
    if kind == "missing":
        resp = make_response("Not Found", 404)
        resp.headers["Content-Type"] = "text/plain; charset=utf-8"
        resp.headers["Cache-Control"] = MISSING_CACHE
        return resp
    if kind == "asset":
        resp = send_from_directory(build_dir, path)
        resp.headers["Cache-Control"] = cache_control_for(path)
        return resp
    # spa — 빌드 전이라 index.html 이 없으면 send_from_directory 가 404 를 낸다(기존 동작 유지)
    resp = send_from_directory(build_dir, "index.html")
    resp.headers["Cache-Control"] = REVALIDATE_CACHE
    return resp

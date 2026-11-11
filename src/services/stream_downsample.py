"""스트림 다운샘플(A-36 후속) — 소스별 균등 간격 추리기, 첫·끝 점 보존. 요청 시에만 적용(기본은 전체 해상도)."""
from __future__ import annotations

MIN_POINTS = 100
MAX_POINTS = 10000


def parse_max_points(raw: str | None) -> int | None:
    """`?max_points=` 해석. 없으면 None(전체), 정수가 아니거나 범위 밖이면 ValueError."""
    if raw is None or raw == "":
        return None
    if not raw.isdigit():
        raise ValueError("max_points 는 정수여야 합니다")
    n = int(raw)
    if not MIN_POINTS <= n <= MAX_POINTS:
        raise ValueError(f"max_points 는 {MIN_POINTS}~{MAX_POINTS} 사이여야 합니다")
    return n


def _pick(rows: list[dict], n: int) -> list[dict]:
    """rows 에서 첫·끝을 포함해 n 개를 균등 간격으로 고른다."""
    if len(rows) <= n:
        return rows
    step = (len(rows) - 1) / (n - 1)
    return [rows[round(i * step)] for i in range(n)]


def downsample_streams(rows: list[dict], max_points: int | None) -> tuple[list[dict], dict | None]:
    """소스별로 max_points 이하로 줄인다(소스 비율대로 배분). 반환 `(rows, info)` — 줄이지 않았으면 info None.

    rows 는 elapsed_sec 순으로 정렬돼 있다고 가정하고, 결과도 elapsed_sec 순으로 돌려준다.
    """
    if max_points is None or len(rows) <= max_points:
        return rows, None
    by_src: dict[str, list[dict]] = {}
    for r in rows:
        by_src.setdefault(r.get("source") or "", []).append(r)
    out: list[dict] = []
    for src_rows in by_src.values():
        quota = max(2, round(max_points * len(src_rows) / len(rows)))
        out.extend(_pick(src_rows, quota))
    out.sort(key=lambda r: (r.get("elapsed_sec") is None, r.get("elapsed_sec") or 0))
    return out, {"from": len(rows), "to": len(out)}

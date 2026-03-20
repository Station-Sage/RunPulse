"""웹 뷰 공통 헬퍼 함수."""
from __future__ import annotations

import html as _html
from pathlib import Path

from src.utils.config import load_config

# ── 내비게이션 링크 ────────────────────────────────────────────────────
_NAV = [
    ("/", "홈"),
    ("/db", "DB"),
    ("/wellness", "회복/웰니스"),
    ("/activity/deep", "활동 심층"),
    ("/analyze/today", "Today"),
    ("/analyze/full", "Full"),
    ("/analyze/race?date=2026-06-01&distance=42.195", "Race"),
    ("/payloads", "Payloads"),
    ("/config", "Config"),
    ("/sync-status", "Sync"),
    ("/import-preview", "Import"),
]

_CSS = """
    body { font-family: sans-serif; max-width: 980px; margin: 2rem auto; padding: 0 1rem; line-height: 1.5; }
    nav a { margin-right: 1rem; }
    pre { white-space: pre-wrap; word-break: break-word; background: #f5f5f5;
          padding: 1rem; border-radius: 8px; overflow-x: auto; }
    code { background: #f5f5f5; padding: 0.15rem 0.35rem; border-radius: 4px; }
    table { border-collapse: collapse; width: 100%; margin: 1rem 0; }
    th, td { border: 1px solid #ddd; padding: 0.5rem; text-align: left; vertical-align: top; }
    th { background: #f0f0f0; }
    .muted { color: #666; }
    .card { border: 1px solid #ddd; border-radius: 8px; padding: 1rem; margin: 1rem 0; background: #fafafa; }
    .cards-row { display: flex; flex-wrap: wrap; gap: 1rem; margin: 1rem 0; }
    .cards-row > .card { flex: 1; min-width: 210px; margin: 0; }
    .score-badge { display: inline-block; padding: 0.2rem 0.8rem;
                   border-radius: 20px; font-weight: bold; font-size: 1.05rem; }
    .grade-excellent { background: #c8f7c5; color: #1a7a17; }
    .grade-good      { background: #d4edff; color: #0056b3; }
    .grade-moderate  { background: #fff3cd; color: #856404; }
    .grade-poor      { background: #ffd6d6; color: #c0392b; }
    .grade-unknown   { background: #eee;    color: #555; }
    .mrow { display: flex; justify-content: space-between; padding: 0.25rem 0; border-bottom: 1px solid #eee; }
    .mrow:last-child { border-bottom: none; }
    .mlabel { color: #555; font-size: 0.9rem; }
    .mval   { font-weight: 500; }
    h2 { margin-top: 0; }
"""


# ── 경로 헬퍼 ───────────────────────────────────────────────────────────
def project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def db_path() -> Path:
    config = load_config()
    db_value = config.get("database", {}).get("path")
    if db_value:
        return Path(db_value).expanduser()
    return project_root() / "running.db"


# ── HTML 조립 ───────────────────────────────────────────────────────────
def html_page(title: str, body: str) -> str:
    """전체 HTML 페이지 생성 (공통 nav 포함)."""
    nav_html = " ".join(
        f'<a href="{href}">{_html.escape(label)}</a>'
        for href, label in _NAV
    )
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <title>{_html.escape(title)}</title>
  <style>{_CSS}</style>
</head>
<body>
  <nav>{nav_html}</nav>
  <hr>
  <h1>{_html.escape(title)}</h1>
  {body}
</body>
</html>"""


def make_table(headers: list[str], rows: list[tuple]) -> str:
    """HTML 테이블 생성."""
    if not rows:
        return "<p class='muted'>(데이터 없음)</p>"
    head = "".join(f"<th>{_html.escape(str(h))}</th>" for h in headers)
    body_rows = [
        "<tr>" + "".join(f"<td>{_html.escape(str(v))}</td>" for v in row) + "</tr>"
        for row in rows
    ]
    return (
        f"<table><thead><tr>{head}</tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody></table>"
    )


def metric_row(label: str, value, unit: str = "") -> str:
    """라벨-값 한 줄 렌더링."""
    v = "—" if value is None else f"{value}{unit}"
    return (
        f"<div class='mrow'>"
        f"<span class='mlabel'>{_html.escape(label)}</span>"
        f"<span class='mval'>{_html.escape(str(v))}</span>"
        f"</div>"
    )


def score_badge(grade: str | None, score) -> str:
    """점수 + 등급 배지 HTML."""
    grade_class = {
        "excellent": "grade-excellent",
        "good": "grade-good",
        "moderate": "grade-moderate",
        "poor": "grade-poor",
    }.get(grade or "", "grade-unknown")
    score_text = "—" if score is None else str(score)
    grade_kor = {
        "excellent": "최상", "good": "좋음", "moderate": "보통", "poor": "부족"
    }.get(grade or "", grade or "—")
    return (
        f"<span class='score-badge {grade_class}'>"
        f"{_html.escape(score_text)} ({_html.escape(grade_kor)})"
        f"</span>"
    )


def readiness_badge(score) -> str:
    """훈련 준비도 점수 배지 (0-100)."""
    if score is None:
        return "<span class='score-badge grade-unknown'>— (데이터 없음)</span>"
    s = float(score)
    if s >= 70:
        cls, label = "grade-excellent", "준비 완료"
    elif s >= 50:
        cls, label = "grade-good", "양호"
    elif s >= 30:
        cls, label = "grade-moderate", "보통"
    else:
        cls, label = "grade-poor", "회복 필요"
    return (
        f"<span class='score-badge {cls}'>"
        f"{_html.escape(str(score))} ({_html.escape(label)})"
        f"</span>"
    )


def fmt_min(seconds) -> str:
    """초 → 분(시간) 형식 문자열."""
    if seconds is None:
        return "—"
    try:
        m = int(seconds) // 60
        h, rem = divmod(m, 60)
        return f"{h}h {rem}m" if h else f"{m}분"
    except Exception:
        return str(seconds)


def fmt_duration(seconds) -> str:
    """초 → h m s 형식 문자열."""
    if seconds is None:
        return "—"
    try:
        total = int(seconds)
        h, rem = divmod(total, 3600)
        m, s = divmod(rem, 60)
        if h:
            return f"{h}h {m}m {s}s"
        if m:
            return f"{m}m {s}s"
        return f"{s}s"
    except Exception:
        return str(seconds)


def safe_str(value, default: str = "—") -> str:
    return default if value is None else str(value)

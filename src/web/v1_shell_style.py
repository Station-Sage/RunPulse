"""남은 v1 화면(Garmin 연동 `/connect/garmin*`)의 `base.html` 스타일시트 — Jinja context `stylesheet`.

구 `src/web/helpers.py`(HTML 조립·포맷터·하단 nav·동기화 JS·SVG 재노출)에서 `_CSS` 만 남겼다(S4-91, ADR-056).
나머지는 마지막 소비자(routes_v1_pages·v1 동기화 UI)와 함께 삭제. Garmin v1 화면 퇴역 시 함께 삭제한다.
"""
from __future__ import annotations

_CSS = """
    /* ── RunPulse v0.2 다크 테마 (ui-spec.md 기준) ── */
    :root {
        --bg: #1a1a2e; --bg2: #16213e; --bg3: #0f3460;
        --fg: #fff;
        --secondary: rgba(255,255,255,0.7);
        --muted: rgba(255,255,255,0.5);
        --card-bg: rgba(255,255,255,0.05);
        --card-border: rgba(255,255,255,0.1);
        --pre-bg: rgba(255,255,255,0.05);
        --th-bg: rgba(255,255,255,0.08);
        --row-border: rgba(255,255,255,0.08);
        --label-color: rgba(255,255,255,0.6);
        --nav-bg: rgba(26,26,46,0.95);
        --nav-border: rgba(255,255,255,0.1);
        --nav-hover: rgba(255,255,255,0.08);
        --cyan: #00d4ff;
        --green: #00ff88;
        --orange: #ffaa00;
        --red: #ff4444;
    }
    * { box-sizing: border-box; }
    body {
        font-family: 'Noto Sans KR', 'Inter', -apple-system, sans-serif;
        margin: 0; padding: 0; line-height: 1.5;
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        background-color: #1a1a2e; 
        background-attachment: fixed;
        color: var(--fg); min-height: 100vh;
        overflow-x: hidden;
    }
    html { overflow-x: hidden; }
    a { color: var(--cyan); text-decoration: none; }
    a:visited { color: var(--cyan); opacity: 0.85; }
    a:hover { text-decoration: underline; opacity: 1; }
    /* ── 스티키 헤더 ── */
    header {
        position: sticky; top: 0; z-index: 200;
        background: var(--nav-bg); backdrop-filter: blur(10px);
        border-bottom: 1px solid var(--nav-border);
        padding: 0.4rem 1rem; display: flex; align-items: center;
    }
    header .brand {
        font-weight: bold; font-size: 1rem;
        text-decoration: none; color: var(--cyan);
    }
    /* ── 콘텐츠 ── */
    main { max-width: 980px; margin: 0 auto; padding: 1.5rem 1rem calc(6rem + env(safe-area-inset-bottom, 0px)); }
    pre { white-space: pre-wrap; word-break: break-word;
          background: var(--pre-bg); padding: 1rem; border-radius: 8px;
          overflow-x: auto; border: 1px solid var(--card-border);
          color: var(--secondary); }
    code { background: var(--pre-bg); padding: 0.15rem 0.35rem;
           border-radius: 4px; color: var(--cyan); font-size: 0.9em; }
    table { border-collapse: collapse; width: 100%; margin: 1rem 0; }
    th, td { border: 1px solid var(--card-border); padding: 0.5rem;
             text-align: left; vertical-align: top; }
    th { background: var(--th-bg); color: var(--secondary); }
    .muted { color: var(--muted); }
    /* ── 툴팁 (터치/호버) ── */
    .rp-tip { position: relative; cursor: help; border-bottom: 1px dotted rgba(255,255,255,0.3); }
    .rp-tip .rp-tip-text {
        visibility: hidden; opacity: 0;
        position: absolute; z-index: 100; bottom: 125%; left: 50%;
        transform: translateX(-50%);
        background: rgba(22,33,62,0.95); color: rgba(255,255,255,0.9);
        border: 1px solid var(--card-border); border-radius: 12px;
        padding: 10px 14px; font-size: 0.78rem; line-height: 1.5;
        width: max-content; max-width: 250px;
        pointer-events: none; transition: opacity 0.2s;
        box-shadow: 0 4px 12px rgba(0,0,0,0.4);
        word-break: keep-all; overflow-wrap: break-word;
    }
    @media (max-width: 640px) {
        .rp-tip .rp-tip-text {
            position: fixed; left: 8px; right: 8px; bottom: auto; top: 50%;
            transform: translateY(-50%); max-width: none; width: auto;
        }
    }
    .rp-tip:hover .rp-tip-text,
    .rp-tip:focus .rp-tip-text,
    .rp-tip.active .rp-tip-text { visibility: visible; opacity: 1; pointer-events: auto; }
    .card { border: 1px solid var(--card-border); border-radius: 20px;
            padding: 1.2rem; margin: 1rem 0;
            background: var(--card-bg); backdrop-filter: blur(10px); }
    .card:hover { transform: translateY(-2px); transition: transform 0.2s; }
    .cards-row { display: flex; flex-wrap: wrap; gap: 1rem; margin: 1rem 0; }
    .cards-row > .card { flex: 1; min-width: 210px; margin: 0; }
    .score-badge { display: inline-block; padding: 0.2rem 0.8rem;
                   border-radius: 20px; font-weight: bold; font-size: 1.05rem; }
    .grade-excellent { background: rgba(0,255,136,0.15); color: var(--green);
                       border: 1px solid rgba(0,255,136,0.3); }
    .grade-good      { background: rgba(0,212,255,0.15); color: var(--cyan);
                       border: 1px solid rgba(0,212,255,0.3); }
    .grade-moderate  { background: rgba(255,170,0,0.15);  color: var(--orange);
                       border: 1px solid rgba(255,170,0,0.3); }
    .grade-poor      { background: rgba(255,68,68,0.15);   color: var(--red);
                       border: 1px solid rgba(255,68,68,0.3); }
    .grade-unknown   { background: rgba(255,255,255,0.05); color: var(--muted);
                       border: 1px solid var(--card-border); }
    .mrow { display: flex; justify-content: space-between; padding: 0.25rem 0;
            border-bottom: 1px solid var(--row-border); }
    .mrow:last-child { border-bottom: none; }
    .mlabel { color: var(--label-color); font-size: 0.9rem; }
    .mval   { font-weight: 500; color: var(--secondary); }
    h1 { margin-top: 0; font-size: 1.4rem; color: var(--fg); }
    h2 { margin-top: 0; font-size: 1.1rem; color: var(--secondary); }
    h3 { color: var(--secondary); }
    input, select, textarea {
        font-family: inherit;
        background: rgba(255,255,255,0.08); color: var(--fg);
        border: 1px solid var(--card-border); border-radius: 6px;
        padding: 0.4rem 0.7rem;
    }
    select option {
        background: #1a2035; color: var(--fg);
    }
    button {
        font-family: inherit; cursor: pointer;
        background: rgba(255,255,255,0.1); color: var(--fg);
        border: 1px solid var(--card-border); border-radius: 6px;
        padding: 0.4rem 0.8rem;
    }
    button:hover { background: rgba(255,255,255,0.18); }
    input:focus, select:focus, textarea:focus { outline: 2px solid var(--cyan); }
    label { color: var(--secondary); }
    .section-title {
        font-size: 1rem; font-weight: 600; color: var(--secondary);
        margin: 1.5rem 0 0.5rem; padding-left: 0.8rem;
        border-left: 4px solid var(--cyan);
    }
    /* ── 하단 7탭 네비게이션 ── */
    .bottom-nav {
        position: fixed; bottom: 0; left: 0; right: 0; z-index: 1000;
        background: rgba(26,26,46,0.98); backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border-top: 1px solid rgba(255,255,255,0.1);
        padding: 4px 0 calc(4px + env(safe-area-inset-bottom, 0px));
        padding-bottom: max(8px, env(safe-area-inset-bottom, 8px));
    }
    .nav-items {
    margin: 0 auto; display: flex;
    justify-content: space-around; padding: 0 4px;
    width: 100%;
    }
    .nav-item-tab {
        display: flex; flex-direction: column; align-items: center;
        padding: 6px 8px; text-decoration: none;
        color: var(--muted); min-width: 44px;
        border-radius: 8px; transition: color 0.2s;
    }
    .nav-item-tab:hover { color: var(--secondary); text-decoration: none; }
    .nav-item-tab.active { color: var(--cyan); }
    .nav-item-icon { font-size: 18px; line-height: 1; margin-bottom: 2px; }
    .nav-item-label { font-size: 10px; white-space: nowrap; }
    /* ── 모바일 반응형 ── */
    @media (max-width: 640px) {
        main { padding: 1rem 0.5rem calc(6rem + env(safe-area-inset-bottom, 0px)); }
        .cards-row { flex-direction: column; }
        .cards-row > .card { min-width: unset; }
        table { font-size: 0.85rem; }
        th, td { padding: 0.3rem; }
        pre { font-size: 0.85rem; }
        h1 { font-size: 1.2rem; }
        .nav-item > a, .nav-item > span { padding: 0.45rem 0.5rem; font-size: 0.82rem; }
        .nav-item-tab { padding: 5px 4px; min-width: 36px; }
    }
"""

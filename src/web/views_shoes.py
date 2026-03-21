"""신발 목록 뷰 — Flask Blueprint.

/shoes
  - Strava export shoes.csv에서 임포트된 신발 목록
"""
from __future__ import annotations

import html
import sqlite3

from flask import Blueprint

from .helpers import db_path, html_page

shoes_bp = Blueprint("shoes", __name__)


@shoes_bp.get("/shoes")
def shoes_list():
    """신발 목록 페이지."""
    dpath = db_path()

    # shoes 테이블 없거나 DB 없는 경우 처리
    if not dpath.exists():
        body = "<div class='card'><p>running.db 가 없습니다. DB를 먼저 초기화하세요.</p></div>"
        return html_page("신발 목록", body)

    try:
        with sqlite3.connect(str(dpath)) as conn:
            rows = conn.execute(
                "SELECT id, source, brand, model, name, default_sport_types, created_at "
                "FROM shoes ORDER BY brand, model"
            ).fetchall()
    except sqlite3.OperationalError:
        body = (
            "<div class='card'>"
            "<p class='muted'>shoes 테이블이 없습니다. "
            "<a href='/import-export'>임포트 페이지</a>에서 Strava 데이터를 먼저 적재하세요.</p>"
            "</div>"
        )
        return html_page("신발 목록", body)
    except Exception as exc:
        body = f"<div class='card'><p>조회 오류: {html.escape(str(exc))}</p></div>"
        return html_page("신발 목록", body)

    if not rows:
        body = (
            "<div class='card'>"
            "<p class='muted'>등록된 신발이 없습니다. "
            "<a href='/import-export'>임포트 페이지</a>에서 Strava export 데이터를 적재하세요.</p>"
            "</div>"
        )
        return html_page("신발 목록", body)

    headers = ["브랜드", "모델", "이름", "기본 스포츠", "소스", "등록일"]
    head = "".join(f"<th>{html.escape(h)}</th>" for h in headers)
    body_rows = []
    for row in rows:
        _, source, brand, model, name, sport, created_at = row
        date_str = str(created_at)[:10] if created_at else "—"
        body_rows.append(
            "<tr>"
            f"<td>{html.escape(brand or '—')}</td>"
            f"<td><strong>{html.escape(model or '—')}</strong></td>"
            f"<td>{html.escape(name or '—')}</td>"
            f"<td>{html.escape(sport or '—')}</td>"
            f"<td>{html.escape(source or '—')}</td>"
            f"<td>{html.escape(date_str)}</td>"
            "</tr>"
        )

    table = (
        f"<table><thead><tr>{head}</tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody></table>"
    )

    body = (
        "<div class='card'>"
        f"<h2>신발 목록 ({len(rows)}켤레)</h2>"
        + table
        + "<p class='muted' style='margin-top:0.5rem;'>Strava export shoes.csv 기준. "
        "향후 활동·훈련 분석과 연계 예정.</p>"
        "</div>"
    )
    return html_page("신발 목록", body)

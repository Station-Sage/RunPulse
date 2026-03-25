"""Export 데이터 임포트 뷰 — Flask Blueprint.

/import-export
  - Garmin export CSV 폴더 지정 → DB 적재
  - Strava export 폴더 지정 → activities.csv + shoes.csv 적재
  - intervals.icu export FIT 폴더 지정 → DB 적재
  - 임포트 결과 표시
"""
from __future__ import annotations

import html
import sqlite3
from pathlib import Path

from flask import Blueprint, request

from .helpers import db_path, html_page


def _import_garmin_folder(*args, **kwargs):
    from src.import_export.garmin_csv import import_garmin_folder
    return import_garmin_folder(*args, **kwargs)


def _import_strava_folder(*args, **kwargs):
    from src.import_export.strava_csv import import_strava_folder
    return import_strava_folder(*args, **kwargs)


def _import_intervals_folder(*args, **kwargs):
    from src.import_export.intervals_fit import import_intervals_folder
    return import_intervals_folder(*args, **kwargs)

export_import_bp = Blueprint("export_import", __name__)

# 기본 폴더 경로 (프로젝트 루트 기준)
_DEFAULT_GARMIN_FOLDER = Path(__file__).resolve().parent.parent.parent / "activities data" / "garmin"
_DEFAULT_STRAVA_FOLDER = Path(__file__).resolve().parent.parent.parent / "activities data" / "strava"
_DEFAULT_INTERVALS_FOLDER = Path(__file__).resolve().parent.parent.parent / "activities data" / "intervals.icu"


def _render_form(
    garmin_folder: str,
    strava_folder: str,
    intervals_folder: str,
    result: dict | None = None,
    error: str = "",
) -> str:
    result_html = ""
    if error:
        result_html = f"<div class='card'><p style='color:red;'>{html.escape(error)}</p></div>"
    elif result:
        result_html = _render_result(result)

    return (
        "<div class='card'>"
        "<h2>Export 데이터 임포트</h2>"
        "<p class='muted'>Garmin / Strava / intervals.icu 에서 내보낸 파일을 DB에 적재합니다.</p>"
        "<form method='post' action='/import-export'>"
        "<table style='width:100%; border-collapse:collapse;'>"
        "<tr>"
        "<td style='padding:0.5rem; width:130px;'><label>Garmin 폴더</label></td>"
        "<td style='padding:0.5rem;'>"
        f"<input type='text' name='garmin_folder' value='{html.escape(garmin_folder)}' "
        "style='width:100%; font-size:0.85rem;'>"
        "</td>"
        "</tr>"
        "<tr>"
        "<td style='padding:0.5rem;'><label>Strava 폴더</label></td>"
        "<td style='padding:0.5rem;'>"
        f"<input type='text' name='strava_folder' value='{html.escape(strava_folder)}' "
        "style='width:100%; font-size:0.85rem;'>"
        "</td>"
        "</tr>"
        "<tr>"
        "<td style='padding:0.5rem;'><label>intervals.icu 폴더</label></td>"
        "<td style='padding:0.5rem;'>"
        f"<input type='text' name='intervals_folder' value='{html.escape(intervals_folder)}' "
        "style='width:100%; font-size:0.85rem;'>"
        "</td>"
        "</tr>"
        "</table>"
        "<div style='margin-top:0.8rem; display:flex; gap:0.8rem; flex-wrap:wrap;'>"
        "<button type='submit' name='target' value='garmin'>Garmin 임포트</button>"
        "<button type='submit' name='target' value='strava'>Strava 임포트</button>"
        "<button type='submit' name='target' value='intervals'>intervals.icu 임포트</button>"
        "<button type='submit' name='target' value='all'>전체 임포트</button>"
        "</div>"
        "</form>"
        "</div>"
        + result_html
    )


def _render_result(result: dict) -> str:
    parts = ["<div class='card'><h2>임포트 결과</h2>"]

    # Garmin 결과
    if "garmin" in result:
        g = result["garmin"]
        parts.append("<h3>Garmin</h3>")
        if "error" in g:
            parts.append(f"<p style='color:red;'>{html.escape(g['error'])}</p>")
        else:
            total = g.get("total", {})
            parts.append(
                f"<p>파일 {len(g.get('files', []))}개 처리 | "
                f"신규 <strong>{total.get('inserted', 0)}</strong>건 | "
                f"중복 {total.get('skipped', 0)}건 | "
                f"오류 {total.get('errors', 0)}건</p>"
            )
            if g.get("files"):
                rows = "".join(
                    f"<tr><td>{html.escape(f['file'])}</td>"
                    f"<td>+{f['inserted']}</td>"
                    f"<td>{f['skipped']}</td>"
                    f"<td>{f['errors']}</td></tr>"
                    for f in g["files"]
                )
                parts.append(
                    "<table><thead><tr>"
                    "<th>파일</th><th>신규</th><th>중복</th><th>오류</th>"
                    "</tr></thead>"
                    f"<tbody>{rows}</tbody></table>"
                )

    # Strava 결과
    if "strava" in result:
        s = result["strava"]
        parts.append("<h3 style='margin-top:1rem;'>Strava</h3>")

        acts = s.get("activities", {})
        if "error" in acts:
            parts.append(f"<p style='color:red;'>{html.escape(acts['error'])}</p>")
        else:
            parts.append(
                f"<p>activities.csv: 신규 <strong>{acts.get('inserted', 0)}</strong>건 | "
                f"중복 {acts.get('skipped', 0)}건 | "
                f"오류 {acts.get('errors', 0)}건</p>"
            )

        shoes = s.get("shoes", {})
        if "error" in shoes:
            parts.append(f"<p style='color:orange;'>{html.escape(shoes['error'])}</p>")
        else:
            parts.append(
                f"<p>shoes.csv: 신규 <strong>{shoes.get('inserted', 0)}</strong>건 | "
                f"중복 {shoes.get('skipped', 0)}건</p>"
            )

    # intervals.icu 결과
    if "intervals" in result:
        iv = result["intervals"]
        parts.append("<h3 style='margin-top:1rem;'>intervals.icu</h3>")
        if "error" in iv:
            parts.append(f"<p style='color:red;'>{html.escape(iv['error'])}</p>")
        else:
            total = iv.get("total", {})
            parts.append(
                f"<p>파일 {len(iv.get('files', []))}개 처리 | "
                f"신규 <strong>{total.get('inserted', 0)}</strong>건 | "
                f"중복 {total.get('skipped', 0)}건 | "
                f"오류 {total.get('errors', 0)}건</p>"
            )

    parts.append("</div>")
    return "".join(parts)


@export_import_bp.get("/import-export")
def export_import_page():
    """임포트 폼 페이지."""
    body = _render_form(
        str(_DEFAULT_GARMIN_FOLDER),
        str(_DEFAULT_STRAVA_FOLDER),
        str(_DEFAULT_INTERVALS_FOLDER),
    )
    return html_page("Export 데이터 임포트", body)


@export_import_bp.post("/import-export")
def export_import_run():
    """임포트 실행."""
    garmin_folder_str = request.form.get("garmin_folder", "").strip()
    strava_folder_str = request.form.get("strava_folder", "").strip()
    intervals_folder_str = request.form.get("intervals_folder", "").strip()
    target = request.form.get("target", "all")

    garmin_folder = Path(garmin_folder_str) if garmin_folder_str else _DEFAULT_GARMIN_FOLDER
    strava_folder = Path(strava_folder_str) if strava_folder_str else _DEFAULT_STRAVA_FOLDER
    intervals_folder = Path(intervals_folder_str) if intervals_folder_str else _DEFAULT_INTERVALS_FOLDER

    dpath = db_path()
    if not dpath.exists():
        body = _render_form(
            str(garmin_folder), str(strava_folder), str(intervals_folder),
            error="running.db 가 없습니다. DB를 먼저 초기화하세요.",
        )
        return html_page("Export 데이터 임포트", body)

    result: dict = {}
    try:
        with sqlite3.connect(str(dpath)) as conn:
            if target in ("garmin", "all"):
                if garmin_folder.is_dir():
                    result["garmin"] = _import_garmin_folder(conn, garmin_folder)
                else:
                    result["garmin"] = {"error": f"폴더 없음: {garmin_folder}"}

            if target in ("strava", "all"):
                if strava_folder.is_dir():
                    result["strava"] = _import_strava_folder(conn, strava_folder)
                else:
                    result["strava"] = {"error": f"폴더 없음: {strava_folder}"}

            if target in ("intervals", "all"):
                if intervals_folder.is_dir():
                    result["intervals"] = _import_intervals_folder(conn, intervals_folder)
                else:
                    result["intervals"] = {"error": f"폴더 없음: {intervals_folder}"}

    except Exception as exc:
        body = _render_form(
            str(garmin_folder), str(strava_folder), str(intervals_folder),
            error=f"임포트 오류: {exc}",
        )
        return html_page("Export 데이터 임포트", body)

    body = _render_form(
        str(garmin_folder), str(strava_folder), str(intervals_folder),
        result=result,
    )
    return html_page("Export 데이터 임포트", body)

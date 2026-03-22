"""RunPulse integration workbench web app."""

from __future__ import annotations

import html
import sqlite3
import sys
import time
from collections import Counter
from pathlib import Path

from flask import Flask, redirect, request

from src.analysis import generate_report
from src.utils.config import load_config, redact_config_for_display
from src.sync.garmin import check_garmin_connection
from src.sync.strava import check_strava_connection
from src.sync.intervals import check_intervals_connection
from src.sync.runalyze import check_runalyze_connection

# Phase 5 Blueprint imports
from .views_wellness import wellness_bp
from .views_activity import activity_bp
from .views_activities import activities_bp
from .views_settings import settings_bp
from .views_activity_merge import merge_bp
from .views_export_import import export_import_bp
from .views_shoes import shoes_bp

# Phase 3 (v0.2) Blueprint imports
from .views_dashboard import dashboard_bp


# ── 홈 화면 TTL 캐시 (60초) ─────────────────────────────────────────────────
_HOME_CACHE_TTL = 60
# db_path 문자열 → {"ts": float, "data": dict} 맵
_home_cache: dict[str, dict] = {}


def _get_home_data(db_path: Path) -> dict:
    """TTL 캐시로 홈 화면 분석 데이터 반환. 캐시 유효 시 재계산 생략.

    db_path별로 독립 캐시 항목을 유지하므로 다른 DB 간 오염 없음.
    """
    cache_key = str(db_path)
    now = time.monotonic()
    entry = _home_cache.get(cache_key)
    if entry and now - entry["ts"] < _HOME_CACHE_TTL:
        return entry["data"]

    from src.analysis.recovery import get_recovery_status
    from src.analysis.weekly_score import calculate_weekly_score
    from src.services.unified_activities import fetch_unified_activities
    from datetime import date as _date

    today = _date.today().isoformat()
    with sqlite3.connect(str(db_path)) as conn:
        recovery = get_recovery_status(conn, today)
        try:
            weekly = calculate_weekly_score(conn)
        except Exception:
            weekly = None
        recent_unified, _, _ = fetch_unified_activities(conn, page=1, page_size=5)

    data = {"recovery": recovery, "weekly": weekly, "recent_rows": recent_unified}
    _home_cache[cache_key] = {"ts": now, "data": data}
    return data


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _db_path() -> Path:
    config = load_config()
    db_value = config.get("database", {}).get("path")
    if db_value:
        return Path(db_value).expanduser()
    return _project_root() / "running.db"


def _html_page(title: str, body: str) -> str:
    """helpers.html_page 위임 — CSS/nav 중복 제거."""
    from .helpers import html_page as _hp
    return _hp(title, body)


def _already_finished(stdout: str) -> bool:
    """sync.py 내부에서 mark_finished를 이미 호출했는지 stdout으로 추정."""
    # strava/garmin sync 함수가 rate limit 발생 시 직접 mark_finished 호출
    return "⚠️" in stdout and ("제한" in stdout or "타임아웃" in stdout)


def _days_since_last_sync(sources: list[str]) -> int:
    """DB에서 마지막 활동 이후 일수 계산. 데이터 없으면 7 반환."""
    from datetime import date
    db = _db_path()
    if not db.exists():
        return 7
    try:
        with sqlite3.connect(str(db)) as conn:
            placeholders = ",".join("?" * len(sources))
            row = conn.execute(
                f"SELECT MAX(start_time) FROM activity_summaries WHERE source IN ({placeholders})",
                sources,
            ).fetchone()
        if not row or not row[0]:
            return 7
        last_date = date.fromisoformat(str(row[0])[:10])
        return max(1, min((date.today() - last_date).days + 2, 365))
    except Exception:
        return 7


def _query_rows(conn: sqlite3.Connection, sql: str) -> list[tuple]:
    return conn.execute(sql).fetchall()


def _query_value(conn: sqlite3.Connection, sql: str) -> int:
    row = conn.execute(sql).fetchone()
    return int(row[0]) if row and row[0] is not None else 0


def _table(headers: list[str], rows: list[tuple]) -> str:
    if not rows:
        return "<p class='muted'>(no rows)</p>"
    head = "".join(f"<th>{html.escape(h)}</th>" for h in headers)
    body_rows = []
    for row in rows:
        cols = "".join(f"<td>{html.escape(str(v))}</td>" for v in row)
        body_rows.append(f"<tr>{cols}</tr>")
    body = "".join(body_rows)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def _payload_recent_table(rows: list[tuple]) -> str:
    if not rows:
        return "<p class='muted'>(no rows)</p>"

    headers = ["id", "source", "entity_type", "entity_id", "activity_id", "payload_len", "updated_at", "view"]
    head = "".join(f"<th>{html.escape(h)}</th>" for h in headers)

    body_rows = []
    for row in rows:
        payload_id, source, entity_type, entity_id, activity_id, payload_len, updated_at = row
        view_html = f"<a href='/payloads/view?id={payload_id}'>open</a>"
        cols = "".join(
            [
                f"<td>{html.escape(str(payload_id))}</td>",
                f"<td>{html.escape(str(source))}</td>",
                f"<td>{html.escape(str(entity_type))}</td>",
                f"<td>{html.escape(str(entity_id))}</td>",
                f"<td>{html.escape(str(activity_id))}</td>",
                f"<td>{html.escape(str(payload_len))}</td>",
                f"<td>{html.escape(str(updated_at))}</td>",
                f"<td>{view_html}</td>",
            ]
        )
        body_rows.append(f"<tr>{cols}</tr>")

    body = "".join(body_rows)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def _bool_text(value: bool) -> str:
    return "yes" if value else "no"


def _to_int(value, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _json_pretty_block(value) -> str:
    import json

    try:
        if isinstance(value, str):
            parsed = json.loads(value)
        else:
            parsed = value
        pretty = json.dumps(parsed, ensure_ascii=False, indent=2, sort_keys=True)
    except Exception:
        pretty = str(value)
    return f"<pre>{html.escape(pretty)}</pre>"


def _scan_history_dir(base_dir: Path) -> dict:
    _SUPPORTED = {".fit", ".gpx", ".tcx", ".fit.gz", ".gpx.gz", ".tcx.gz"}
    if not base_dir.exists():
        return {
            "exists": False,
            "base_dir": str(base_dir),
            "total_files": 0,
            "by_ext": [],
            "sample_files": [],
        }

    files = [
        p for p in base_dir.rglob("*")
        if p.is_file() and any(
            "".join(p.suffixes).lower().endswith(ext) for ext in _SUPPORTED
        )
    ]
    # 복합 확장자(.fit.gz) 포함 집계
    def _ext(p: Path) -> str:
        s = "".join(p.suffixes).lower()
        for ext in (".fit.gz", ".gpx.gz", ".tcx.gz"):
            if s.endswith(ext):
                return ext
        return p.suffix.lower()

    counts = Counter(_ext(p) for p in files)
    samples = [str(p.relative_to(_project_root())) for p in sorted(files)[:20]]

    return {
        "exists": True,
        "base_dir": str(base_dir),
        "total_files": len(files),
        "by_ext": sorted(counts.items()),
        "sample_files": samples,
    }


def _auto_migrate() -> None:
    """앱 시작 시 기존 DB에 v0.2 신규 테이블 자동 마이그레이션."""
    db = _db_path()
    if not db.exists():
        return
    try:
        from src.db_setup import migrate_db
        with sqlite3.connect(str(db)) as conn:
            migrate_db(conn)
    except Exception:
        pass  # 마이그레이션 실패해도 앱 기동은 계속


def create_app() -> Flask:
    app = Flask(__name__)
    _auto_migrate()

    @app.get("/")
    def index():
        return redirect("/dashboard")

    @app.get("/home-legacy")
    def index_legacy():
        db_path = _db_path()

        if not db_path.exists():
            body = f"""
            <p>RunPulse 대시보드 — DB 미초기화 상태입니다.</p>
            <div class="card">
              <h2>시작 방법</h2>
              <ol>
                <li><code>python src/db_setup.py</code> 로 DB 생성</li>
                <li><code>python src/sync.py --source all --days 7</code> 로 데이터 동기화</li>
                <li>이 페이지를 새로고침하면 대시보드가 표시됩니다.</li>
              </ol>
            </div>
            <p class="muted">DB path: {html.escape(str(db_path))}</p>
            """
            return _html_page("RunPulse 대시보드", body)

        # ── 대시보드 데이터 수집 (TTL 캐시 60초) ───────────────────────
        recovery_card_html = ""
        weekly_card_html = ""
        recent_acts_html = ""

        try:
            home_data = _get_home_data(db_path)
            recovery = home_data["recovery"]
            weekly = home_data["weekly"]
            recent_rows = home_data["recent_rows"]

        except Exception as exc:
            body = (
                f"<div class='card'><p>대시보드 로드 오류: {html.escape(str(exc))}</p></div>"
                f"<p class='muted'>DB path: {html.escape(str(db_path))}</p>"
            )
            return _html_page("RunPulse 대시보드", body)

        # ── 회복 카드 ────────────────────────────────────────────────
        if recovery.get("available"):
            detail = recovery.get("detail") or {}
            readiness = detail.get("training_readiness_score")
            score = recovery.get("recovery_score")
            grade = recovery.get("grade")
            grade_kor = {"excellent": "최상", "good": "좋음", "moderate": "보통", "poor": "부족"}.get(grade or "", "—")

            def _rbadge(val, lo, mid, hi):
                if val is None:
                    return "<span class='score-badge grade-unknown'>—</span>"
                v = float(val)
                if v >= hi:
                    cls = "grade-excellent"
                elif v >= mid:
                    cls = "grade-good"
                elif v >= lo:
                    cls = "grade-moderate"
                else:
                    cls = "grade-poor"
                return f"<span class='score-badge {cls}'>{html.escape(str(val))}</span>"

            readiness_badge = _rbadge(readiness, 30, 50, 70)
            recovery_badge = (
                f"<span class='score-badge grade-{html.escape(grade or 'unknown')}'>"
                f"{html.escape(str(score) if score is not None else '—')} ({html.escape(grade_kor)})</span>"
            )
            raw = recovery.get("raw") or {}

            recovery_card_html = f"""
            <div class="card">
              <h2>오늘 회복 상태 <a href="/wellness" style="font-size:0.8rem; font-weight:normal;">상세 &rarr;</a></h2>
              <p><strong>훈련 준비도:</strong> {readiness_badge}
                 &nbsp; <strong>회복 점수:</strong> {recovery_badge}</p>
              <div style="display:flex; gap:2rem; flex-wrap:wrap; margin-top:0.5rem;">
                <span>바디 배터리: <strong>{html.escape(str(raw.get("body_battery") or "—"))}</strong></span>
                <span>수면 점수: <strong>{html.escape(str(raw.get("sleep_score") or "—"))}</strong></span>
                <span>HRV: <strong>{html.escape(str(raw.get("hrv_value") or "—"))} ms</strong></span>
                <span>SpO2: <strong>{html.escape(str(detail.get("spo2_avg") or "—"))}%</strong></span>
              </div>
            </div>
            """
        else:
            recovery_card_html = f"""
            <div class="card">
              <h2>오늘 회복 상태 <a href="/wellness" style="font-size:0.8rem; font-weight:normal;">상세 &rarr;</a></h2>
              <p class="muted">오늘 Garmin 웰니스 데이터가 없습니다.
                <code>python src/sync.py --source garmin --days 1</code></p>
            </div>
            """

        # ── 주간 점수 카드 ────────────────────────────────────────────
        if weekly:
            w_score = weekly.get("total_score")
            w_grade = weekly.get("grade") or "—"
            w_data = weekly.get("data") or {}
            weekly_card_html = f"""
            <div class="card">
              <h2>이번 주 훈련 점수 <a href="/analyze/today" style="font-size:0.8rem; font-weight:normal;">리포트 &rarr;</a></h2>
              <p style="font-size:1.4rem; margin:0.3rem 0;">
                <strong>{html.escape(str(w_score) if w_score is not None else "—")}</strong>
                <span style="font-size:1rem; color:#666;">/ 100 ({html.escape(str(w_grade))})</span>
              </p>
              <div style="display:flex; gap:2rem; flex-wrap:wrap; margin-top:0.5rem;">
                <span>거리: <strong>{html.escape(str(w_data.get("total_distance_km") or "—"))} km</strong></span>
                <span>런 횟수: <strong>{html.escape(str(w_data.get("run_count") or "—"))}</strong></span>
              </div>
            </div>
            """
        else:
            weekly_card_html = """
            <div class="card">
              <h2>이번 주 훈련 점수</h2>
              <p class="muted">데이터 부족</p>
            </div>
            """

        # ── 최근 활동 카드 ────────────────────────────────────────────
        if recent_rows:
            from src.web.views_activities import _render_activity_table
            act_table_html = _render_activity_table(recent_rows)
            _toggle_js = (
                "<script>"
                "function uaToggle(gid){"
                "var sub=document.getElementById('sub-'+gid);"
                "var btn=document.getElementById('btn-'+gid);"
                "if(!sub)return;"
                "var opening=sub.style.display==='none';"
                "sub.style.display=opening?'':'none';"
                "if(btn){var ico=btn.querySelector('.expand-icon');"
                "if(ico)ico.textContent=opening?'▼':'▶';"
                "btn.style.background=opening?'rgba(0,85,179,0.08)':'';}}"
                "</script>"
            )
            recent_acts_html = f"""
            <div class="card">
              <h2>최근 활동 <a href="/activities" style="font-size:0.8rem; font-weight:normal;">전체 &rarr;</a></h2>
              {act_table_html}
              {_toggle_js}
            </div>
            """
        else:
            recent_acts_html = """
            <div class="card">
              <h2>최근 활동</h2>
              <p class="muted">활동 데이터가 없습니다.</p>
            </div>
            """

        from .sync_ui import sync_card_html
        from .helpers import last_sync_info, connected_services
        from src.utils.sync_state import get_all_states
        sync_card = sync_card_html(
            last_sync=last_sync_info(["garmin", "strava", "intervals", "runalyze"]),
            sync_states=get_all_states(),
            connected=connected_services(),
        )

        body = f"""
        {sync_card}
        <div class="cards-row">
          {recovery_card_html}
          {weekly_card_html}
        </div>
        {recent_acts_html}
        <p class="muted">DB: {html.escape(str(db_path))}</p>
        """
        return _html_page("RunPulse 대시보드", body)

    @app.get("/config")
    def config_summary():
        """설정 현황 + 각 서비스별 직접 수정 링크 제공."""
        import json as _json
        config = load_config()
        db_path = _db_path()
        redacted = redact_config_for_display(config)

        garmin_status = check_garmin_connection(config)
        strava_status = check_strava_connection(config)
        intervals_status = check_intervals_connection(config)
        runalyze_status = check_runalyze_connection(config)

        def _svc_card(name: str, href: str, status: dict) -> str:
            ok = status["ok"]
            badge_cls = "grade-good" if ok else "grade-poor"
            badge_txt = html.escape(status["status"])
            detail = html.escape(status.get("detail", ""))
            icon = "✅" if ok else "❌"
            return (
                f"<div class='card' style='flex:1; min-width:200px; margin:0;'>"
                f"<h2 style='margin-bottom:0.3rem;'>{icon} {html.escape(name)}</h2>"
                f"<p><span class='score-badge {badge_cls}' style='font-size:0.85rem;'>{badge_txt}</span></p>"
                f"<p class='muted' style='font-size:0.82rem;'>{detail}</p>"
                f"<a href='{href}'><button style='padding:0.3rem 0.8rem; cursor:pointer;'>설정 변경</button></a>"
                f"</div>"
            )

        svc_cards = (
            "<div class='cards-row'>"
            + _svc_card("Garmin Connect", "/connect/garmin", garmin_status)
            + _svc_card("Strava", "/connect/strava", strava_status)
            + _svc_card("Intervals.icu", "/connect/intervals", intervals_status)
            + _svc_card("Runalyze", "/connect/runalyze", runalyze_status)
            + "</div>"
        )

        # DB 경로 수정 폼
        db_form = f"""
        <div class="card">
          <h2>DB 경로</h2>
          <form method="post" action="/config/db-path">
            <input type="text" name="db_path" value="{html.escape(str(db_path))}"
                   style="width:340px; padding:0.3rem 0.5rem;">
            <button type="submit" style="padding:0.3rem 0.8rem; cursor:pointer; margin-left:0.5rem;">저장</button>
          </form>
          <p class='muted' style='font-size:0.82rem;'>DB 존재: {_bool_text(db_path.exists())}</p>
        </div>
        """

        body = (
            "<h2>서비스 연동 상태 / 설정 변경</h2>"
            + svc_cards
            + db_form
            + "<h2>전체 설정 내용 (민감정보 전체 마스킹)</h2>"
            + f"<pre>{html.escape(_json.dumps(redacted, indent=2, ensure_ascii=False))}</pre>"
            + "<p class='muted'>민감 정보(비밀번호/토큰/API키)는 ****로 완전 숨김 처리됩니다.</p>"
        )
        return _html_page("Config", body)

    @app.post("/config/db-path")
    def config_db_path():
        """DB 경로 설정 저장."""
        from src.utils.config import update_service_config
        new_path = request.form.get("db_path", "").strip()
        if new_path:
            update_service_config("database", {"path": new_path})
        return redirect("/config")

    @app.post("/trigger-sync")
    def trigger_sync():
        """동기화 실행 — 연결 확인 + 정책 검사 + 중복 방지 + JSON 응답."""
        import re
        import subprocess
        from datetime import date
        from flask import jsonify
        from src.utils.sync_policy import check_incremental_guard, check_range_guard
        from src.utils.sync_state import (
            is_running, mark_running, mark_finished,
            get_last_sync_at, get_retry_after_sec,
        )

        mode = request.form.get("mode", "basic").strip()
        source = request.form.get("source", "all").strip()
        from_date = request.form.get("from_date", "").strip()
        to_date = request.form.get("to_date", "").strip()

        _VALID_SOURCES = {"garmin", "strava", "intervals", "runalyze"}
        checkers = {
            "garmin": check_garmin_connection,
            "strava": check_strava_connection,
            "intervals": check_intervals_connection,
            "runalyze": check_runalyze_connection,
        }
        if source == "all":
            sources_to_sync = list(checkers.keys())
        else:
            # 콤마 구분 다중 소스 지원
            parts = [s.strip() for s in source.split(",") if s.strip() in _VALID_SOURCES]
            sources_to_sync = parts if parts else list(checkers.keys())
        config = load_config()

        # 기간 동기화: days 공통 계산
        hist_days: int | None = None
        if mode in ("historical", "hist") and from_date:
            try:
                d = date.fromisoformat(from_date)
                end = date.fromisoformat(to_date) if to_date else date.today()
                hist_days = max(1, min((end - d).days + 1, 3650))
            except (ValueError, TypeError):
                hist_days = 30

        results = []
        for src in sources_to_sync:
            # 1) 연결 상태 확인
            conn_status = checkers[src](config)
            if not conn_status["ok"]:
                results.append({
                    "source": src, "ok": False, "skipped": True,
                    "count": 0, "error": f"미연결 ({conn_status['status']})",
                })
                continue

            # 2) 중복 실행 방지
            if is_running(src):
                results.append({
                    "source": src, "ok": False, "skipped": True, "count": 0,
                    "error": f"{src} 동기화가 이미 진행 중입니다. 잠시 후 다시 시도하세요.",
                    "reason": "running",
                })
                continue

            # 3) retry_after 확인 (429 등으로 설정된 경우)
            retry_sec = get_retry_after_sec(src)
            if retry_sec and retry_sec > 0:
                from src.utils.sync_policy import _fmt_duration
                results.append({
                    "source": src, "ok": False, "skipped": True, "count": 0,
                    "error": f"{src} — {_fmt_duration(retry_sec)} 후 재시도 가능합니다.",
                    "reason": "retry_after",
                    "retry_after_sec": retry_sec,
                })
                continue

            # 4) 정책 검사
            if hist_days is not None:
                # 기간 동기화: 범위 검사
                guard = check_range_guard(src, hist_days)
                days_for_src = hist_days
            else:
                # 증분 동기화: cooldown 검사
                last_at = get_last_sync_at(src)
                guard = check_incremental_guard(src, last_at)
                days_for_src = _days_since_last_sync([src])

            if not guard.allowed:
                results.append({
                    "source": src, "ok": False, "skipped": True, "count": 0,
                    "error": guard.message_ko or "정책 제한",
                    "reason": guard.reason,
                    "retry_after_sec": guard.retry_after_sec,
                })
                continue

            if guard.message_ko and guard.reason == "range_auto_reduced":
                # 경고는 있지만 허용 — 결과에 경고 포함하고 계속
                print(f"[trigger_sync] {guard.message_ko}")

            # 5) 동기화 실행
            mark_running(src, mode)
            try:
                proc = subprocess.run(
                    [sys.executable, "src/sync.py", "--source", src, "--days", str(days_for_src)],
                    capture_output=True, text=True, timeout=300,
                    cwd=str(_project_root()),
                )
                count = 0
                for line in proc.stdout.splitlines():
                    m = re.search(r"활동 (\d+)개 동기화", line)
                    if m:
                        count += int(m.group(1))

                stderr_tail = (proc.stderr or "")[-400:]
                # subprocess 내 sync 함수가 mark_finished 를 직접 호출하지만
                # subprocess 바깥에서도 실패 시 상태 복구
                if proc.returncode != 0:
                    mark_finished(src, count=0, partial=True, error=stderr_tail)
                    results.append({
                        "source": src, "ok": False, "skipped": False,
                        "count": 0, "error": stderr_tail,
                        "warn": guard.message_ko,
                    })
                else:
                    # 부분 성공 여부는 stdout에서 힌트 확인
                    partial = "일부" in proc.stdout or "⚠️" in proc.stdout
                    if not _already_finished(proc.stdout):
                        mark_finished(src, count=count, partial=partial)
                    results.append({
                        "source": src, "ok": True, "skipped": False,
                        "count": count, "error": None,
                        "partial": partial,
                        "warn": guard.message_ko,
                    })
            except subprocess.TimeoutExpired:
                mark_finished(src, count=0, partial=True, error="타임아웃 (300초)")
                results.append({
                    "source": src, "ok": False, "skipped": False,
                    "count": 0, "error": "동기화 타임아웃 (300초 초과)",
                })
            except Exception as e:
                mark_finished(src, count=0, partial=True, error=str(e))
                results.append({
                    "source": src, "ok": False, "skipped": False,
                    "count": 0, "error": str(e),
                })

        total_count = sum(r.get("count", 0) for r in results)
        overall_ok = any(r.get("ok") for r in results)
        return jsonify({"ok": overall_ok, "results": results, "total_count": total_count})

    # ── 백그라운드 기간 동기화 ────────────────────────────────────────────

    @app.post("/bg-sync/start")
    def bg_sync_start():
        """백그라운드 기간 동기화 시작."""
        from datetime import date as _date
        from flask import jsonify
        from .bg_sync import start_job
        source = request.form.get("source", "").strip()
        from_date = request.form.get("from_date", "").strip()
        to_date = request.form.get("to_date", "").strip() or _date.today().isoformat()

        if source not in ("garmin", "strava", "intervals", "runalyze"):
            return jsonify({"ok": False, "error": "지원하지 않는 서비스입니다."}), 400
        if not from_date:
            return jsonify({"ok": False, "error": "시작일을 입력하세요."}), 400

        try:
            _date.fromisoformat(from_date)
            _date.fromisoformat(to_date)
        except ValueError:
            return jsonify({"ok": False, "error": "날짜 형식이 올바르지 않습니다 (YYYY-MM-DD)."}), 400

        config = load_config()
        job_id = start_job(source, from_date, to_date, config)
        return jsonify({"ok": True, "job_id": job_id, "source": source})

    @app.post("/bg-sync/pause")
    def bg_sync_pause():
        from flask import jsonify
        from .bg_sync import pause_job
        source = request.form.get("source", "").strip()
        ok = pause_job(source)
        return jsonify({"ok": ok})

    @app.post("/bg-sync/stop")
    def bg_sync_stop():
        from flask import jsonify
        from .bg_sync import stop_job
        source = request.form.get("source", "").strip()
        ok = stop_job(source)
        return jsonify({"ok": ok})

    @app.post("/bg-sync/resume")
    def bg_sync_resume():
        from flask import jsonify
        from .bg_sync import resume_job
        source = request.form.get("source", "").strip()
        config = load_config()
        ok = resume_job(source, config)
        return jsonify({"ok": ok})

    @app.get("/bg-sync/status")
    def bg_sync_status():
        from flask import jsonify
        from .bg_sync import get_status
        source = request.args.get("source", "").strip()
        if source not in ("garmin", "strava", "intervals", "runalyze"):
            return jsonify({"active": False})
        return jsonify(get_status(source))

    @app.get("/import")
    @app.get("/import-preview")
    def import_page():
        """GPX/FIT 파일 업로드 + 폴더 미리보기."""
        import tempfile, shutil
        project_root = _project_root()
        garmin_dir = project_root / "data/history/garmin"
        strava_dir = project_root / "data/history/strava"

        garmin_info = _scan_history_dir(garmin_dir)
        strava_info = _scan_history_dir(strava_dir)

        msg = html.escape(request.args.get("msg", ""))
        err = html.escape(request.args.get("error", ""))
        msg_html = f"<div class='card' style='border-color:#4caf50;'><p>{msg}</p></div>" if msg else ""
        err_html = f"<div class='card' style='border-color:#c0392b;'><p style='color:#c0392b;'>{err}</p></div>" if err else ""

        def section(title: str, source: str, info: dict) -> str:
            by_ext_rows = [(ext, count) for ext, count in info["by_ext"]]
            return (
                f"<div class='card'>"
                f"<h2>{html.escape(title)}</h2>"
                f"<p>경로: <code>{html.escape(info['base_dir'])}</code> — "
                f"{'존재' if info['exists'] else '없음'}, 파일 {info['total_files']}개</p>"
                + _table(["확장자", "개수"], by_ext_rows)
                + "</div>"
            )

        upload_form = f"""
        <div class="card">
          <h2>파일 업로드 (단일/다수)</h2>
          <p>GPX · FIT · TCX (+ .gz) 파일을 선택하면 <code>data/history/&lt;source&gt;/</code> 폴더에 저장 후 import 합니다.</p>
          <form method="post" action="/import/upload" enctype="multipart/form-data">
            <table style="width:auto; border:none;">
              <tr>
                <td style="border:none; padding:0.3rem 0.5rem;">소스:</td>
                <td style="border:none; padding:0.3rem 0.5rem;">
                  <select name="source" style="padding:0.3rem 0.5rem; border-radius:4px;">
                    <option value="garmin">Garmin</option>
                    <option value="strava">Strava</option>
                  </select>
                </td>
              </tr>
              <tr>
                <td style="border:none; padding:0.3rem 0.5rem;">파일:</td>
                <td style="border:none; padding:0.3rem 0.5rem;">
                  <input type="file" name="files" multiple
                    accept=".gpx,.fit,.tcx,.gpx.gz,.fit.gz,.tcx.gz,.GPX,.FIT,.TCX">
                </td>
              </tr>
            </table>
            <div style="margin-top:0.8rem;">
              <button type="submit" style="padding:0.4rem 1.2rem; background:#2ecc71; color:#fff; border:none; border-radius:4px; cursor:pointer;">
                업로드 및 Import
              </button>
            </div>
          </form>
        </div>
        <div class="card">
          <h2>Strava archive ZIP 업로드</h2>
          <p>Strava &gt; 내 계정 &gt; 데이터 내보내기에서 받은 <strong>.zip</strong> 파일을 업로드합니다.<br>
             <code>activities.csv</code> + <code>activities/</code> 폴더를 자동으로 인식합니다.</p>
          <form method="post" action="/import/upload-archive" enctype="multipart/form-data">
            <table style="width:auto; border:none;">
              <tr>
                <td style="border:none; padding:0.3rem 0.5rem;">ZIP 파일:</td>
                <td style="border:none; padding:0.3rem 0.5rem;">
                  <input type="file" name="archive" accept=".zip,.ZIP">
                </td>
              </tr>
            </table>
            <div style="margin-top:0.8rem;">
              <button type="submit" style="padding:0.4rem 1.2rem; background:#3498db; color:#fff; border:none; border-radius:4px; cursor:pointer;">
                Archive 임포트
              </button>
            </div>
          </form>
        </div>
        """

        body = (
            err_html + msg_html
            + upload_form
            + section("Garmin 폴더 현황", "garmin", garmin_info)
            + section("Strava 폴더 현황", "strava", strava_info)
        )
        return _html_page("Import", body)

    @app.post("/import/upload")
    def import_upload():
        """GPX/FIT/TCX (+ .gz) 파일 수신 → 폴더 저장 → import_history 실행."""
        import subprocess
        from werkzeug.utils import secure_filename

        _ALLOWED = {".gpx", ".fit", ".tcx", ".gz"}

        source = request.form.get("source", "garmin").strip()
        if source not in ("garmin", "strava"):
            source = "garmin"

        files = request.files.getlist("files")
        if not files or all(f.filename == "" for f in files):
            return redirect("/import?error=파일을 선택하세요.")

        dest_dir = _project_root() / "data" / "history" / source
        dest_dir.mkdir(parents=True, exist_ok=True)

        saved = []
        for f in files:
            if f.filename:
                fname = secure_filename(f.filename)
                ext = Path(fname).suffix.lower()
                if ext not in _ALLOWED:
                    continue
                save_path = dest_dir / fname
                f.save(str(save_path))
                saved.append(fname)

        if not saved:
            return redirect("/import?error=GPX/FIT/TCX (.gz 포함) 파일만 업로드 가능합니다.")

        try:
            proc = subprocess.run(
                [sys.executable, "src/import_history.py", str(dest_dir),
                 "--source", source, "-r"],
                capture_output=True, text=True, timeout=120,
                cwd=str(_project_root()),
            )
            stdout = proc.stdout[-3000:] if proc.stdout else "(출력 없음)"
            stderr = proc.stderr[-1000:] if proc.stderr else ""
            rc = proc.returncode
        except Exception as e:
            stdout, stderr, rc = "", str(e), -1

        status = "✅ 성공" if rc == 0 else f"❌ 오류 (exit {rc})"
        body = f"""
        <div class="card">
          <h2>Import 결과</h2>
          <p>저장된 파일: {html.escape(', '.join(saved))}</p>
          <p>{status}</p>
          <pre>{html.escape(stdout)}</pre>
          {"<pre style='color:#c0392b;'>" + html.escape(stderr) + "</pre>" if stderr else ""}
          <p><a href="/import">&larr; Import 페이지로</a> &nbsp; <a href="/">홈으로</a></p>
        </div>
        """
        return _html_page("Import 결과", body)

    @app.post("/import/upload-archive")
    def import_upload_archive():
        """Strava archive ZIP 업로드 → 임시 디렉터리 압축 해제 → import_strava_archive 실행."""
        import shutil
        import tempfile
        import zipfile
        from werkzeug.utils import secure_filename
        from src.import_export.strava_archive import import_strava_archive

        f = request.files.get("archive")
        if not f or f.filename == "":
            return redirect("/import?error=ZIP 파일을 선택하세요.")

        fname = secure_filename(f.filename)
        if not fname.lower().endswith(".zip"):
            return redirect("/import?error=ZIP 파일만 업로드 가능합니다.")

        tmp_dir = Path(tempfile.mkdtemp(prefix="runpulse_archive_"))
        try:
            zip_path = tmp_dir / fname
            f.save(str(zip_path))

            # ZIP 압축 해제
            try:
                with zipfile.ZipFile(zip_path, "r") as zf:
                    zf.extractall(tmp_dir)
            except zipfile.BadZipFile:
                return redirect("/import?error=유효한 ZIP 파일이 아닙니다.")

            # activities.csv 위치 탐색 (루트 또는 1단계 하위)
            archive_root: Path | None = None
            if (tmp_dir / "activities.csv").exists():
                archive_root = tmp_dir
            else:
                for sub in sorted(tmp_dir.iterdir()):
                    if sub.is_dir() and (sub / "activities.csv").exists():
                        archive_root = sub
                        break

            if archive_root is None:
                return redirect("/import?error=activities.csv를 찾을 수 없습니다. Strava archive ZIP이 맞는지 확인하세요.")

            db_path = _db_path()
            if not db_path.exists():
                return redirect("/import?error=DB가 초기화되지 않았습니다. python src/db_setup.py를 먼저 실행하세요.")

            with sqlite3.connect(str(db_path)) as conn:
                stats = import_strava_archive(conn, archive_root)

        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

        rows = [
            ("CSV 전체 행", stats["csv_total"]),
            ("신규 삽입", stats["inserted"]),
            ("중복 건너뜀", stats["skipped"]),
            ("파일 연결 성공", stats["file_linked"]),
            ("CSV-only fallback", stats["csv_only"]),
            ("gz 압축 해제 성공", stats["gz_ok"]),
            ("오류", stats["errors"]),
        ]
        table_html = _table(["항목", "수"], rows)
        body = f"""
        <div class="card">
          <h2>Strava Archive Import 결과</h2>
          {table_html}
          <p><a href="/import">&larr; Import 페이지로</a> &nbsp; <a href="/activities">활동 목록</a></p>
        </div>
        """
        return _html_page("Archive Import 결과", body)

    @app.get("/sync-status")
    def sync_status():
        config = load_config()

        garmin_st = check_garmin_connection(config)
        strava_st = check_strava_connection(config)
        intervals_st = check_intervals_connection(config)
        runalyze_st = check_runalyze_connection(config)

        def _row(service: str, status: dict) -> tuple:
            icon = "✅" if status["ok"] else "❌"
            return (service, f"{icon} {status['status']}", status.get("detail", ""))

        rows = [
            _row("Garmin Connect", garmin_st),
            _row("Strava", strava_st),
            _row("Intervals.icu", intervals_st),
            _row("Runalyze", runalyze_st),
        ]

        body = (
            "<div class='card'>"
            "<h2>서비스 연동 상태</h2>"
            "<p>실제 인증 상태 기반 표시입니다. 연동이 필요하면 <a href='/settings'>설정 페이지</a>로 이동하세요.</p>"
            + _table(["서비스", "상태", "상세"], rows)
            + "</div>"
            + """
            <div class="card">
              <h2>추천 sync 명령</h2>
              <pre>python src/sync.py --source garmin --days 7
python src/sync.py --source strava --days 7
python src/sync.py --source intervals --days 28
python src/sync.py --source runalyze --days 28
python src/sync.py --source all --days 7</pre>
            </div>
            <div class="card">
              <h2>Garmin MFA 안내</h2>
              <p>Garmin 로그인 시 MFA(이중 인증)가 요청되면 Garmin 앱 또는 이메일에서 승인하세요.</p>
              <p>로그인 성공 후 토큰이 저장되면 이후 sync 시 MFA 없이 복구됩니다.</p>
              <p><a href='/connect/garmin'>Garmin 연동 설정 →</a></p>
            </div>
            """
        )
        return _html_page("Sync Status", body)


    @app.get("/payloads")
    def payloads():
        db_path = _db_path()
        if not db_path.exists():
            body = "<div class='card'><h2>DB 없음</h2><p>running.db가 없습니다.</p></div>"
            return _html_page("Payloads", body)

        source = request.args.get("source", "").strip()
        entity_type = request.args.get("entity_type", "").strip()
        activity_id = request.args.get("activity_id", "").strip()
        limit = max(1, min(_to_int(request.args.get("limit", "20"), 20), 200))

        where = []
        params = []

        if source:
            where.append("source = ?")
            params.append(source)
        if entity_type:
            where.append("entity_type = ?")
            params.append(entity_type)
        if activity_id:
            where.append("activity_id = ?")
            params.append(activity_id)

        where_sql = ("WHERE " + " AND ".join(where)) if where else ""

        try:
            with sqlite3.connect(db_path) as conn:
                payload_counts = conn.execute(
                    """
                    SELECT source, entity_type, count(*) AS cnt
                    FROM raw_source_payloads
                    GROUP BY source, entity_type
                    ORDER BY source, entity_type
                    """
                ).fetchall()

                metric_counts = conn.execute(
                    """
                    SELECT source, metric_name, count(*) AS cnt
                    FROM activity_detail_metrics
                    GROUP BY source, metric_name
                    ORDER BY source, metric_name
                    LIMIT 100
                    """
                ).fetchall()

                recent_payloads = conn.execute(
                    f"""
                    SELECT id, source, entity_type, entity_id, activity_id,
                           length(payload_json) AS payload_len, updated_at
                    FROM raw_source_payloads
                    {where_sql}
                    ORDER BY updated_at DESC
                    LIMIT ?
                    """,
                    (*params, limit),
                ).fetchall()
        except Exception as e:
            return _html_page("Payloads", f"<div class='card'><h2>조회 실패</h2><pre>{html.escape(str(e))}</pre></div>")

        filter_form = f"""
        <div class="card">
          <h2>filters</h2>
          <form method="get" action="/payloads">
            <label>source <input type="text" name="source" value="{html.escape(source)}"></label>
            <label> entity_type <input type="text" name="entity_type" value="{html.escape(entity_type)}"></label>
            <label> activity_id <input type="text" name="activity_id" value="{html.escape(activity_id)}"></label>
            <label> limit <input type="number" name="limit" min="1" max="200" value="{limit}"></label>
            <button type="submit">apply</button>
          </form>
          <p class="muted">예: /payloads?source=intervals&entity_type=wellness&limit=50</p>
        </div>
        """

        body = (
            filter_form
            + "<div class='card'><h2>source_payloads counts</h2>"
            + _table(["source", "entity_type", "count"], payload_counts)
            + "</div>"
            + "<div class='card'><h2>source_metrics counts</h2>"
            + _table(["source", "metric_name", "count"], metric_counts)
            + "</div>"
            + "<div class='card'><h2>recent payloads</h2>"
            + _payload_recent_table(recent_payloads)
            + "</div>"
        )
        return _html_page("Payloads", body)


    @app.get("/payloads/view")
    def payload_view():
        db_path = _db_path()
        if not db_path.exists():
            body = "<div class='card'><h2>DB 없음</h2><p>running.db가 없습니다.</p></div>"
            return _html_page("Payload View", body)

        payload_id = request.args.get("id", "").strip()
        if not payload_id:
            body = "<div class='card'><h2>잘못된 요청</h2><p>id 파라미터가 필요합니다.</p></div>"
            return _html_page("Payload View", body)

        try:
            with sqlite3.connect(db_path) as conn:
                row = conn.execute(
                    """
                    SELECT id, source, entity_type, entity_id, activity_id, payload_json, created_at, updated_at
                    FROM raw_source_payloads
                    WHERE id = ?
                    """,
                    (payload_id,),
                ).fetchone()

                if not row:
                    body = f"<div class='card'><h2>없음</h2><p>payload id={html.escape(payload_id)} 를 찾을 수 없습니다.</p></div>"
                    return _html_page("Payload View", body)

                metrics = []
                if row[4]:
                    metrics = conn.execute(
                        """
                        SELECT source, metric_name,
                               COALESCE(CAST(metric_value AS TEXT), metric_json) AS metric_data
                        FROM activity_detail_metrics
                        WHERE activity_id = ?
                        ORDER BY source, metric_name
                        LIMIT 100
                        """,
                        (row[4],),
                    ).fetchall()
        except sqlite3.Error as exc:
            body = f"<div class='card'><h2>DB 오류</h2><pre>{html.escape(str(exc))}</pre></div>"
            return _html_page("Payload View", body)

        detail_rows = [
            ("id", row[0]),
            ("source", row[1]),
            ("entity_type", row[2]),
            ("entity_id", row[3]),
            ("activity_id", row[4]),
            ("created_at", row[6]),
            ("updated_at", row[7]),
        ]

        extra = ""
        if row[4]:
            extra += (
                "<div class='card'><h2>연관 source_metrics</h2>"
                + _table(["source", "metric_name", "metric_data"], metrics)
                + "</div>"
            )

        body = (
            "<div class='card'><h2>payload metadata</h2>"
            + _table(["field", "value"], detail_rows)
            + "</div>"
            + "<div class='card'><h2>payload json</h2>"
            + _json_pretty_block(row[5])
            + "</div>"
            + extra
            + "<p><a href='/payloads'>← payloads 목록으로</a></p>"
        )
        return _html_page(f"Payload View #{row[0]}", body)

    @app.get("/db")
    def db_summary():
        db_path = _db_path()
        if not db_path.exists():
            body = f"""
            <p>데이터베이스가 없습니다: <code>{html.escape(str(db_path))}</code></p>

            <div class="card">
              <h2>다음 액션</h2>
              <ol>
                <li><code>python src/db_setup.py</code> 로 DB 스키마 생성</li>
                <li>최근 데이터는 sync CLI로 가져오기</li>
                <li>과거 파일은 import_history CLI로 가져오기</li>
              </ol>
            </div>

            <div class="card">
              <h2>예시 명령</h2>
              <pre>python src/db_setup.py

python src/import_history.py data/history/garmin --source garmin -r
python src/import_history.py data/history/strava --source strava -r

python src/analyze.py today
python src/analyze.py full</pre>
            </div>

            <div class="card">
              <h2>권장 디렉터리</h2>
              <pre>data/history/garmin/
data/history/strava/</pre>
            </div>
            """
            return _html_page("DB Summary", body)

        conn = sqlite3.connect(str(db_path))
        try:
            table_counts = [
                ("activity_summaries", _query_value(conn, "select count(*) from activity_summaries")),
                ("activity_detail_metrics", _query_value(conn, "select count(*) from activity_detail_metrics")),
                ("daily_wellness", _query_value(conn, "select count(*) from daily_wellness")),
                ("daily_fitness", _query_value(conn, "select count(*) from daily_fitness")),
                ("goals", _query_value(conn, "select count(*) from goals")),
            ]

            activities_total = dict(table_counts).get("activity_summaries", 0)

            activities_by_source = _query_rows(
                conn,
                """
                select source, count(*)
                from activity_summaries
                group by source
                order by source
                """,
            )
            fitness_by_source = _query_rows(
                conn,
                """
                select source, count(*)
                from daily_fitness
                group by source
                order by source
                """,
            )
            wellness_by_source = _query_rows(
                conn,
                """
                select source, count(*)
                from daily_wellness
                group by source
                order by source
                """,
            )
            recent_activities = _query_rows(
                conn,
                """
                select id, source, activity_type, start_time, distance_km, duration_sec
                from activity_summaries
                order by start_time desc
                limit 20
                """,
            )
            matched_groups = _query_rows(
                conn,
                """
                select matched_group_id, count(*)
                from activity_summaries
                where matched_group_id is not null
                group by matched_group_id
                having count(*) > 1
                order by count(*) desc, matched_group_id
                limit 20
                """,
            )
        finally:
            conn.close()

        body = (
            f"<p class='muted'>DB path: {html.escape(str(db_path))}</p>"
            + "<h2>Table row counts</h2>"
            + _table(["table", "count"], table_counts)
        )

        if activities_total == 0:
            body += """
            <div class="card">
              <h2>빈 DB 상태</h2>
              <p>DB 파일과 스키마는 존재하지만 아직 activity 데이터가 없습니다.</p>
              <ol>
                <li>최근 데이터는 <code>sync.py</code>로 가져오기</li>
                <li>과거 파일은 <code>import_history.py</code>로 가져오기</li>
                <li>데이터가 들어오면 이 페이지에 source별 집계와 최근 활동이 표시됩니다.</li>
              </ol>
            </div>
            <div class="card">
              <h2>추천 명령</h2>
              <pre>python src/sync.py --source all --days 7

python src/import_history.py data/history/garmin --source garmin -r
python src/import_history.py data/history/strava --source strava -r</pre>
            </div>
            """
            return _html_page("DB Summary", body)

        # 최근 활동 테이블에 심층 분석 링크 추가
        act_rows_with_link = []
        for row in recent_activities:
            act_id = row[0]
            act_rows_with_link.append(row + (f"/activity/deep?id={act_id}",))

        def _recent_acts_table(rows):
            if not rows:
                return "<p class='muted'>(no rows)</p>"
            headers = ["id", "source", "activity_type", "start_time", "distance_km", "duration_sec", "심층 분석"]
            head = "".join(f"<th>{html.escape(h)}</th>" for h in headers)
            body_rows = []
            for row in rows:
                *data_cols, link = row
                cols = "".join(f"<td>{html.escape(str(v))}</td>" for v in data_cols)
                cols += f"<td><a href='{html.escape(str(link))}'>보기</a></td>"
                body_rows.append(f"<tr>{cols}</tr>")
            return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body_rows)}</tbody></table>"

        body += (
            "<h2>Activities by source</h2>"
            + _table(["source", "count"], activities_by_source)
            + "<h2>Daily fitness by source</h2>"
            + _table(["source", "count"], fitness_by_source)
            + "<h2>Daily wellness by source</h2>"
            + _table(["source", "count"], wellness_by_source)
            + "<h2>Recent activities</h2>"
            + _recent_acts_table(act_rows_with_link)
            + "<h2>Matched groups</h2>"
            + _table(["matched_group_id", "count"], matched_groups)
        )
        return _html_page("DB Summary", body)

    # ── /db 테이블에 활동 심층 링크 추가는 recent_activities 쿼리에서 처리 ──

    @app.get("/analyze/<report_type>")
    def analyze_preview(report_type: str):
        allowed = {"today", "full", "race"}
        if report_type not in allowed:
            return _html_page(
                "Analyze Preview",
                f"<p>지원하지 않는 report_type: {html.escape(report_type)}</p>",
            ), 404

        db_path = _db_path()
        if not db_path.exists():
            body = f"<p>데이터베이스가 없습니다: {html.escape(str(db_path))}</p>"
            return _html_page("Analyze Preview", body)

        config = load_config()
        if report_type == "race":
            race_date = request.args.get("date")
            race_distance = request.args.get("distance")
            if race_date:
                config.setdefault("race", {})
                config["race"]["date"] = race_date
            if race_distance:
                config.setdefault("race", {})
                try:
                    config["race"]["distance"] = float(race_distance)
                except ValueError:
                    pass

        conn = sqlite3.connect(str(db_path))
        try:
            output = generate_report(conn, report_type=report_type, config=config)
        finally:
            conn.close()

        body = f"<pre>{html.escape(output)}</pre>"
        return _html_page(f"Analyze Preview: {report_type}", body)

    # ── Blueprint 등록 ─────────────────────────────────────────────────
    app.register_blueprint(wellness_bp)
    app.register_blueprint(activity_bp)
    app.register_blueprint(activities_bp)
    app.register_blueprint(settings_bp)  # 서비스 연동 설정
    app.register_blueprint(merge_bp)          # 활동 그룹 병합/분리 API
    app.register_blueprint(export_import_bp)  # Export CSV 임포트
    app.register_blueprint(shoes_bp)          # 신발 목록
    app.register_blueprint(dashboard_bp)      # v0.2 통합 대시보드

    return app

"""RunPulse integration workbench web app."""

from __future__ import annotations

import html
import logging
import os
import sqlite3
import time
from pathlib import Path

from flask import Flask, redirect, request, session

from src.utils.config import load_config

log = logging.getLogger(__name__)

# Phase 5 Blueprint imports
from .views_wellness import wellness_bp
from .views_activity import activity_bp
from .views_activities import activities_bp
from .views_settings import settings_bp
from .views_settings_garmin import settings_garmin_bp
from .views_settings_integrations import settings_integrations_bp
from .views_settings_metrics import settings_metrics_bp
from .views_activity_merge import merge_bp
from .views_export_import import export_import_bp
from .views_export import export_bp
from .views_shoes import shoes_bp

# Phase 3 (v0.2) Blueprint imports
from .views_dashboard import dashboard_bp
from .views_report import report_bp
from .views_import import import_bp
from .views_race import race_bp
from .views_dev import dev_bp
from .views_training import training_bp
from .views_training_crud import training_crud_bp
from .views_training_goal_crud import training_goal_crud_bp
from .views_training_export import training_export_bp
from src.api.routes_calendar_feed import calendar_feed_bp
from src.mcp_remote.http import mcp_remote_bp
from .views_training_wizard import wizard_bp
from .views_training_fullplan import fullplan_bp
from .views_sync import sync_bp
from .views_guide import guide_bp

# Phase 7 /api/v1/ JSON API (SvelteKit v2 소비)
from src.api import api_bp
from src.api.routes_v1_sync import v1_sync_bp
from src.api.routes_v1_pages import v1_pages_bp
from .spa_static import serve_v2_response
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
    from src.services.unified_view import fetch_unified_activities
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
    """helpers.db_path() 위임 — 사용자별 DB 경로 반환."""
    from src.utils.user_context import db_path as _dbp
    return _dbp()


def _html_page(title: str, body: str) -> str:
    """helpers.html_page 위임 — CSS/nav 중복 제거."""
    from .helpers import html_page as _hp
    return _hp(title, body)


def _auto_migrate() -> None:
    """앱 시작 시 기존 DB 스키마를 최신 버전으로 자동 마이그레이션."""
    db = _db_path()
    if not db.exists():
        return
    try:
        from src.db_setup import migrate_db
        with sqlite3.connect(str(db)) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            migrated = migrate_db(conn)
            if migrated:
                import logging
                logging.getLogger(__name__).info("DB 스키마 마이그레이션 완료, 재동기화 필요")
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("마이그레이션 실패: %s", exc)


def _resolve_secret_key() -> str:
    """FLASK_SECRET_KEY 환경변수 우선. 없으면 production 시 시작 거부."""
    key = os.environ.get("FLASK_SECRET_KEY", "")
    if key:
        return key
    is_production = os.environ.get("APP_ENV", "development").lower() == "production"
    if is_production:
        raise RuntimeError(
            "[app] FLASK_SECRET_KEY 환경변수가 설정되지 않았습니다. "
            "production 환경에서는 필수입니다. .env 파일을 확인하세요."
        )
    log.warning("[app] FLASK_SECRET_KEY 미설정 — 로컬 개발 전용 키 사용 (production 금지)")
    return "runpulse-local-dev-only"


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=str(_project_root() / "templates"),
        static_folder=str(_project_root() / "static"),
        static_url_path="/static",
    )
    app.secret_key = _resolve_secret_key()
    app.config["PERMANENT_SESSION_LIFETIME"] = 60 * 60 * 24 * 7  # 7일
    # 세션 쿠키 속성 (SRV-10) — Secure 판정은 APP_ENV (http 개발 환경에서 쿠키가 사라지지 않게)
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SECURE"] = os.environ.get("APP_ENV", "development").lower() == "production"

    # CF Zero Trust 헤더 기반 사용자 식별 미들웨어 등록
    from .auth_cf import init_cf_auth
    init_cf_auth(app, config=load_config())

    # Origin 관문 — 인증 훅 뒤에 등록(인증 통과 요청만 검사, SRV 2.1)
    from .request_guard import init_request_guard
    init_request_guard(app)

    # 응답 정책 — 공통 보안 헤더 + 표면별 CSP (after_request, S3-9)
    from .response_policy import init_response_policy
    init_response_policy(app)

    _auto_migrate()

    # 모든 유저 DB 마이그레이션 + 자동 주기 동기화 daemon thread 시작
    try:
        from src.sync.auto_sync import start as _start_auto_sync
        from src.db_setup import create_tables, migrate_db, get_db_path
        from src.utils.user_context import list_user_ids
        user_ids = list_user_ids() if (_project_root() / "data" / "users").exists() else ["default"]
        # 모든 유저 DB를 최신 스키마로 마이그레이션
        for _uid in user_ids:
            _db = get_db_path(_uid)
            if _db.exists():
                try:
                    with sqlite3.connect(str(_db)) as _conn:
                        _conn.execute("PRAGMA journal_mode=WAL")
                        create_tables(_conn)  # 빈 DB(가입 직후)도 마이그레이션 전에 스키마 확보
                        migrate_db(_conn)
                except Exception as _me:
                    log.warning("[startup] %s DB 마이그레이션 실패: %s", _uid, _me)
        # 자격증명이 있는 non-default 유저 우선, 없으면 첫 번째 non-default, 최후에 default
        def _has_creds(uid: str) -> bool:
            try:
                cfg = load_config(user_id=uid)
                return bool(
                    cfg.get("garmin", {}).get("email")
                    or cfg.get("strava", {}).get("refresh_token")
                    or cfg.get("intervals", {}).get("api_key")
                )
            except Exception:
                return False

        _sync_uid = next(
            (uid for uid in user_ids if uid != "default" and _has_creds(uid)),
            next((uid for uid in user_ids if uid != "default"),
                 user_ids[0] if user_ids else "default"),
        )
        _start_auto_sync(load_config(user_id=_sync_uid), user_id=_sync_uid)
    except Exception as _e:
        log.warning("[auto_sync] 시작 실패: %s", _e)

    from src.utils.user_context import InvalidUserId

    @app.errorhandler(InvalidUserId)
    def _invalid_user_id(exc: InvalidUserId):
        """get_db_path 등에서 올라온 uid 규칙 위반(V1-20 이중 방어) — HTML 500 으로 새지 않게 403."""
        from .request_guard import forbidden_response
        logging.getLogger("runpulse.security").warning("[app] uid 규칙 위반 %s (path=%s)", exc.masked, request.path)
        return forbidden_response("FORBIDDEN_USER", "허용되지 않는 사용자 식별자입니다.")

    @app.before_request
    def _ensure_user_db_migrated():
        """요청마다 현재 사용자 DB를 최신 스키마로 마이그레이션 (이미 최신이면 즉시 반환)."""
        if request.path.startswith("/feeds/cal/"):
            return
        db = _db_path()
        if not db.exists():
            # 신규 가입자: 인증을 통과한 v2 API 요청에서만 빈 DB를 만들어 503 대신 빈 상태를 보이게 한다.
            if not request.path.startswith("/api/v1/") or "user_id" not in session:
                return
            try:
                from src.db_setup import init_db
                init_db(session["user_id"])
            except Exception as exc:
                log.warning("신규 사용자 DB 생성 실패: %s", exc)
            return
        try:
            from src.db_setup import migrate_db
            with sqlite3.connect(str(db)) as conn:
                conn.execute("PRAGMA journal_mode=WAL")
                migrate_db(conn)
        except Exception as exc:
            log.warning("요청별 마이그레이션 실패: %s", exc)

    # ── Jinja2 설정 ──────────────────────────────────────────────────────────
    from .helpers import _CSS, _SYNC_JS, _build_nav, bottom_nav

    @app.context_processor
    def _inject_ui_context():
        try:
            _dev = bool(load_config().get("dev_mode", True))
        except Exception:
            _dev = True
        return {
            "stylesheet": _CSS,
            "nav_html": _build_nav(),
            "sync_js": _SYNC_JS,
            "dev_mode": _dev,
        }

    app.jinja_env.globals["bottom_nav"] = bottom_nav

    # 사용자 전환은 v2 로 이관됨 — GET /api/v1/dev/users, POST /api/v1/dev/switch-user (개발 전용, V1-8)

    @app.get("/")
    def index():
        from src.services.user_settings_service import entry_path
        conn = None
        try:
            db = _db_path()
            conn = sqlite3.connect(str(db)) if db.exists() else None
            return redirect(entry_path(conn, load_config()))
        except sqlite3.Error:
            return redirect("/dashboard")
        finally:
            if conn is not None:
                conn.close()

    # ── v0.1 → v0.2 리다이렉트 (V2-9-7) ──────────────────────────────
    @app.get("/analyze/today")
    def analyze_today_redirect():
        return redirect("/dashboard")

    @app.get("/analyze/full")
    def analyze_full_redirect():
        return redirect("/report")

    @app.get("/analyze/race")
    def analyze_race_redirect():
        return redirect("/race")

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
              <h2>이번 주 훈련 점수 <a href="/report" style="font-size:0.8rem; font-weight:normal;">리포트 &rarr;</a></h2>
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
        from src.utils.sync_ledger_query import legacy_card_states
        from src.utils.user_context import get_current_user_id as _get_uid
        sync_card = sync_card_html(
            last_sync=last_sync_info(["garmin", "strava", "intervals", "runalyze"]),
            sync_states=legacy_card_states(_get_uid()),
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


    # ── Phase 7 /v2/ 정적 서빙 (SvelteKit 빌드 산출물) ──────────────────
    # 05-tech-architecture.md §3.4. frontend/build/가 없으면(아직 빌드 전) 404 —
    # 개발 중엔 `cd frontend && npm run dev`(5173)로 확인한다.
    @app.route("/v2/", defaults={"path": ""})
    @app.route("/v2/<path:path>")
    def serve_v2(path):
        # 자산/클라이언트 라우트 분기·캐시 규칙은 spa_static (S3-8, E-04)
        return serve_v2_response(_project_root() / "frontend" / "build", path)

    # ── Blueprint 등록 ─────────────────────────────────────────────────
    app.register_blueprint(wellness_bp)
    app.register_blueprint(activity_bp)
    app.register_blueprint(activities_bp)
    app.register_blueprint(settings_bp)              # 설정 메인
    app.register_blueprint(settings_garmin_bp)       # 설정 — Garmin 연동
    app.register_blueprint(settings_integrations_bp) # 설정 — Strava/Intervals/Runalyze
    app.register_blueprint(settings_metrics_bp)      # 설정 — 메트릭 재계산
    app.register_blueprint(merge_bp)          # 활동 그룹 병합/분리 API
    app.register_blueprint(export_import_bp)  # Export CSV 임포트
    app.register_blueprint(export_bp)         # 활동 CSV 내보내기
    app.register_blueprint(shoes_bp)          # 신발 목록
    app.register_blueprint(dashboard_bp)      # v0.2 통합 대시보드
    app.register_blueprint(report_bp)         # v0.2 분석 레포트
    app.register_blueprint(import_bp)         # v0.2 Strava 아카이브 임포트
    app.register_blueprint(race_bp)          # v0.2 Sprint5 레이스 예측
    app.register_blueprint(training_bp)            # v0.3 훈련 계획 (스캐폴딩)
    app.register_blueprint(training_crud_bp)       # v0.3 훈련 워크아웃 CRUD
    app.register_blueprint(training_goal_crud_bp)  # v0.3 훈련 목표 CRUD
    app.register_blueprint(training_export_bp)     # v0.3 훈련 내보내기/전송
    app.register_blueprint(mcp_remote_bp)          # 원격 MCP (/mcp, Bearer 토큰)
    app.register_blueprint(calendar_feed_bp)       # 캘린더 구독 공개 피드 (/feeds/cal/<token>.ics)
    app.register_blueprint(wizard_bp)         # v0.2 훈련 계획 Wizard
    app.register_blueprint(fullplan_bp)       # v0.2 전체 훈련 일정 뷰
    app.register_blueprint(dev_bp)            # 개발자/디버그 도구
    app.register_blueprint(guide_bp)          # 용어집/가이드
    app.register_blueprint(sync_bp)           # 동기화 탭
    app.register_blueprint(api_bp)            # Phase 7 /api/v1/ JSON API
    app.register_blueprint(v1_sync_bp)        # v1 sync 트리거·bg-sync·garmin local-sync (V1S-12 b, S3-7)
    app.register_blueprint(v1_pages_bp)       # v1 import 화면·sync-status (V1S-12 b, S3-7)

    return app

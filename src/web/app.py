"""RunPulse integration workbench web app."""

from __future__ import annotations

import logging
import os
import sqlite3
from pathlib import Path

from flask import Flask, redirect, request, session

from src.utils.config import load_config

log = logging.getLogger(__name__)

# Phase 5 Blueprint imports
from .views_settings_garmin import settings_garmin_bp
from .views_settings_integrations import settings_integrations_bp
from .views_export import export_bp

# Phase 3 (v0.2) Blueprint imports
from .views_training_export import training_export_bp
from src.api.routes_calendar_feed import calendar_feed_bp
from src.mcp_remote.http import mcp_remote_bp

# Phase 7 /api/v1/ JSON API (SvelteKit v2 소비)
from src.api import api_bp
from src.api.routes_context import context_bp
from src.api.routes_v1_sync import v1_sync_bp
from src.api.routes_v1_pages import v1_pages_bp
from .spa_static import serve_v2_response
def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _db_path() -> Path:
    """helpers.db_path() 위임 — 사용자별 DB 경로 반환."""
    from src.utils.user_context import db_path as _dbp
    return _dbp()


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
            return redirect("/v2/today")
        finally:
            if conn is not None:
                conn.close()

    # ── Phase 7 /v2/ 정적 서빙 (SvelteKit 빌드 산출물) ──────────────────
    # 05-tech-architecture.md §3.4. frontend/build/가 없으면(아직 빌드 전) 404 —
    # 개발 중엔 `cd frontend && npm run dev`(5173)로 확인한다.
    @app.route("/v2/", defaults={"path": ""})
    @app.route("/v2/<path:path>")
    def serve_v2(path):
        # 자산/클라이언트 라우트 분기·캐시 규칙은 spa_static (S3-8, E-04)
        return serve_v2_response(_project_root() / "frontend" / "build", path)

    # ── Blueprint 등록 ─────────────────────────────────────────────────
    app.register_blueprint(settings_garmin_bp)       # 설정 — Garmin 연동
    app.register_blueprint(settings_integrations_bp) # 설정 — Strava/Intervals/Runalyze
    app.register_blueprint(export_bp)         # 활동 CSV 내보내기
    app.register_blueprint(training_export_bp)     # v0.3 훈련 내보내기/전송
    app.register_blueprint(mcp_remote_bp)          # 원격 MCP (/mcp, Bearer 토큰)
    app.register_blueprint(calendar_feed_bp)       # 캘린더 구독 공개 피드 (/feeds/cal/<token>.ics)
    app.register_blueprint(api_bp)            # Phase 7 /api/v1/ JSON API
    app.register_blueprint(context_bp)        # 컨텍스트 에피소드 /api/context-episodes (NEW-40)
    app.register_blueprint(v1_sync_bp)        # v1 sync 트리거·bg-sync·garmin local-sync (V1S-12 b, S3-7)
    app.register_blueprint(v1_pages_bp)       # v1 import 화면·sync-status (V1S-12 b, S3-7)

    return app

"""pytest 공통 fixture — v0.3 스키마.

테스트 DB 전략:
  - db_conn: 인메모리 DB (빈 스키마, 단위 테스트용)
  - db_conn_default: data/users/default/running.db 복사본 (실 데이터 테스트)
  - db_conn_user: data/users/pansongit@gmail.com/running.db 복사본 (실 데이터 테스트)

실 데이터 DB는 원본을 건드리지 않고 temp 파일로 복사하여 사용합니다.
해당 DB 파일이 없으면 skip됩니다.
"""

import shutil
import sqlite3
import tempfile
from pathlib import Path

import pytest

from src.db_setup import create_tables, migrate_db, get_db_path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Origin 관문(SRV 2.1)은 운영 기본이 observe 지만 테스트는 enforce 최종 상태로 돌린다 —
# 쓰기 요청을 보내는 test_client 호출은 `Origin: http://localhost`(test_client 의 url_root)를 붙여야 한다.

@pytest.fixture
def isolated_users_root(tmp_path, monkeypatch):
    """`data/users` 를 tmp 로 격리 — 경로를 조립·생성하는 3곳(db_setup·config·user_context)을 모두 돌린다.

    CF 헤더 사용자로 create_app 요청을 보내는 테스트는 이걸 써야 실제 `data/users/<uid>` 가 생기지 않는다
    (`load_config(user_id=...)` 도 mkdir 한다 — S3 5단계에서 발견). 반환은 tmp 의 `data/users`.
    """
    import src.db_setup as dbs
    import src.utils.config as cfg
    import src.utils.user_context as uc
    monkeypatch.setattr(dbs, "_PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(cfg, "_PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(uc, "project_root", lambda: tmp_path)
    users = tmp_path / "data" / "users"
    users.mkdir(parents=True)
    return users


@pytest.fixture(autouse=True)
def _origin_guard_enforce(monkeypatch):
    monkeypatch.setenv("ORIGIN_GUARD_MODE", "enforce")
    monkeypatch.delenv("PUBLIC_BASE_URL", raising=False)


# ─────────────────────────────────────────────────────────────────────────────
# 1. 인메모리 (순수 단위 테스트)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def db_conn():
    """인메모리 SQLite DB에 v0.3 테이블 생성 후 연결 반환."""
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys=ON")
    create_tables(conn)
    migrate_db(conn)
    yield conn
    conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# 2. 실 DB 복사 헬퍼
# ─────────────────────────────────────────────────────────────────────────────

def _copy_real_db(user_id: str):
    """실 DB를 temp로 복사하여 Connection 반환. 원본 없으면 None."""
    db_path = get_db_path(user_id, create=False)  # 조회만 — 없는 유저 디렉터리를 만들지 않는다
    if not db_path.exists() or db_path.stat().st_size == 0:  # 0바이트 = 외부 도구가 만든 빈 파일
        return None

    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    shutil.copy2(db_path, tmp.name)

    # WAL/SHM도 복사 (있으면)
    for ext in ("-wal", "-shm"):
        src = Path(str(db_path) + ext)
        if src.exists():
            shutil.copy2(src, tmp.name + ext)

    conn = sqlite3.connect(tmp.name)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn, tmp.name


# ─────────────────────────────────────────────────────────────────────────────
# 3. default 유저 DB
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def db_conn_default():
    """data/users/default/running.db 복사본.

    실 DB가 없으면 테스트 skip.
    읽기/쓰기 모두 가능하지만 원본에는 영향 없음.
    """
    result = _copy_real_db("default")
    if result is None:
        pytest.skip("default 유저 DB 없음: data/users/default/running.db")
    conn, tmp_path = result
    yield conn
    conn.close()
    # temp 파일 정리
    for ext in ("", "-wal", "-shm"):
        p = Path(tmp_path + ext)
        if p.exists():
            p.unlink()


# ─────────────────────────────────────────────────────────────────────────────
# 4. 실 유저 DB (pansongit@gmail.com)
# ─────────────────────────────────────────────────────────────────────────────

_REAL_USER = "pansongit@gmail.com"


@pytest.fixture
def db_conn_user():
    """data/users/pansongit@gmail.com/running.db 복사본.

    실 DB가 없으면 테스트 skip.
    """
    result = _copy_real_db(_REAL_USER)
    if result is None:
        pytest.skip(f"유저 DB 없음: data/users/{_REAL_USER}/running.db")
    conn, tmp_path = result
    yield conn
    conn.close()
    for ext in ("", "-wal", "-shm"):
        p = Path(tmp_path + ext)
        if p.exists():
            p.unlink()


# ─────────────────────────────────────────────────────────────────────────────
# 5. 공통 설정
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_config():
    """테스트용 설정 딕셔너리."""
    return {
        "garmin": {"email": "test@test.com", "password": "testpass"},
        "strava": {
            "client_id": "12345",
            "client_secret": "secret",
            "refresh_token": "rt_test",
            "access_token": "at_test",
            "expires_at": 9999999999,
        },
        "intervals": {"athlete_id": "i12345", "api_key": "apikey_test"},
        "runalyze": {"token": "token_test"},
        "user": {
            "max_hr": 190,
            "threshold_pace_sec_km": 300,
            "rest_hr": 50,
            "weight_kg": 70,
        },
    }


@pytest.fixture(autouse=True)
def _isolated_sync_ledger(tmp_path, monkeypatch):
    """원장(sync_jobs.db)을 테스트별 임시 경로로 격리 — 실 DB 오염 방지."""
    import src.utils.sync_jobs as sj
    monkeypatch.setattr(sj, "_jobs_db_path", lambda uid=None: str(tmp_path / "sync_jobs.db"))
    yield

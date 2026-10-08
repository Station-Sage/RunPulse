"""합성 DB로 Flask 앱 기동 — 사용: python3 scripts/synth_smoke/serve_synth.py <db> <port>

코드는 프로세스 시작 시 한 번 로드되므로 병합·수정 뒤엔 재시작해야 반영된다.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def make_app(db: Path):
    """get_db_path를 db로 고정한 Flask 앱을 만든다(default 계정 DB를 만들지 않도록 create 무시)."""
    import src.db_setup as dbs

    dbs.get_db_path = lambda user_id=None, *, create=True: db
    import src.services.calendar_feed_index as cfi

    cfi.index_path = lambda: db.parent / "calendar_feeds.db"
    from src.web.app import create_app

    return create_app()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("사용: serve_synth.py <db> <port>")
    make_app(Path(sys.argv[1]).resolve()).run(host="127.0.0.1", port=int(sys.argv[2]), debug=False)

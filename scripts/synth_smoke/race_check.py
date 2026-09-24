"""동시 GET 요청 부하 — 사용: python3 scripts/synth_smoke/race_check.py <port> [요청 수]

`before_request`의 migrate_db가 요청마다 돌며 뷰를 재생성하던 레이스(500)의 회귀 확인용.
정상이면 {200: N} 또는 {200: a, 404: b}(활성 플랜 없음) 형태로만 나온다.
"""
from __future__ import annotations

import concurrent.futures as cf
import sys
import urllib.error
import urllib.request
from collections import Counter

URLS = [
    "/api/v1/library/activities?per_page=5",
    "/api/v1/library/activities/100",
    "/api/v1/today",
    "/api/v1/coach/plan/active",
]


def hit(port: str, path: str) -> int:
    try:
        return urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=30).status
    except urllib.error.HTTPError as e:
        return e.code


def main() -> None:
    port = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    with cf.ThreadPoolExecutor(16) as ex:
        results = list(ex.map(lambda i: hit(port, URLS[i % len(URLS)]), range(n)))
    print(Counter(results))


if __name__ == "__main__":
    main()

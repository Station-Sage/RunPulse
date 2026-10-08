"""MCP 원격/공용 코어 — stdio(src/mcp_server.py)와 HTTP(/mcp)가 공유하는 프로토콜·안전 장치.

- protocol.py   : JSON-RPC 처리(허용 도구 집합·연결 팩토리 주입, 프로토콜 버전 협상)
- safe_conn.py  : 읽기 전용 SQLite 연결(ro + query_only + authorizer + 시간 제한)
- policy.py     : 원격 노출 도구 분류(REMOTE_TOOLS / REMOTE_DENIED)
- token_index.py: Bearer 토큰 인덱스(data/mcp_tokens.db, 해시만 저장)
- audit.py      : 호출 감사 로그(mcp_audit)
설계: v0.3/data/phase-7-ui-renewal/ux-review-2026-09/DESIGN-MCP-REMOTE.md
"""

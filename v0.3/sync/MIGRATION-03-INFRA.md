문서 3 (INFRA): requirements.txt, Dockerfile, docker-compose.yml, config.json.example, .gitignore 5개 파일 변경 diff 제시. views_sync.py, sync_ui.py, rate_limiter.py는 변경 불필요 확인.
📄 문서 3: MIGRATION-03-INFRA.md — 인프라/설정/의존성 변경
Garmin 마이그레이션 — 인프라·설정·의존성 변경 상세
작성일: 2026-04-09 | 브랜치: renew/data-architecture
1. requirements.txt
현행garminconnect>=0.2.0garth>=0.4.0변경diff-garminconnect>=0.2.0-garth>=0.4.0+garminconnect>=0.3.1+curl_cffi>=0.7.0+ua-generator>=1.0.0근거- garminconnect 0.3.x는 garth 의존 제거, curl_cffi + ua-generator가 신규 필수 의존성- curl_cffi: Cloudflare TLS fingerprint 우회를 위한 libcurl 바인딩- ua-generator: 랜덤 브라우저 fingerprint 생성
2. Dockerfile
현행dockerfileRUN apt-get update && apt-get install -y --no-install-recommends \    gcc \    libffi-dev \    && rm -rf /var/lib/apt/lists/*변경diff RUN apt-get update && apt-get install -y --no-install-recommends \     gcc \     libffi-dev \+    libcurl4-openssl-dev \+    libssl-dev \     && rm -rf /var/lib/apt/lists/*근거- curl_cffi 빌드에 libcurl 헤더 필요 (wheel이 없는 플랫폼의 경우)- python:3.12-slim 기반 이미지에 libcurl-dev 미포함- 검증: pip install curl_cffi가 wheel로 설치되면 불필요할 수 있으나, ARM64(AWS Graviton) 등에서는 소스 빌드 필요
3. docker-compose.yml
현행yamlvolumes:  - ./.garth:/root/.garth변경diff volumes:-  - ./.garth:/root/.garth+  - ./.garminconnect:/root/.garminconnect+  # 마이그레이션 기간 동안 기존 garth 토큰 읽기용 (제거 예정)+  # - ./.garth:/root/.garth근거- 토큰 디렉터리가 /.garth → /.garminconnect로 변경- 컨테이너 내부 /root/.garminconnect에 마운트- 프로젝트 루트에 .garminconnect/ 디렉터리 생성 필요
4. config.json.example
현행json{  "garmin": {    "email": "your@email.com",    "password": "your_password"  }}변경diff {   "garmin": {     "email": "your@email.com",-    "password": "your_password"+    "password": "your_password",+    "tokenstore": "~/.garminconnect"   },+  "cf": {+    "service_client_id": "xxxxxxxx.access",+    "service_client_secret": "your_cf_service_token_secret_here"+  } }근거- password는 서버에 저장되지 않지만 example에 포함 (초기 CLI 로그인용 안내)- tokenstore 기본 경로 명시로 설정 가독성 향상- cf.service_client_id/secret: CF Zero Trust 대시보드 → Service Auth에서 발급. scripts/garmin_local_sync.py가 CF-Access-Client-Id/Secret 헤더로 VPS POST 시 사용. 미설정 시 서비스 토큰 바이패스 비활성화. (상세: MIGRATION-01-02-A-DESIGN.md §4, §7)

신규 파일 (A안 구현): 상세 설계는 MIGRATION-01-02-A-DESIGN.md 참고
- scripts/garmin_local_sync.py — 로컬 기기(주거용 IP)에서 Garmin 토큰 발급 후 VPS에 업로드하는 CLI 스크립트
5. .gitignore
추가diff+.garminconnect/근거- 토큰 파일 git 추적 방지 (기존 .garth/는 이미 무시되어 있을 것)
6. views_sync.py — 토큰 경로 표시 변경
현행 (L28)pythonfrom src.sync.garmin import check_garmin_connection, _tokenstore_path→ _tokenstore_path 반환값이 /.garth/... → /.garminconnect/...로 자동 변경됨.→ views_sync.py 코드 자체는 변경 불필요, 표시값만 달라짐.
단, _garmin_token_status_html import:pythonfrom .views_settings_garmin import _garmin_token_status_html→ views_settings_garmin.py의 _garmin_token_status_html 내부가 garth → garminconnect로 바뀌면 자동 반영.→ 변경 불필요
7. sync_ui.py — 영향 없음
전수 확인: garth/garminconnect import 없음. 순수 HTML 생성 유틸. 변경 불필요.
8. rate_limiter.py — 영향 없음
전수 확인: garth/garminconnect import 없음. 독립적 rate-limit 로직. garminconnect 0.3.x 내부 retry 없음 확인 → 이중 retry 위험 없음. 변경 불필요.
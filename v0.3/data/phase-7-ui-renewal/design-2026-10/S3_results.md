# S3 결과 (2026-10-14) — 서버 입력·Origin 검증(SRV, ADR-048) + 응답 정책(SEC, ADR-049) + v1 라우트 이동

브랜치 `ccr-8ec9b1bc-q2i3u3`. 설계서 `patterns/server-input-origin-validation.md`·`patterns/security-headers.md`·`bundles/v1-sunset-prep.md`. 롤백 = 단계별 커밋 revert(역순). 미확인은 '미확인'으로 표시. **상태: 구현·로컬 검증 완료(0~11단계), 사용자 확인 대기**(승인된 것은 S3 계획뿐 — 구현 세부 S3-3~S3-11 과 V1-8 해석은 아직 사용자 확인 전).

## 1. S3 결정 (사용자 승인된 것)

| ID | 내용 |
|---|---|
| V1S-12 | (b) `app.py` 비UI 직접 라우트를 `src/api/` Blueprint 로 이동, URL 불변, 삭제는 일몰 단계(S5) |
| V1-8 해석 | '두번째' = `GET /api/v1/dev/users` + `POST /api/v1/dev/switch-user` + MenuDrawer 다이얼로그 — **미확인(사용자 확인 대기)** |
| ENV-1 | Flask·gunicorn 은 `.venv`, 표준 테스트 명령·설치 문서 정정(0단계) |
| S3-1·S3-2 | 승인(운영 `data/users` 점검은 운영에서, 기본값 이견 없음) |

## 2. 단계와 커밋 (1단계 = 1커밋, 모두 push 됨)

| 단계 | 내용 | 커밋 | 결정 기록 |
|---|---|---|---|
| 0 | 승인 기록, ENV-1(CLAUDE.md·install-guide·setup-termux) | `7082428` | S3-1·2 |
| 1 | `register_envelope_handlers` — 뷰 내 HTTP 오류·미처리 예외를 봉투로 | `9aa6399` | |
| 2 | 입력 상수·경계 검증기·쓰기 라우트 4개 적용(체크인·플랜 생성/템플릿·코치) | `ce6a1cb` | S3-3 |
| 3 | `validate_uid`·경로 이탈 차단·`auth_cf` 403+마스킹·`scripts/check_user_dirs.py` | `e4f41ab` | S3-4 |
| 4 | Origin 관문(observe 기본)·세션 쿠키 속성·`/mcp` `same_origin` 재사용 | `caefcfc`, 재점검 `a7930ee` | S3-5 |
| 5 | `/switch-user` v2 이관(dev 엔드포인트·production 404·MenuDrawer 다이얼로그) | `5abd17e` | S3-6 |
| 6 | v1 sync·import 14개 URL → `src/api/` Blueprint 2개 | `9159789` | S3-7 |
| 7 | `/v2` 정적 서빙 분리 `spa_static` | `201f4fd` | S3-8 |
| 8 | 응답 정책(보안 헤더·표면별 CSP)·`/api/v1/csp-report` | `50ba9ad` | S3-9 |
| 9 | favicon·manifest·apple-touch-icon·"새 버전" 알림 | `9091d20` | S3-10 |
| 10 | MenuDrawer 'CSV 내보내기' → v2 내보내기(EXP) 화면(V1-11 b) | `d47fca2` | S3-11 |
| 11 | ADR-048·049, 본 문서, BACKLOG | (이 커밋) | |

## 3. 사용자에게 보이는 변화

- 쓰기 요청(POST 등)은 Origin 관문을 지난다 — **기본은 observe(로그만)이라 차단 없음**. `ORIGIN_GUARD_MODE=enforce` 로 바꿔야 403 `FORBIDDEN_ORIGIN`.
- 잘못된 입력은 400 `INVALID_PARAM`(체크인·플랜 생성/템플릿·코치 4개 라우트), 비JSON 본문은 415. 이전에는 조용히 보정·무시되던 값이 거절될 수 있다.
- 규칙(`[A-Za-z0-9._%+@-]{1,254}`)에 맞지 않는 사용자 식별자는 403 `FORBIDDEN_USER`. 앱 시작 시 규칙 위반 디렉터리는 건너뛴다.
- v1 `/switch-user` 삭제. 개발 환경에서만 MenuDrawer 에 사용자 전환 다이얼로그. production 에서는 `/api/v1/dev/*` 가 404.
- 모든 응답에 공통 보안 헤더 4종. v2·일반 표면 CSP 는 **Report-Only**(깨지지 않음), api·feed 는 `default-src 'none'` enforce.
- `/v2/<없는 자산>` 이 HTML 200 → 404(의도). 딥링크(`/v2/activity/…`)는 그대로 index.html.
- v2 에 favicon·홈 화면 아이콘·manifest, 새 빌드 감지 시 "새로고침" 안내 토스트(자동 새로고침 없음).
- MenuDrawer 'CSV 내보내기' 는 `/v2/data/export` 로 이동(v1 CSV 라우트는 삭제 안 함).
- v1 sync·import URL·응답 포맷 불변(219-rule URL map 이동 전후 동일, 엔드포인트 이름만 `v1_sync.*`·`v1_pages.*`).

## 4. 설계서에 없던 세부 (에이전트가 정함 — 사용자 확인 필요)

S3-3(보조 상한 기본값), S3-4(uid 규칙 범위·심볼릭 링크 거부), S3-5(Origin 관문 정규화·폴백·`/mcp` 판정 변경), S3-6(dev 전환 방식·production 판정 시점), S3-7(Blueprint 분할), S3-8(자산 판정 규칙), S3-9(알 수 없는 값 처리·로그 형식), S3-10(임시 아이콘·알림 동작), S3-11(라벨 유지). 각 행 본문은 `decisions-table.md`.

## 5. 위험·한계

| # | 내용 | 처리 |
|---|---|---|
| R1 | Origin 관문이 observe 라 실제 차단은 아직 없음. 운영에서 `PUBLIC_BASE_URL` 미설정이면 프록시 뒤 정상 요청이 위반으로 집계됨 | **운영 인계**(§6) |
| R2 | `/mcp` Origin 판정이 `request.host` → `public_base_url` 기준으로 변경. 운영 MCP 클라이언트가 브라우저형 Origin 을 보내는 경우 영향 | 미확인 |
| R3 | CSP 는 Report-Only. 누락 출처·`blob:`(createObjectURL 다운로드 등)·인라인 스타일 위반 여부를 실브라우저로 본 적 없음 | 미확인, 2주 관찰 |
| R4 | `csp-report` 가 CF Access 에 막히면 보고가 도착하지 않음(README §5 질문 4 — 이 경우 우회 대상 결정 필요). 도착 확인은 실환경에서만 가능 | 미확인, enforce 전 필수 |
| R5 | 라우팅 단계의 404/405 는 봉투가 아님(`register_envelope_handlers` 는 Blueprint 범위) | 알려진 한계 |
| R6 | 운영 `data/users` 에 규칙 위반 이름·심볼릭 링크 배치가 있으면 해당 사용자가 403 / 시작 시 건너뜀 | `scripts/check_user_dirs.py` 운영 실행 전까지 미확인 |
| R7 | 운영 환경변수(`ORIGIN_GUARD_MODE`·`PUBLIC_BASE_URL`·`APP_ENV`·`CSP_V2_MODE`)를 설명할 기존 문서가 없음(`.env.example`·배포 문서 부재) | 인계 — 문서 위치 미정 |
| R8 | `DevUserSwitch` 는 마운트 시 `/dev/users` 를 호출하므로 운영에서 404 1회가 나감 | 수용(S3-6 ⑤) |
| R9 | 아이콘은 v1 maskable 아이콘 기계적 리사이즈(임시). manifest `crossorigin="use-credentials"` 가 CF Access 뒤에서 동작하는지 미확인. v1 `static/sw.js`·manifest 와의 scope 상호작용 미확인 | 최종 아이콘 디자인 필요 |
| R10 | SvelteKit 은 업데이트 감지 후 내비게이션 로드 실패 시 자체적으로 새로고침(끌 수 없음) — "자동 새로고침 없음" 은 우리 코드 범위에 한함. 실브라우저 동작 미확인 | 미확인 |
| R11 | 브라우저 동작 전반(DevUserSwitch 다이얼로그, UpdateNotice, 아이콘·홈 화면 추가, 메뉴 → EXP 이동) 미확인. 개발 서버·브라우저 미실행, gunicorn 기동 미확인 | 미확인 |
| R12 | 300줄 초과 경고 지속(`helpers.py`·`bg_sync.py`·`app.py` ~500줄). 이번에 `app.py` 는 1159 → 약 500줄로 줄었으나 여전히 초과 | 미배정 |
| R13 | v1 `/activities/export.csv`(`views_export.py`)·v1 sync·import 라우트는 삭제하지 않음(V1S-12 b) | S5, 사용자 허가 후 |

## 6. 운영 인계 (사용자 작업 — 이 샌드박스는 운영 접근 불가)

1. `python scripts/check_user_dirs.py` 를 운영 `data/users` 에서 실행 — `invalid-name`·`symlink-escape` 항목 확인(S3-1, R6).
2. 운영 환경변수 확인·설정: `PUBLIC_BASE_URL`(외부 URL), `APP_ENV=production`, 필요 시 `ORIGIN_GUARD_MODE`·`CSP_V2_MODE`.
3. **Origin 관문 observe 2주** → 로그(`runpulse.security`)에 위반 0건이면 `ORIGIN_GUARD_MODE=enforce`(SRV-8·SEC-10). 봇·스캐너 제외 방식은 README §5 질문 5(미결).
4. **CSP Report-Only 2주** → `runpulse.csp` 로그에서 `grep '\[csp-report\] ext=0'` 집계 0건 확인. **enforce 전 의도적 위반으로 보고 도착 확인 필수**(절차: S3-9 ⑧ — 콘솔에서 인라인 스크립트 삽입). 도착하지 않으면 CF Access 우회 대상 결정(R4).
5. `blob:`/`createObjectURL` 다운로드·인라인 스타일 등이 CSP 위반으로 보고되는지 확인(R3).
6. `/mcp` 외부 클라이언트(Claude 등) 연결 확인(R2).
7. 최종 아이콘 디자인 제공(SEC-11, 별도 에이전트 또는 직접) → `frontend/static/` 교체(R9).

## 7. 열려 있는 항목 (S3 범위 밖, 그대로 유지)

R1 백필 결정(미결, 변동 없음), TXT-1 문구(RC-18·EXP-7·NEW-15… + S3-10 알림 문구·S3-11 라벨), FRS-28, `TEST-PLAN-CREATION-DATE`(기존 간헐 실패, 이번 실행에서는 발생 안 함), README §5 정책 질문 1~3(S4 이후), 질문 4·5(운영 관찰 시 결정).

## 8. 다음 단계로 넘길 것

| 작업 | 단계 | 내용 |
|---|---|---|
| FRS(050)·NRA(051)·TZ: 신선도·비러닝·시간대 | S4 | 사용자 승인 후 계획부터 |
| 레거시 삭제 7종 → v37~v40 + PLN·RC·ADJ·NEW | S5~ | **사용자가 v37 이전에 DB 에서 직접 실행**(백업·건수 확인) |
| EXP·OVL·ERR·A11Y 프런트 | 이후 | |
| v1 라우트·`views_export.py`·`/activities/export.csv` 삭제 | v1 일몰 | 사용자 허가 |
| MenuDrawer `AI 코치`·`SyncPanel` 링크 등 v2→v1 링크 | MENUDRAWER-POST-V1 | V1-5 |

## 9. 검증

- 환경: `.venv`(flask 3.1.3, pytest 9.1.1). 시스템 python3 는 flask 없음(ENV-1).
- 전체 pytest(최종): `3255 passed, 240 skipped`(실패 0). `data/users` 실행 전후 동일(테스트가 실제 사용자 디렉터리를 만들지 않음 — `isolated_users_root` fixture). Pillow 가 `.venv` 에 없어 아이콘 픽셀 검사 2개는 skip(시스템 python3 에서는 통과).
- 프런트: `npm run test:unit` 479 통과, `npm run check` 에러 0 / 경고 38, `npm run build` 성공.
- `check_docs.py`: 오류 0 / 경고 64(S2 말 기준선 63 → +1, 원인 파일 미특정, 필수 검사 아님).
- 변이 확인: 단계별 테스트에서 의도적으로 결함을 넣어 실패하는지 확인(8단계 5종, 9단계 2종 등).
- 테스트 규칙 변경: 쓰기 요청을 보내는 테스트는 `Origin: http://localhost` 헤더 필요(conftest autouse 가 enforce).

# DESIGN — P7-DATA-MENU-ENTRY (상단 ☰ 메뉴 실제 진입점)

상태: 설계 초안 · 코드 변경 없음 · 결정 1건 대기(DECISIONS.md `[P7-DATA-MENU-ENTRY]`)

## 1. 결론 요약

BACKLOG 항목(2026-09 작성)은 "☰ 버튼은 비활성, Data API 없음"을 전제로 한다. 현재 코드와 대조하면
**그 전제가 더 이상 사실이 아니다.** 진입점·API·화면은 이미 구현돼 있다. 따라서 이 설계의 산출물은
"새로 만들 것"이 아니라 (a) 현황 대조표, (b) 남은 문서 불일치, (c) IMPL 항목의 처리 방향이다.

## 2. 현황 대조 (코드 확인)

| BACKLOG 전제 | 현재 코드 | 근거 |
|---|---|---|
| ☰ 버튼 비활성 | 활성. 클릭 시 `MenuDrawer` 열림(데모 모드에선 숨김) | `frontend/src/routes/+layout.svelte` (`menuOpen`, `<MenuDrawer>`) |
| 진입 링크 없음 | 드로어에 데이터(개요·소스 연결·가져오기·내보내기)·설정(데이터 설정·러너 기준값·AI 설정)·바로가기 그룹, 동기화 요약 행, 로그아웃 | `frontend/src/lib/components/MenuDrawer.svelte`, `frontend/src/lib/menuLinks.ts` (`MENU_GROUPS`), `frontend/tests/menuLinks.test.mjs` |
| `/data/settings` 없음 | 존재. 소스 연결·자동 동기화·러너 기준값·AI 설정 카드 + 테마 + MCP 토큰 | `frontend/src/routes/data/settings/+page.svelte` |
| Data API 없음 | `GET /data/sources`, `/data/sources/<p>`, `/data/summary`, `/data/runs`, `/data/sync-state`, `POST /data/sync`, `/data/sync/estimate`, `/data/sync/auto`, `/data/recompute`, `/data/jobs/<id>`, connect/test/disconnect, Garmin 로그인·MFA, import, export, calendar-feed, `/data/settings/ai` | `src/api/routes_data*.py` |
| Data 화면 없음 | `/data`, `/data/sources`, `/data/sync`, `/data/import`, `/data/export`, `/data/settings` (+ `/profile`, `/ai` 링크) | `frontend/src/routes/data/` |

주의: URL 은 문서가 쓰는 `/v2/data/*` 가 아니라 SvelteKit `base` 기준 `/data/*` 다.
TODO: 확인 필요 — `frontend/svelte.config.js` 의 `paths.base` 값과 `/v2` prefix 의 현재 처리.
또한 `/data/settings/profile`·`/data/settings/ai` 라우트 파일은 이번 조회(`+page.svelte` 목록 깊이 2)에서
확인하지 못했다. TODO: 확인 필요.

## 3. 정보 구조 판단 (02 §3 3선 메뉴 원칙과 대조)

02 원칙: "3선은 관리·설정 서랍이지 기능 탭 대체물이 아니다." 현재 드로어는 '바로가기'(활동 목록·훈련 계획·
레이스·웰니스·신발·지표 가이드)까지 담는다. `design-2026-11-features/menudrawer-post-v1.md`(S4-90)에서
"탭에서 두 번 이상 눌러야 닿는 화면"으로 정당화됐고 탭 루트(Today/Library/Coach)는 중복 배치하지 않는다.
02 원칙과 부분 충돌하지만 이미 확정된 결정이므로 이 설계에서 되돌리지 않고, 02 문서를 현재 구조에 맞추는
쪽을 택한다(§4).

## 4. 남은 불일치 (문서)

1. `07-migration-roadmap.md` §7a 의 `[ ] 상단 3선 메뉴 UI` — 이미 구현. 체크 + 근거 기재.
2. `07-migration-roadmap.md` 7d 산출물 `GET /api/v1/data/sources`·`/data/sync`·`/data/settings` — settings 는
   단일 엔드포인트가 아니라 `/data/settings/ai`·`/data/sync/auto` 등으로 분할 구현됨. 명세 갱신.
3. `02-information-architecture.md` 3선 메뉴 항목 목록에 바로가기 그룹 서술 추가.
4. `03f-data.md` §6-A 목업의 4탭 vs 실제 라우트의 가져오기(`/data/import`) 추가 반영.
5. `BACKLOG.md` 의 본 항목과 `P7-DATA-MENU-ENTRY-IMPL`: 전제가 낡았다. `-IMPL` 은 kind=code 라 그대로 두면
   autopilot 이 이미 있는 API·화면을 다시 만들려 할 위험이 있다.

## 5. 확인하지 못한 것

- `03f-data.md` 의 신규 소스 연결 카드(COROS/Polar 등)는 7d 신규 커넥터 선행. `/data/sources` 가 미지원 소스를
  "준비 중"으로 노출하는지 TODO: 확인 필요(`src/services/data_service.py`).
- 드로어 접근성(포커스 트랩·ESC)은 `use:modal` 로 처리되는 것으로 보이나 검증하지 않았다.
- pytest·브라우저 스모크는 이 무인 실행에서 수행하지 않았다(코드 변경 없음).

## 6. IMPL 처리 방향 (선택지는 DECISIONS.md)

권고: `P7-DATA-MENU-ENTRY-IMPL` 을 코드 구현에서 **문서 정합 + 브라우저 스모크 검증**으로 축소한다
(§4 1~4 문서 갱신, 드로어→각 Data 하위 화면 이동 스모크). 신규 API·라우트는 만들지 않는다.

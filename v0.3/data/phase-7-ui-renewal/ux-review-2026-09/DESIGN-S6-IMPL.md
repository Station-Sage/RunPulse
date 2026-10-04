# S6 C4 Provider 매트릭스 쌍 비교 재구축 — 구현 명세

> 작성: 2026-10-04 (product-architect)
> 근거 문서: `21-library-metrics/design.md` §2.5·§3(소스 비교 행)·§4.5·§6·§7.1·§7.2(e)(f)·§7.3 C4·V9·§9 S6, `99-summary.md` 3-8(21:S6), `IMPL-PROGRESS.md` 1-4 "남음: C4 매트릭스 쌍 비교(3-8)"
> 실측(`/tmp/real_copy.db`, 읽기 전용 조회): 최근 84일 canonical 활동은 running 50건, swimming 1건이다. activity-scope에 실제로 있는 비교 후보는 다음과 같다.
> - `training_load`: garmin 353건, intervals 615건 (SEMANTIC_GROUPS에는 `training_load_score`로 잘못 적혀 있어 0건으로 잡힌다)
> - `hrss`(RunPulse) 350건, `normalized_power`: garmin·intervals·strava(73건)
> - `efficiency_factor`(intervals 평균 1.68) / `efficiency_factor_rp`(19.35): 척도가 약 11.5배 다르다
> - `vo2max_activity`(garmin) / `runpulse_vdot`
>
> **실제 데이터가 0건인 멤버**: `trimp`(intervals), `decoupling`(intervals), `suffer_score`(strava), `effective_vo2max`(runalyze).
> daily 데이터: `ctl`·`atl`·`tsb` intervals 370건(5/8에 멈춤), `lthr_self` 177.5 / `lthr_ref`(garmin) 35건, `garmin_ftp`, intervals `icu_ftp` 289(고정값).
>
> 상태: 설계 제안이며 코드는 바꾸지 않았다. **(사용자 승인 필요)** 표시가 붙은 항목은 사용자가 결정한다.

---

## 1. 범위

**포함 (21:S6)**
1. 매트릭스 서비스 재작성. 같은 canonical 러닝 그룹 안의 쌍만 비교하고, 중앙값·IQR·n을 계산하며, 기간에 따라 결과가 달라지게 한다(§7.3 C4).
2. `GET /library/providers/matrix?days=` 응답을 새 형태로 바꾼다(§7.2(e)). 호출처는 `routes/library/providers/+page.ts` 하나뿐이므로 하위 호환은 필요 없다.
3. 신규 `GET /library/providers/pairs?group=&days=`(§7.2(f))와 그룹 상세 라우트 `/library/providers/[group]`.
4. 매트릭스 표 규격 적용: 단위, 오른쪽 정렬, 차이 칩, 행 링크, ★ 이유를 화면에 노출, `N/D 이후 없음`. 기간 chip은 replace로 동작.
5. 메트릭 상세의 "Provider 비교" 버튼을 해당 행의 그룹 상세로 연결한다. 해당 그룹이 없으면 버튼을 숨긴다.

**제외**
- [대표 소스 변경]: 쓰기 동작이라 설정 과업으로 넘긴다(§10 F-UX-07 보류).
- 활동별 소스 비교 탭(`/library/:id/providers`): 화면 변경은 없다. 단 §3.3의 SEMANTIC_GROUPS 이름 교정이 들어가면 그 영향은 받는다.
- 재매칭 시 그룹 재계산 트리거(1-4 남음), Intervals daily CTL 인제스트 복구(F-DATA-12), S7 접근성 총점검.

## 2. 화면·컴포넌트

### 2.1 `/library/providers` (매트릭스, Library 1단 서브탭 "소스 비교")

**Level 0 — 헤더 한 줄(서버 문구):** "같은 러닝을 소스마다 다르게 계산해요. ★ 값을 판단에 씁니다." 그 아래 캡션 "최근 4주 · 러닝 14건 비교"를 둔다.

**Level 1 — 표.** 섹션 3개로 나누고 서버가 정한 순서를 그대로 따른다. 섹션 이름은 다음과 같다.
- ① **같은 러닝 비교** (`kind=pair_activity`)
- ② **기준값·프로필** (`kind=profile`, `pair_daily`)
- ③ **정의가 달라 비교하지 않는 지표** (`kind=definition`, 기본 접힘)

```
지표 ›          Garmin    Intervals   RunPulse    차이(중앙)      n
훈련 부하 ›     ★98 AU    58 AU       52 AU       척도 ×1.9       14
정규화 파워 ›   ★241 W    240 W       —           비슷함 ±1%      11
LTHR ›          168 bpm   —           ★178 bpm    +10 bpm         프로필
CTL ›           5/8 이후 없음         ★72.7       겹친 날 없음    —
VO2max·VDOT     53        —           44.5        정의 다름 ⓘ     —
```

- **데스크톱:** `<table>`, `max-w-[760px]`. 숫자는 오른쪽 정렬에 `tabular-nums`를 쓴다. 단위는 값 뒤에 작게 붙인다(§C4).
- **모바일(390px):** 행 카드로 바꾼다.
  - 1줄: 라벨과 차이 칩
  - 2줄: ★ 값을 크게
  - 3줄: 나머지 소스를 `Garmin 98 · Intervals 58`처럼 작게
- **열 구성:** 기간 안에 값이 하나라도 있는 provider만 열로 둔다. 순서는 서버 `providers[]`를 따른다.
- **셀 상태:**
  - 값 없음: `—`
  - `stale`: `5/8 이후 없음` (§4.5 확장. 날짜는 `formatDateShort`)
  - `estimated`: `추정` 배지
- **★ 이유:** ★이나 차이 칩을 탭하면 행 아래에 1줄 설명을 펼친다(`aria-expanded`). title 속성은 쓰지 않는다. 문구는 서버 `preferred.reason_text`, `diff.explain_text`를 그대로 쓴다.
- **행 탭:** `/library/providers/{group}?days=` push. `definition` 행은 탭하면 정의 설명을 펼치고, 이동 링크는 없다.
- **기간 chip** [4주][8주][12주]: `?days=`로 **replace**(`goto(..., {replaceState, noScroll, keepFocus})`). 현재 코드는 push라서 수정 대상이다.
- **한 소스만 있는 행:** 표에서 뺀다. 표 아래에 접힌 1줄 "비교 상대가 없는 지표 3개 ›"를 두고, 펼치면 "TRIMP — RunPulse만 수집" 형식으로 보여 준다. **(사용자 승인 필요: §8-3)**

### 2.2 `/library/providers/[group]` (그룹 상세, 신규 2단)

- **브레드크럼(48px, S4 문법):** `Library › 소스 비교 › 훈련 부하`. ‹는 sessionStorage에 저장한 매트릭스 URL로 돌아간다. 저장된 `?days`가 유지된다(`libraryNav.ts` 재사용).
- **Level 0 요약 1문장(서버 `summary_text`):** 의미를 먼저 말하고 수치는 괄호에 둔다.
  - scale 예: "Garmin은 같은 러닝을 RunPulse보다 보통 1.9배 높게 계산해요 (14쌍, 1.6–2.2배)"
  - same 예: "두 소스 값이 거의 같아요 (중앙 차이 +1%, 11쌍)"
- **정의 블록:** provider마다 1줄씩 쓴다(서버 `definitions{}`). 예: `Garmin = EPOC 기반`, `RunPulse = HRSS(LTHR 기준)`.
- **겹친 시계열** `ProviderPairChart`:
  - x축은 날짜, provider별 점을 §C7 `--series-1/2/3`으로 찍는다. 같은 그룹 쌍은 세로 연결선으로 잇는다.
  - scale 행에는 토글 [원값 | 비율]을 둔다. 비율 모드는 쌍별 a/b를 찍고 중앙선을 긋는다.
  - §C1 ChartScrub(`lib/chart/scrub.ts`)으로 스크럽하고, 점을 탭하면 아래 목록의 해당 행이 강조된다.
- **쌍 목록:** 열은 날짜(`9/27(토)`), 활동(이름·`9.3km`), provider별 값, 쌍 차이다. 서버 `outlier=true`인 행에는 `평소와 다름` InfoTag를 붙인다. 행 탭은 `/library/{canonical_id}/providers` push.
- **profile 행:** 쌍 목록 대신 "값이 바뀐 날" 목록을 보여 준다(provider별 계단 차트). `pair_daily`(CTL)는 날짜 쌍 목록이다.
- **하단:** ★ 규칙 1줄 "기간 내 러닝 primary_source 최빈값(Garmin 11/14)".

### 2.3 컴포넌트·파일 (frontend/src)

| 파일 | 변경 |
|---|---|
| `routes/library/providers/+page.{svelte,ts}` | 새 응답 타입, 섹션 3개, 기간 chip replace, 제목 `소스 비교 · RunPulse`. 현재 헤더 "Provider 정체성 매트릭스"는 삭제(라벨 규칙) |
| `routes/library/providers/[group]/+page.{svelte,ts}` | **신규**. pairs API 1개만 await(§C5) |
| `lib/components/ProviderMatrix.svelte` | **신규**. 기간 매트릭스 표와 카드. `ProviderComparison.svelte`(단일 활동 탭)는 데이터 모양이 달라서 건드리지 않는다. 설계 §7.1의 "ProviderComparison 수정"을 이렇게 분리하는 것을 제안한다(§8-5) |
| `lib/components/ProviderPairChart.svelte`·`ProviderPairList.svelte` | **신규** |
| `lib/providerMatrix.ts` | **신규** 순수 함수: `visibleProviders(rows)`, `cellText(cell, fmt)`, `rowHref(row, days)`, `pairSeries(pairs, mode)`, `periodHref(days)` |
| `lib/api/providers.ts`·`lib/types/index.ts` | `getProviderMatrix(days)`(threshold 인자 삭제), `getProviderPairs(group, days)`, 타입 `ProviderMatrixData`·`ProviderPairsData` |
| `routes/library/metrics/[slug]/+page.svelte` | "Provider 비교" → `compare_group`가 있으면 "{provider} 값과 비교 →"로 `/library/providers/{group}?days=28` push. 없으면 숨김 |

**프론트 금지 사항 (§8 원칙):**
- 임계값 상수: 15%, n<3, 30일 stale, IQR 이상치 기준 모두 서버가 판정한다.
- 정의·이유 문구를 프론트에서 하드코딩하는 것.
- 기존 `discrepancyThreshold={5}` prop은 매트릭스 경로에서 제거한다.

포맷은 행의 `format` 키(registry 포맷 키와 같은 이름)로 `formatMetric`을 호출한다. hex 하드코딩은 금지한다.

## 3. API·서비스

### 3.1 행 정의 SSOT — 신규 `src/utils/provider_matrix_rows.py` (위치는 system-architect가 확정)

SEMANTIC_GROUPS는 활동 상세 2곳(`provider_comparison_service`, `activity_detail_service`)이 공유한다. 그래서 그것을 재정의하지 않고 **매트릭스 전용 행 정의를 따로 둔다**.

행 필드는 `{key, label, unit, format, kind, members:[(metric, provider, scope)], compare, definitions:{provider: 한 줄}, metric_slugs:[...]}`이다.

**kind (비교 방식)**

| kind | 표본 | 셀 | 차이 |
|---|---|---|---|
| `pair_activity` | 기간 내 canonical 러닝 그룹 | provider별 중앙값과 최신값 | 쌍별 (a−b)/b의 중앙값·IQR·n |
| `pair_daily` | 같은 날짜 daily 쌍 | 같음 | `compare=scale`이면 a/b 비율의 중앙값 |
| `profile` | 각 provider의 기간 말 최신 daily 값 | 최신값과 기준일 | 절대 차이(`+10 bpm`). n은 "프로필"로 표시 |
| `definition` | — | 최신값 | 비교하지 않음. 정의 설명만 |

**compare 키:** `same`은 % 차이와 ⚠를 쓴다. `scale`은 척도 비율 ×r만 보여 주고 ⚠는 없다.

**초기 행 (실측에 근거)**
- `training_load`: garmin `training_load` / intervals `training_load` / runpulse `hrss`. pair_activity, **scale** (§8-1).
- `normalized_power`: garmin / intervals / strava. pair_activity, same.
- `lthr`: runpulse `lthr_self` / garmin `lthr_ref`. profile.
- `hrmax`: `hrmax_self` / `hrmax_ref`. profile.
- `threshold_power`: intervals `icu_ftp` / garmin `garmin_ftp` / runpulse `critical_power`. profile, W.
- `ctl`: runpulse / intervals. pair_daily, scale.
- `vo2max_vdot`: garmin `vo2max_activity` / runpulse `runpulse_vdot` / daily `race_pred_vdot`. definition.
- `efficiency_factor`: intervals / runpulse. 환산 규칙이 확정되기 전에는 definition (§8-2).
- 데이터 0건 멤버(trimp·decoupling·relative_effort의 strava·runalyze vo2max): 정의는 유지한다. 한 소스만 있으면 §2.1 "비교 상대 없음" 목록으로 간다.

### 3.2 서비스 — `src/services/provider_matrix_service.py` 재작성 (300줄 초과 시 `provider_pairs_service.py`로 분리)

ADR-009는 Calculator에 해당한다. 이 모듈은 서비스라서 SQL을 직접 쓸 수 있다. 다만 canonical 판정은 `v_canonical_activities`와 `src/utils/canonical.py` 규칙을 재사용하고, 러닝 판정은 `src/utils/activity_types`의 정규화를 쓴다(수영 제외).

| 함수 | 역할 |
|---|---|
| `running_groups(conn, start, end)` | canonical 러닝 그룹 목록 `[{group_key, canonical_id, date, name, distance_m, sibling_by_source}]` |
| `collect_activity_values(conn, groups, row)` | 그룹별 `{provider: value}`. RunPulse 값은 canonical id에서만, 외부 provider 값은 `source == provider`인 사본에서 가져온다(같은 소스 사본이 여럿이면 id가 가장 작은 것) |
| `collect_daily_values(conn, start, end, row)` | `{date: {provider: value}}` |
| `summarize_pairs(pairs, a, b, compare)` | `{n, median, iqr, status, status_label, explain_text}`. n<3이면 `insufficient`. same에서 \|median\|>`row.threshold_pct`(기본 15)이면 `differs` |
| `cell_summary(values, end)` | `{median, latest, last_date, stale}`. stale은 마지막 값이 기간 끝 30일 전보다 앞선 경우 |
| `preferred(conn, groups, available)` | 기존 `_mode_primary_source`·`_preferred_provider` 재사용. `reason_text` 생성 |
| `get_matrix(conn, days, today)` | 행 조립. 섹션 순서와 `providers[]` 순서를 정하고, 한 소스만 있는 행은 `single_source[]`로 분리 |
| `get_pairs(conn, group, days, today)` | 그룹 상세. pairs, 이상치(IQR×1.5 밖이면 `outlier`), `summary_text` |

- 쌍의 기준 b: 행에 RunPulse가 있으면 RunPulse, 없으면 ★ provider다. 3소스 행은 `diffs[]`에 모든 쌍을 담는다. 대표 `diff`는 \|median\|이 가장 큰 쌍이고, 칩에는 `Garmin↔RunPulse`처럼 쌍을 표기한다.
- `today` 인자를 주입해서 테스트가 날짜에 고정되도록 한다(현재는 `date.today()` 직접 호출).

### 3.3 기존 정의 교정
`metric_groups.SEMANTIC_GROUPS.training_load`에서 `("training_load_score","intervals")`를 `("training_load","intervals")`로 바꾼다. 이렇게 하면 활동 소스 비교 탭에 Intervals 값 615건이 나타난다. 이름 버그 수정이지만 다른 화면이 바뀌므로 **(사용자 승인 필요: §8-4)**.

rtti·wlei를 빼는 것은 §7.3 C4-5에 있지만, 활동 탭 표시가 바뀌므로 이 S6에서는 매트릭스 행 정의에만 적용한다.

### 3.4 라우트 (`src/api/routes_library.py`)
- `GET /library/providers/matrix?days=`: `days ∈ {28,56,84}`, 그 밖의 값이면 400 `INVALID_PARAM`. `discrepancy_threshold` 파라미터는 삭제한다.
  - 응답: `{days, sport:"running", sample_n, header_text, providers[], sections:[{key,label,rows[]}], single_source[], state}`
  - row: `{key, label, unit, format, kind, compare, cells:{p:{median,latest,last_date,stale,estimated}}, pairs_n, diff, diffs[], preferred:{provider,reason_text}, href_group}`
- `GET /library/providers/pairs?group=&days=`: 그룹을 모르면 404 `NOT_FOUND`. days 규칙은 위와 같다.
  - 응답: `{row(위 형태), summary_text, definitions, pairs:[{date, canonical_id, name, distance_m, values:{p:v}, diff_pct|ratio, outlier}], state}`
- `GET /library/metrics/:slug`: 응답에 `compare_group:{key,label,provider}|null`을 추가한다. 행 정의의 `metric_slugs`로 역매핑한다.
- DB 없음 503은 현행 유지. **DB 스키마 변경은 없다.**

## 4. 빈·로딩·오류 상태

| 상황 | 처리 |
|---|---|
| 로딩 (매트릭스) | 섹션 헤더와 행 6개를 최종 치수로 그린 스켈레톤(`Skeleton.svelte`, CLS ≤0.05). 기간 전환 중에는 기존 표를 유지하고 §C5 진행바만 표시 |
| 로딩 (그룹 상세) | 요약 1줄, 차트 높이 예약(모바일 180px), 목록 행 5개 |
| 기간 내 러닝 0건 | 200 `state:"no_data"` → "최근 {4주}에 러닝 기록이 없어요" + [기간 늘리기](다음 기간 chip). 12주에서는 버튼을 숨기고 [동기화 상태 보기]를 둔다 |
| 행은 있으나 쌍 n=0 | 차이 칸 `겹친 기록 없음`. 그룹 상세는 "이 기간에 두 소스가 모두 기록한 러닝이 없어요" + [기간 늘리기] |
| n<3 | `표본 부족 (n=2)` 무채색 칩. ⚠ 없음 |
| stale 셀 | `5/8 이후 없음`. 그룹 상세 요약에 "Intervals 값은 5월 8일 이후 들어오지 않았어요" |
| 오류 | §C5 블록 오류 `불러오지 못했어요 · [다시 시도]`. 400은 `?days=28`로 replace 보정. 404 그룹은 `+error.svelte` "없는 비교 항목이에요" + [소스 비교로] |

"데이터 없음"(200)과 "불러오기 실패"(오류)는 문구와 아이콘으로 구분한다(§C5).

## 5. 접근성
- 데스크톱 표:
  - `<table>`에 `<caption class="sr-only">소스별 지표 비교, 최근 4주 러닝 14건</caption>`를 둔다.
  - 열 머리는 `<th scope="col">`, 지표명은 `<th scope="row">`.
  - 행 이동은 지표명 셀 안의 `<a>`로 한다. 행 전체 클릭은 보조 수단이다.
- ★은 시각 기호 옆에 `<span class="sr-only">대표값</span>`을 둔다. 차이 상태는 색만으로 전달하지 않는다. 칩 텍스트(`차이 큼 +24%`)가 기본이다(§C7).
- 기간 chip은 `role="group" aria-label="비교 기간"`, 각 chip은 `aria-pressed`. 타깃은 44px 이상이다.
- 펼침 설명(★·차이·definition 행)은 `<button aria-expanded aria-controls>`로 만들고, Esc로 닫는다.
- 차트:
  - §C1 키보드 스크럽(←/→)과 `aria-live` 판독을 쓴다.
  - 동적 `aria-label` 예: "훈련 부하 4주: Garmin 중앙 98, RunPulse 중앙 52, 14쌍, Garmin이 1.9배 높음".
  - 쌍 목록이 같은 정보를 담은 텍스트 대체물 역할을 한다.
- 모바일 카드 목록은 `role="list"`. 각 카드의 접근성 이름은 "훈련 부하, 대표 Garmin 98 AU, 척도 1.9배"다.

## 6. 테스트 계획 (함수당 최소 1개)

**pytest — `tests/test_provider_matrix_service.py` 재작성 + `tests/test_provider_pairs.py`**

| # | 대상 | 케이스 |
|---|---|---|
| 1 | `running_groups` | 같은 날 수영과 러닝이 있으면 러닝만 나온다(V9). trail·treadmill 포함 |
| 2 | `collect_activity_values` | RunPulse 값은 canonical에서만 온다(비대표 사본 값은 무시). Garmin 값은 garmin 사본에서 온다 |
| 3 | `collect_daily_values` | 날짜 쌍을 정렬한다. intervals 결측일은 쌍에서 제외 |
| 4 | `summarize_pairs` | n=2이면 insufficient·diff null. same +20%이면 differs. +10%이면 similar. scale에서는 ratio 중앙값·IQR |
| 5 | `cell_summary` | 마지막 값이 40일 전이면 stale·last_date |
| 6 | `preferred` | 최빈 primary_source, 동률이면 `_SOURCE_PRIORITY`. `reason_text`에 "11/14" 포함 |
| 7 | `get_matrix` | days 28과 84에서 pairs_n이 다르다(V9). training_load 행에 Intervals 셀이 있다. 한 소스만 있으면 `single_source`로 간다 |
| 8 | `get_pairs` | IQR 이상치에 outlier. 없는 group은 None |
| 9 | 행 정의 | 모든 행이 필수 키를 갖는다. kind·compare 값이 유효하다. `metric_slugs`는 registry에 실재한다 |
| 10 | API | matrix 200, days=30이면 400, pairs의 미지 그룹은 404, `/library/metrics/training_load`의 `compare_group` 존재 |
| 11 | SEMANTIC_GROUPS 교정 (승인 시) | 활동 소스 비교에 intervals training_load 셀이 나온다 |

**프론트 단위 — `frontend/tests/providerMatrix.test.mjs`**
`visibleProviders`(빈 열 제거·서버 순서 유지), `cellText`(stale·추정·—), `rowHref`(days 승계), `pairSeries`(원값/비율 모드, 결측 provider 제외), `periodHref`.

**Playwright — `pw/s6_providers.mjs`** (실 DB 사본)
- 4주→12주 전환 시 pairs_n이 바뀌고 히스토리가 늘지 않는다.
- 행 탭 → 그룹 상세 → 쌍 행 탭 → 활동 소스 비교 → 뒤로 두 번 → 매트릭스에서 days가 유지된다.
- 390px에서 가로 넘침 0, 콘솔 에러 0.

**회귀 실행:** `pytest tests/`, `npm run test:unit && npm run check && npm run build`, `check_docs.py`, `check_data_consistency.py`.

## 7. 구현 단위 (순서)

| # | 단위 | 산출 | 의존 |
|---|---|---|---|
| U1 | 행 정의 SSOT와 테스트 9 | `provider_matrix_rows.py` | §8-1·2 결정 |
| U2 | 서비스 수집·요약 함수 | `running_groups`~`preferred`, 테스트 1–6 | U1 |
| U3 | `get_matrix` + matrix API 새 형태·400 | 테스트 7·10 | U2 |
| U4 | `get_pairs` + pairs API, metrics `compare_group` | 테스트 8·10 | U2 |
| U5 | 프론트 타입·API·`providerMatrix.ts`(+단위 테스트) | | U3·U4 |
| U6 | `ProviderMatrix` + 매트릭스 페이지(섹션·카드·펼침·chip replace·상태) | | U5 |
| U7 | `[group]` 라우트, `ProviderPairChart`·`List`, 브레드크럼 | | U5 |
| U8 | 메트릭 상세 링크 교체 | | U4·U5 |
| U9 | (승인 시) SEMANTIC_GROUPS 이름 교정과 테스트 11 | | 독립 |
| U10 | Playwright, ADR-021(매트릭스 kind·compare 규칙), IMPL-PROGRESS·BACKLOG·files_index 갱신 | | U6–U8 |

## 8. 열린 결정 (사용자 판단)

1. **(사용자 승인 필요) 훈련 부하의 비교 방식.**
   - 원설계 §2.5는 `+80% ▲` % 차이로 표시한다.
   - Garmin(EPOC)·Intervals(HR 부하)·HRSS는 정의가 다른 양이라서, 이 안은 `scale`로 바꿔 "척도 ×1.9 (IQR)"를 표시하고 ⚠를 내지 않는다. 비율이 안정적인지가 정보다.
   - 설계를 바꾸는 사안이다.
2. **(사용자 승인 필요) EF 처리.** RunPulse 19.35와 Intervals 1.68은 척도가 약 11.5배 다르다. 원설계의 "÷1000 환산"은 실측과 맞지 않는다. 데이터 전문가가 정의를 확인하기 전까지 `definition` 행으로 둔다.
3. **(사용자 승인 필요) 한 소스만 있는 행.** 표에서 빼고 "비교 상대가 없는 지표" 접힘 목록으로 보낸다. 대안은 `—` 셀로 표에 남기는 것이다.
4. **(사용자 승인 필요) SEMANTIC_GROUPS의 `training_load_score`→`training_load` 교정.** 활동 소스 비교 탭에도 Intervals 값이 새로 보이게 된다. rtti·wlei 제외는 매트릭스에만 적용한다.
5. 컴포넌트 분리. 설계 §7.1은 `ProviderComparison` 수정이지만, 이 안은 신규 `ProviderMatrix`를 만들고 활동 탭 컴포넌트는 그대로 둔다. 구현 판단이며 확인만 받으면 된다.
6. 대표 차이 쌍 선택. 3소스 행에서 칩에 \|median\|이 가장 큰 쌍을 보일지, ★ 대 RunPulse 쌍으로 고정할지 정해야 한다.
7. 이상치 기준(IQR×1.5)과 stale 30일은 서버 상수로 두고 ADR-021에 기록한다. 항목별 조정이 필요한지 정해야 한다.

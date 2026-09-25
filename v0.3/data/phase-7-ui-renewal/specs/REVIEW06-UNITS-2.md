# REVIEW-06 반영 유닛 명세 2 (autopilot 전용, 프론트 전용)

`REVIEW-06-design-agent-review.md` §5의 6·5(일부)·7·8(일부)·9·10 중 **프론트만으로 가능한 부분**. 백엔드가 필요한 항목(예측 기록 근거 드릴다운, 활동의 CTL Δ·유사 활동 비교, 병합 소스 수)은 이번 범위 밖이다.
**코드·문구·클래스는 그대로 구현한다. 바꾸고 싶으면 DECISIONS.md에 사유를 적고 중단.** 순수 모듈은 다른 모듈을 런타임 import하지 않는다(타입 import만 허용). 검증: `cd frontend && npm install && npm run test:unit && npm run check && npm run build`.

## 유닛 A — P7-IMPL-METRICS-MEANING (메트릭에 의미를 붙이고 DB 덤프 감각 제거)

1. 신규 `frontend/src/lib/metricMeaning.ts`:

```ts
export type MeaningStatus = 'excellent' | 'good' | 'neutral' | 'caution' | 'poor';
export interface Meaning {
	status: MeaningStatus;
	note: string;
}

export const STATUS_TEXT_CLASS: Record<MeaningStatus, string> = {
	excellent: 'text-semantic-green',
	good: 'text-semantic-teal',
	neutral: 'text-fg-secondary',
	caution: 'text-semantic-amber',
	poor: 'text-semantic-red'
};

// cuts: [상한(미만), 상태, 문구] 순서대로 검사, 모두 넘으면 last
function band(v: number, cuts: [number, MeaningStatus, string][], last: [MeaningStatus, string]): Meaning {
	for (const [max, status, note] of cuts) if (v < max) return { status, note };
	return { status: last[0], note: last[1] };
}

// 개인 기준선 없이 말할 수 있는 것만 해석한다 — 근거 없는 라벨을 붙이지 않는다(원칙 1).
export function meaningFor(name: string, value: number | null | undefined): Meaning | null {
	if (value == null || !Number.isFinite(value)) return null;
	switch (name) {
		case 'tsb':
			return band(value, [[-20, 'poor', '과부하'], [-10, 'caution', '피로 누적'], [5, 'neutral', '균형'], [25, 'excellent', '레이스 최적']], ['caution', '휴식 과다']);
		case 'utrs':
		case 'crs':
			return band(value, [[40, 'poor', '낮음'], [60, 'neutral', '보통'], [80, 'good', '좋음']], ['excellent', '매우 좋음']);
		case 'cirs':
			return band(value, [[30, 'good', '낮음'], [50, 'neutral', '보통'], [70, 'caution', '주의']], ['poor', '높음']);
		case 'acwr':
			return band(value, [[0.8, 'caution', '저부하'], [1.3, 'good', '적정'], [1.5, 'caution', '주의']], ['poor', '위험']);
		case 'training_effect_aerobic':
		case 'training_effect_anaerobic':
			return band(value, [[1, 'neutral', '효과 미미'], [2, 'neutral', '체력 유지'], [3, 'good', '체력 개선'], [4, 'excellent', '큰 개선'], [5, 'caution', '매우 높은 자극']], ['poor', '과도한 자극']);
		case 'aerobic_decoupling':
		case 'aerobic_decoupling_rp':
			return band(Math.abs(value), [[5, 'excellent', '유산소 안정'], [8, 'good', '양호'], [10, 'neutral', '보통']], ['caution', '심박 드리프트']);
		default:
			return null;
	}
}

const LABELS: Record<string, string> = {
	ctl: '체력 (CTL)',
	atl: '피로 (ATL)',
	tsb: '폼 (TSB)',
	acwr: '급성/만성 부하비 (ACWR)',
	utrs: '훈련 준비도 (UTRS)',
	cirs: '부상 위험도 (CIRS)',
	crs: '복합 준비도 (CRS)',
	rec: '러닝 효율 (REC)'
};

// 내부 식별자 "(parent: xxx)"는 사용자 화면에 노출하지 않는다.
export function displayLabel(name: string, label: string): string {
	return LABELS[name] ?? label.replace(/\s*\(parent:[^)]*\)/g, '').trim();
}

// UTRS/CIRS 구성요소 같은 하위 메트릭 — 그리드에서는 숨기고 상위 메트릭의 분해 시트에서 본다.
export function isComponentMetric(label: string): boolean {
	return /\(parent:/.test(label);
}

// 값이 전부 같은 스파크라인은 정보가 없다(캡 걸린 값·미계산 가능성).
export function isFlat(series: (number | null)[]): boolean {
	const v = series.filter((x): x is number => x != null);
	return v.length >= 2 && v.every((x) => x === v[0]);
}
```

   `frontend/tests/metricMeaning.test.mjs`(신규, `scoreRing.test.mjs`와 같은 import 스타일): `meaningFor('tsb', 8.8)` → `{status:'excellent', note:'레이스 최적'}`; `meaningFor('tsb', -25).note === '과부하'`; `meaningFor('tsb', 30).note === '휴식 과다'`; `meaningFor('utrs', 64.7).note === '좋음'`; `meaningFor('utrs', 85).status === 'excellent'`; `meaningFor('cirs', 25).status === 'good'`; `meaningFor('acwr', 0.76).note === '저부하'`; `meaningFor('acwr', 1.0).note === '적정'`; `meaningFor('training_effect_aerobic', 4.5).note === '매우 높은 자극'`; `meaningFor('training_effect_aerobic', 3.2).note === '큰 개선'`; `meaningFor('aerobic_decoupling', -6).note === '양호'`(절댓값); `meaningFor('trimp', 200) === null`; `meaningFor('tsb', null) === null`; `displayLabel('tsb','Training Stress Balance') === '폼 (TSB)'`; `displayLabel('utrs_tsb','UTRS 구성요소 - TSB 정규화값 (parent: utrs)') === 'UTRS 구성요소 - TSB 정규화값'`; `isComponentMetric('X (parent: utrs)') === true`, `isComponentMetric('폼') === false`; `isFlat([100,100,100]) === true`, `isFlat([100,null,99]) === false`, `isFlat([100]) === false`.
2. `frontend/src/lib/types/index.ts`의 `MetricCellProps`에 `note?: string;` 추가(`status?: SemanticStatus;` 다음 줄). `frontend/src/lib/components/MetricCell.svelte`: props 구조분해에 `note`를 추가하고, 상태 줄의 `{#if status}<span aria-hidden="true">●</span>{statusLabel}{/if}`를 `{#if status}<span aria-hidden="true">●</span>{note ?? statusLabel}{/if}`로 바꾼다(그 외 변경 금지).
3. `frontend/src/routes/library/metrics/+page.svelte`:
   - `import { meaningFor, displayLabel, isComponentMetric, isFlat, STATUS_TEXT_CLASS } from '$lib/metricMeaning';`
   - `visibleCategories`의 `.map(...)` 안에서 카테고리의 `metrics`를 만든 뒤 `isComponentMetric(m.label)`인 항목을 제외한다(기존 provider 필터와 함께 `.filter((m) => !isComponentMetric(m.label))`).
   - 카드의 라벨 `{m.label}` → `{displayLabel(m.name, m.label)}`.
   - 값 줄 아래(스파크라인 위)에 `{@const mean = typeof m.value === 'number' ? meaningFor(m.name, m.value) : null}`로 계산해 `{#if mean}<span class="text-[11px] {STATUS_TEXT_CLASS[mean.status]}">● {mean.note}</span>{/if}`.
   - Provider 배지(`{#if m.provider} … {/if}`)는 `availableProviders.length > 1`일 때만 렌더한다(`{#if m.provider && availableProviders.length > 1}`).
   - 스파크라인: `{#if m.sparkline.length > 1}` 블록을 `{#if m.sparkline.length > 1 && !isFlat(m.sparkline)}<Sparkline …/>{:else if m.sparkline.length > 1}<span class="text-[10px] text-fg-muted">변동 없음</span>{/if}`로 바꾼다.

## 유닛 B — P7-IMPL-ACTIVITY-MEANING (활동 상세 핵심 메트릭 해석 + 스플릿 범례; 유닛 A 이후)

1. `frontend/src/routes/library/[id]/+page.svelte`: `import { meaningFor } from '$lib/metricMeaning';` 후 핵심 메트릭 그리드의 `<MetricCell …/>`에 `status={meaningFor(m.metric_name, m.numeric_value)?.status}`와 `note={meaningFor(m.metric_name, m.numeric_value)?.note}` 두 prop을 추가한다(그 외 prop 변경 금지).
2. `frontend/src/lib/components/SplitBars.svelte`: 헤더 `<p class="text-xs uppercase …">km 스플릿 …</p>` 바로 아래에 범례를 추가:
   `<div class="flex flex-wrap gap-x-3 gap-y-1 text-[10px] text-fg-muted"><span class="flex items-center gap-1"><i class="inline-block h-2 w-2 rounded-sm" style="background:#10b981"></i>최고 구간</span><span class="flex items-center gap-1"><i class="inline-block h-2 w-2 rounded-sm" style="background:#3b82f6"></i>평균보다 빠름</span><span class="flex items-center gap-1"><i class="inline-block h-2 w-2 rounded-sm" style="background:#f59e0b"></i>평균보다 느림</span>{#if hasHr}<span>· 우측: 평균 심박</span>{/if}{#if hasElev}<span>· 고도 변화</span>{/if}</div>`.

## 유닛 C — P7-IMPL-COACH-FOLLOWUP (후속 질문·레이스 맥락 주제·규칙 기반 표기 강화)

1. 신규 `frontend/src/lib/coachSuggestions.ts`(순수):

```ts
export interface GoalLite {
	name: string;
	days_left: number;
	target_time_sec: number | null;
}

const DEFAULT_TOPICS = ['오늘 훈련 조언', '레이스 전략', '부상 위험 확인', '훈련 분석'];

// Coach 홈 주제 칩 — 목표 레이스가 있으면 국면에 맞춘 질문을 앞에 둔다.
export function homeTopics(goal: GoalLite | null): string[] {
	if (!goal) return DEFAULT_TOPICS;
	const phase = goal.days_left <= 21 ? '테이퍼는 언제부터 어떻게 할까?' : '레이스까지 어떻게 훈련을 쌓을까?';
	const topics = ['오늘 훈련 조언', phase];
	if (goal.target_time_sec != null) topics.push('목표 기록 가능할까?');
	topics.push('부상 위험 확인');
	return topics.slice(0, 4);
}

// 답변에 붙은 근거 메트릭 이름으로 다음 질문을 제안한다(최대 3개, 중복 없음).
export function followUps(metrics: string[]): string[] {
	const has = (n: string) => metrics.includes(n);
	const out: string[] = [];
	if (has('race_form_projection')) out.push('왜 테이퍼하면 폼이 올라가?');
	if (has('tsb')) out.push('이 폼이면 이번 주엔 뭘 하면 돼?');
	if (has('race_days_left')) out.push('남은 기간 주차별로 어떻게 준비할까?');
	if (has('utrs')) out.push('오늘 컨디션 점수는 어떻게 계산돼?');
	if (has('cirs')) out.push('부상 위험을 낮추려면?');
	if (out.length === 0) out.push('이번 주 훈련 뭘 하면 좋을까?');
	return [...new Set(out)].slice(0, 3);
}
```

   `frontend/tests/coachSuggestions.test.mjs`(신규): `homeTopics(null)`은 기본 4개; `homeTopics({name:'A',days_left:30,target_time_sec:15300})` → `['오늘 훈련 조언','레이스까지 어떻게 훈련을 쌓을까?','목표 기록 가능할까?','부상 위험 확인']`; days_left 10이면 두 번째가 `'테이퍼는 언제부터 어떻게 할까?'`; 목표 시간이 null이면 `'목표 기록 가능할까?'` 없음; `followUps(['race_days_left','race_form_projection','tsb','utrs'])` → 앞의 3개(`'왜 테이퍼하면 폼이 올라가?'`, `'이 폼이면 이번 주엔 뭘 하면 돼?'`, `'남은 기간 주차별로 어떻게 준비할까?'`); `followUps([])` → `['이번 주 훈련 뭘 하면 좋을까?']`.
2. `frontend/src/routes/coach/+page.ts`: `getRaceHub`(`$lib/api/today`)를 `Promise.all`에 `getRaceHub().catch(() => null)`로 추가하고 `CoachPageData`에 `goal: RaceHubGoal | null`(`hub?.goal ?? null`, 에러 분기 반환에도 포함)을 추가. `frontend/src/routes/coach/+page.svelte`: `SUGGESTED_TOPICS` 상수를 `const topics = $derived(homeTopics(data.goal));`로 바꾸고 `{#each SUGGESTED_TOPICS as topic}`을 `{#each topics as topic}`로(`import { homeTopics } from '$lib/coachSuggestions';`).
3. `frontend/src/routes/coach/[threadId]/+page.svelte`: `import { followUps } from '$lib/coachSuggestions';`. 마지막 assistant 메시지(`messages`에서 뒤에서부터 첫 `role === 'assistant'`)이고 `!sending`이며 그 메시지가 목록의 마지막일 때, `{#if sending}` 블록 바로 위에 `<div class="flex flex-wrap gap-2">{#each followUps((last.evidence ?? []).map((e) => e.metric)) as q}<button type="button" onclick={() => { inputText = q; send(); }} class="rounded-full border border-border-subtle bg-surface-2 px-3 py-1 text-xs text-fg-secondary hover:bg-surface-3">{q}</button>{/each}</div>`를 추가(파생값 `const lastMsg = $derived(messages[messages.length - 1] ?? null);`로 `lastMsg?.role === 'assistant'` 조건). 답변 출처 표기 `<p class="mt-1 text-[10px] text-fg-muted">{localizeSource(msg.ai_model)}</p>`의 클래스를 `mt-1 text-[11px] font-medium text-fg-secondary`로 바꾼다.

## 유닛 D — P7-IMPL-PROVIDER-HINTS (Provider 조치 문구 + 단일 소스 배지 숨김)

1. 신규 `frontend/src/lib/providerHint.ts`(순수):

```ts
export interface ProviderStatusLite {
	has_data: boolean;
	last_synced_at: string | null;
	activity_count: number;
}

// 상태 표만으로는 조치가 안 보이므로 다음 행동을 한 줄로 말한다. 정상이면 null.
export function providerHint(item: ProviderStatusLite, nowMs: number): string | null {
	if (!item.has_data) return '데이터 없음 — 연동 전이거나 동기화가 실패했어요. 동기화를 실행해 보세요.';
	if (!item.last_synced_at) return null;
	const t = Date.parse(item.last_synced_at.includes('T') ? item.last_synced_at : item.last_synced_at.replace(' ', 'T') + 'Z');
	if (!Number.isFinite(t)) return null;
	const days = Math.floor((nowMs - t) / 86_400_000);
	if (days >= 30) return `${days}일째 동기화가 없어요 — 최근 활동이 빠져 있을 수 있어요.`;
	if (days >= 7) return `${days}일 전이 마지막 동기화예요.`;
	return null;
}

// 목록의 모든 활동이 같은 소스면 행마다 배지를 반복하지 않는다(정보량 0).
export function showSourceBadge(sources: string[]): boolean {
	return new Set(sources).size > 1;
}
```

   `frontend/tests/providerHint.test.mjs`(신규): `providerHint({has_data:false,last_synced_at:null,activity_count:0}, 0)`이 `'데이터 없음'`으로 시작; `nowMs = Date.parse('2026-09-25T00:00:00Z')`일 때 `last_synced_at:'2026-06-20 10:00:00'` → `'96일째'`로 시작; `'2026-09-10 10:00:00'` → `'14일 전이 마지막 동기화예요.'`; `'2026-09-24 10:00:00'` → `null`; `showSourceBadge(['garmin','garmin']) === false`, `showSourceBadge(['garmin','strava']) === true`, `showSourceBadge([]) === false`.
2. `frontend/src/routes/library/+page.svelte`: `import { providerHint } from '$lib/providerHint';`. Provider 현황 `<li>`를 `flex flex-wrap`으로 바꾸고, 기존 내용 다음에 `{@const hint = providerHint(item, Date.now())}{#if hint}<p class="w-full text-[11px] text-semantic-amber">{hint}</p>{/if}`를 추가(기존 마크업 변경은 `<li>`의 클래스에 `flex-wrap` 추가만).
3. `frontend/src/routes/library/activities/+page.svelte`: `import { showSourceBadge } from '$lib/providerHint';`, `const showBadge = $derived(showSourceBadge(activities.map((a) => a.source)));`, 행의 소스 배지 `<span class="rounded px-1 py-px text-[9px] text-white …">` 를 `{#if showBadge}…{/if}`로 감싼다.

## 유닛 E — P7-IMPL-ARCHIVE-EXPLORE (월 막대 → 그 달 활동 목록; 기간 필터)

1. `frontend/src/lib/archive.ts`에 추가(기존 export 유지):

```ts
// 'YYYY-MM' → 그 달의 [from, to] (YYYY-MM-DD). 윤년 포함.
export function monthRange(month: string): { from: string; to: string } {
	const [y, m] = month.split('-').map(Number);
	const last = new Date(Date.UTC(y, m, 0)).getUTCDate();
	const mm = String(m).padStart(2, '0');
	return { from: `${y}-${mm}-01`, to: `${y}-${mm}-${String(last).padStart(2, '0')}` };
}
```

   `frontend/tests/archive.test.mjs`에 케이스 추가: `monthRange('2026-09')` → `{from:'2026-09-01', to:'2026-09-30'}`, `monthRange('2024-02').to === '2024-02-29'`, `monthRange('2026-12').to === '2026-12-31'`.
2. `frontend/src/lib/components/ArchiveHero.svelte`: 월별 막대의 각 `<div class="flex h-full flex-1 …" title=…>`를 `<a href="{base}/library/activities?from={monthRange(m.month).from}&to={monthRange(m.month).to}" class="flex h-full flex-1 …" title=…>`로(태그만 `div`→`a`, 클래스·내용 유지, 닫는 태그도 `</a>`). `import { monthHeights, monthRange } from '$lib/archive';`(`base`가 이미 import돼 있으면 재사용). 월 막대 아래 좌측 라벨 줄에 각 달 값이 없는 것은 그대로 둔다.
3. `frontend/src/routes/library/activities/+page.ts`: `load({ url })`로 시그니처를 바꾸고 `const from = url.searchParams.get('from') ?? undefined; const to = url.searchParams.get('to') ?? undefined;`, `getActivities({ per_page: 20, from, to: to ? `${to} 23:59:59` : undefined })`, 반환에 `from`·`to` 추가(`ActivitiesPageData`에 `from: string | undefined; to: string | undefined;`). **API의 `to`는 `start_time <= to` 비교라 날짜만 주면 그날 활동이 빠진다 — 반드시 ` 23:59:59`를 붙인다.**
4. `frontend/src/routes/library/activities/+page.svelte`: `let period = $state({ from: data.from, to: data.to });` 추가, `loadPage`의 `getActivities({…})` 인자에 `from: period.from, to: period.to ? `${period.to} 23:59:59` : undefined`를 추가. 필터 칩 줄 위에 `{#if period.from}<div class="flex items-center gap-2 px-4 pt-3"><span class="rounded-full bg-surface-3 px-3 py-1 text-xs text-fg-primary">{period.from} ~ {period.to}</span><button type="button" class="text-xs text-fg-muted hover:text-fg-primary" onclick={() => { period = { from: undefined, to: undefined }; applyFilters(); }}>기간 해제 ✕</button></div>{/if}`.

## 유닛 F — P7-IMPL-DESKTOP-LAYOUT (데스크톱 ≥1024px에서 Today 2열)

DECISIONS `[P7-IMPL-VISUAL-SYSTEM]`이 "≥1024에서 Today 2열"을 결정했으나 코드에 없었다 — 이 유닛이 그 결정을 실현한다.
1. `frontend/src/routes/+layout.svelte`: `max-w-3xl` 두 곳(헤더 컨테이너, `<main>`)과 하단 탭 컨테이너의 `max-w-3xl`을 `max-w-3xl lg:max-w-6xl`로 바꾼다(총 3곳, 다른 변경 금지).
2. `frontend/src/routes/today/+page.svelte`: 최상위 `<div class="flex flex-col gap-6 px-4 py-4">`를 `<div class="flex flex-col gap-6 px-4 py-4 lg:grid lg:grid-cols-2 lg:items-start lg:gap-x-8 lg:gap-y-6">`로. 각 섹션에 lg 배치 클래스를 **추가만** 한다(DOM 순서·기존 클래스 유지 → 모바일 불변):
   - L0 `<section class="flex flex-col gap-3">`(허브·브리핑·체크인) → `… lg:col-start-1 lg:row-span-2 lg:row-start-1`
   - L1 `<section class="flex flex-col gap-3">`(링·최근 활동) → `… lg:col-start-2 lg:row-start-1`
   - L2 `<section class="flex flex-col gap-3 border-t …">`(흐름·훈련·성장) → `… lg:col-start-2 lg:row-start-2`
   - "다음 세션" `<div class="flex flex-col gap-2 border-t …">` → `… lg:col-start-1 lg:row-start-3`
   - L3 `<section class="flex flex-col gap-2 border-t …">`(원본 데이터) → `… lg:col-span-2 lg:row-start-4`
3. `frontend/src/routes/library/+page.svelte`는 건드리지 않는다(이미 데스크톱에서 잘 읽힘 — REVIEW-06 §2.8).

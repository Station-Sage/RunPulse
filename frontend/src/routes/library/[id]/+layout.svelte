<script lang="ts">
	// 활동 상세 공용 레이아웃 — sticky 헤더(56px)와 탭 바(44px), 탭 전환 진행 표시(F-UX-10).
	import { page } from '$app/state';
	import { afterNavigate, replaceState } from '$app/navigation';
	import { base } from '$app/paths';
	import type { Snippet } from 'svelte';
	import ActivityTabs from '$lib/components/ActivityTabs.svelte';
	import { providerBadgeClass } from '$lib/provider';
	import { backTarget, headerDate, mergedSourceLabel, withEuro } from '$lib/activityHeader';
	import { emptyTabs, missingActivityView } from '$lib/activityDetailView';
	import { normalizeActivityIdParam } from '$lib/utils/validation';
	import PageHead from '$lib/components/ui/PageHead.svelte';
	import type { ActivityLayoutData } from './+layout';
	import type { ProviderKey } from '$lib/types';

	let { data, children }: { data: ActivityLayoutData; children: Snippet } = $props();

	// 앱 내부에서 들어온 경우만 history.back() — 탭 이동(같은 활동)은 제외하기 위해 최초 진입 시점만 기록.
	let cameFromApp = $state(false);
	afterNavigate((nav) => {
		canonicalize();
		if (nav.type === 'enter') cameFromApp = false;
		else if (nav.from) cameFromApp = !nav.from.url.pathname.startsWith(`${base}/library/${page.params.id}`);
	});
	// 앞자리 0 등 같은 활동의 다른 표기는 정규 URL 로 바꾼다(A-21, history 를 쌓지 않음).
	// 라우터 준비 뒤(afterNavigate)에만 replaceState 를 부를 수 있다.
	function canonicalize() {
		const raw = page.params.id ?? '';
		const parsed = normalizeActivityIdParam(raw);
		if (!parsed || raw === parsed.canonical) return;
		const u = new URL(page.url);
		u.pathname = u.pathname.replace(`/library/${raw}`, `/library/${parsed.canonical}`);
		replaceState(u, page.state);
	}
	function onBack(e: MouseEvent) {
		if (cameFromApp && history.length > 1) {
			e.preventDefault();
			history.back();
		}
	}

	const core = $derived(data.activity?.core ?? null);
	const from = $derived(page.url.searchParams.get('from'));
	const back = $derived(backTarget(from));
	const search = $derived(from ? `?from=${encodeURIComponent(from)}` : '');
	const parsedId = $derived(normalizeActivityIdParam(page.params.id));
	const id = $derived(parsedId?.id ?? NaN);
	const missing = $derived(core ? null : missingActivityView(data.failure));
	const empty = $derived(emptyTabs(data.activity));
	const sub = $derived(page.route.id?.split('/[id]')[1] ?? '');
	const active = $derived(
		(sub === '/streams' ? 'streams' : sub === '/laps' ? 'laps' : sub === '/metrics' ? 'metrics' : sub === '/providers' ? 'providers' : 'summary') as
			'summary' | 'streams' | 'laps' | 'metrics' | 'providers'
	);
	const sourceLabel = $derived(core ? mergedSourceLabel(core.source, data.activity?.siblings) : '');
</script>

<div class="sticky top-0 z-20 bg-surface-1">
	<header class="flex h-14 items-center gap-2 border-b border-border-subtle px-4">
		<a
			href="{base}{back.path}"
			class="shrink-0 text-sm text-fg-muted"
			onclick={onBack}
			aria-label="{withEuro(back.label)} 돌아가기"
			data-testid="activity-back">← {back.label}</a
		>
		{#if core}
			<div class="min-w-0 flex-1">
				<h1 class="truncate text-base font-semibold">{core.name}</h1>
				<p class="flex items-center gap-1.5 text-xs text-fg-muted">
					<span>{headerDate(core.start_time)}</span>
					{#if data.activity?.tz_estimated}
						<span
							class="rounded-full bg-surface-3 px-2 py-0.5 text-fg-secondary"
							data-testid="tz-estimated-badge"
							title="Strava 시간대를 확인하지 못해 한국 시간으로 표시했어요. 연결하면 자동으로 고쳐져요"
							>시간대 추정</span
						>
					{/if}
					{#if data.activity?.workout_class_label}
						<span class="rounded-full bg-surface-3 px-2 py-0.5 text-fg-secondary" data-testid="class-chip"
							>{data.activity.workout_class_label}</span
						>
					{/if}
					<span
						class="rounded px-1.5 py-0.5 text-[11px] {providerBadgeClass(core.source as ProviderKey)}"
						data-testid="source-badge">{sourceLabel}</span
					>
				</p>
			</div>
		{/if}
	</header>
	{#if core && Number.isFinite(id)}
		<ActivityTabs activityId={id} {active} {search} {empty} />
	{/if}
</div>

{#if missing}
	<!-- 없는 활동·잘못된 주소는 탭 없이 한 화면(A-23·A-24·E-28) -->
	<div class="flex flex-col items-center gap-3 px-4 py-20 text-center" data-testid="activity-missing">
		<PageHead title={missing.title} class="text-lg text-fg-secondary" />
		<p class="text-sm text-fg-muted">{missing.body}</p>
		<a href="{base}/library/activities" class="text-sm text-fg-secondary underline">← 활동 목록으로</a>
	</div>
{:else}
	{@render children()}
{/if}

<script lang="ts">
	// 활동 상세 공용 레이아웃 — sticky 헤더(56px)와 탭 바(44px), 탭 전환 진행 표시(F-UX-10).
	import { page } from '$app/state';
	import { afterNavigate } from '$app/navigation';
	import { base } from '$app/paths';
	import type { Snippet } from 'svelte';
	import ActivityTabs from '$lib/components/ActivityTabs.svelte';
	import { providerBadgeClass } from '$lib/provider';
	import { backTarget, mergedSourceLabel } from '$lib/activityHeader';
	import { formatDateShort } from '$lib/format';
	import type { ActivityLayoutData } from './+layout';
	import type { ProviderKey } from '$lib/types';

	let { data, children }: { data: ActivityLayoutData; children: Snippet } = $props();

	// 앱 내부에서 들어온 경우만 history.back() — 탭 이동(같은 활동)은 제외하기 위해 최초 진입 시점만 기록.
	let cameFromApp = $state(false);
	afterNavigate((nav) => {
		if (nav.type === 'enter') cameFromApp = false;
		else if (nav.from) cameFromApp = !nav.from.url.pathname.startsWith(`${base}/library/${page.params.id}`);
	});
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
	const id = $derived(parseInt(page.params.id ?? '', 10));
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
			aria-label="{back.label}(으)로 돌아가기"
			data-testid="activity-back">← {back.label}</a
		>
		{#if core}
			<div class="min-w-0 flex-1">
				<h1 class="truncate text-base font-semibold">{core.name}</h1>
				<p class="flex items-center gap-1.5 text-xs text-fg-muted">
					<span>{formatDateShort(core.start_time)}</span>
					{#if data.activity?.workout_class_label}
						<span class="rounded-full bg-surface-3 px-2 py-0.5 text-fg-secondary" data-testid="class-chip"
							>{data.activity.workout_class_label}</span
						>
					{/if}
					<span
						class="rounded px-1.5 py-0.5 text-[11px] text-white {providerBadgeClass(core.source as ProviderKey)}"
						data-testid="source-badge">{sourceLabel}</span
					>
				</p>
			</div>
		{/if}
	</header>
	{#if Number.isFinite(id)}
		<ActivityTabs activityId={id} {active} {search} />
	{/if}
</div>

{@render children()}

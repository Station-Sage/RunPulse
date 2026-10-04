<script lang="ts">
	// S5 — 웰니스 일 상세(/library/wellness/:date). 헤드라인·근거 칩·준비도·수면·핵심 카드·30일 추세.
	// 등급·임계값은 서버가 준다(프론트 상수 없음). 날짜 이동은 모두 replace.
	import { base } from '$app/paths';
	import { goto } from '$app/navigation';
	import { statusColorVar } from '$lib/statusColor';
	import { dateLabel } from '$lib/wellnessDay';
	import WellnessDateBar from '$lib/components/WellnessDateBar.svelte';
	import WellnessSleep from '$lib/components/WellnessSleep.svelte';
	import WellnessCores from '$lib/components/WellnessCores.svelte';
	import WellnessTrends from '$lib/components/WellnessTrends.svelte';
	import type { WellnessDayPageData } from './+page';

	let { data }: { data: WellnessDayPageData } = $props();
	const d = $derived(data.detail);

	const go = (date: string | null) =>
		date && goto(`${base}/library/wellness/${date}`, { replaceState: true, keepFocus: true });

	let startX = 0;
	let startY = 0;
	function onTouchStart(e: TouchEvent) {
		startX = e.touches[0].clientX;
		startY = e.touches[0].clientY;
	}
	function onTouchEnd(e: TouchEvent) {
		const dx = e.changedTouches[0].clientX - startX;
		const dy = e.changedTouches[0].clientY - startY;
		if (Math.abs(dx) < 60 || Math.abs(dx) < Math.abs(dy) * 1.5) return;
		go(dx > 0 ? d.nav.prev : d.nav.next);
	}
	const nearest = $derived(d.nav.prev ?? d.nav.next);
	const vitals = $derived(
		[
			['체중', d.core.weight_kg != null ? `${d.core.weight_kg.toFixed(1)}kg` : null],
			['활동 칼로리', typeof d.core.active_calories === 'number' ? `${Math.round(d.core.active_calories)}kcal` : null]
		].filter((v): v is [string, string] => v[1] != null)
	);
</script>

<svelte:head><title>{dateLabel(data.date)} 웰니스 · RunPulse</title></svelte:head>

<div ontouchstart={onTouchStart} ontouchend={onTouchEnd} role="presentation">
	<WellnessDateBar detail={d} />

	{#if !d.has_record}
		<section class="flex flex-col items-center gap-3 px-4 py-16 text-center">
			<p class="text-lg text-fg-secondary">{dateLabel(data.date)} 웰니스 기록이 없어요</p>
			{#if nearest}
				<button
					type="button"
					class="rounded-lg border border-border-subtle bg-surface-2 px-4 py-2 text-sm text-fg-secondary"
					onclick={() => go(nearest)}>가까운 기록({dateLabel(nearest)})으로 이동</button
				>
			{/if}
		</section>
	{:else}
		{#if d.headline}
			<section class="px-4 pt-4" aria-label="요약">
				<p class="text-base font-semibold leading-snug" style="color:{statusColorVar(d.headline.status)}">
					{d.headline.text}
				</p>
				{#if d.headline.reasons.length}
					<ul class="mt-2 flex flex-wrap gap-1.5">
						{#each d.headline.reasons as r (r.slug)}
							<li>
								<a
									href="{base}/library/metrics/{r.slug}?date={data.date}"
									class="inline-block rounded-full border border-border-subtle px-3 py-1 text-xs text-fg-secondary"
									>{r.chip}</a
								>
							</li>
						{/each}
					</ul>
				{/if}
			</section>
		{/if}

		<section class="grid grid-cols-2 gap-2 px-4 pt-4" aria-label="준비도">
			{#each [['utrs', 'UTRS'], ['cirs', 'CIRS']] as const as [key, label] (key)}
				{@const r = d.readiness[key]}
				<a href="{base}/library/metrics/{key}?date={data.date}" class="rounded-xl bg-surface-2 p-3">
					<span class="text-xs text-fg-muted">{label}</span>
					{#if r}
						<p class="mt-1 font-mono text-2xl font-semibold leading-none" style="color:{statusColorVar(r.status)}">
							{Math.round(r.value)}
						</p>
						<p class="mt-1 text-xs text-fg-muted">{r.status_label}</p>
					{:else}
						<p class="mt-1 text-sm text-fg-muted">데이터 수집 중</p>
					{/if}
				</a>
			{/each}
		</section>

		{#if d.sleep}
			<section class="px-4 pt-4" aria-label="수면">
				<WellnessSleep sleep={d.sleep} date={data.date} />
			</section>
		{/if}

		<section class="px-4 pt-4" aria-label="핵심 지표">
			<WellnessCores detail={d} />
			{#if vitals.length}
				<p class="mt-2 text-xs text-fg-muted">{vitals.map(([k, v]) => `${k} ${v}`).join(' · ')}</p>
			{/if}
		</section>
	{/if}

	<div class="pt-4"><WellnessTrends trend={data.trend} /></div>
</div>

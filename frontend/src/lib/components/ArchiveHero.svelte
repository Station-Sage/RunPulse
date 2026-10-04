<script lang="ts">
	// Library 홈 히어로 — 누적 거리 + 회/시간 근거 칩(탭하면 설명 팝오버). 월별·캘린더는 ArchiveTabCard.
	// DECISIONS.md [P7-IMPL-ARCHIVE]: 데이터 소유감(비전 원칙 1)을 화면의 첫 장면으로.
	import type { ArchiveData } from '$lib/types';
	import { base } from '$app/paths';

	let { archive }: { archive: ArchiveData } = $props();

	const t = $derived(archive.totals);
	const sinceLabel = $derived(t ? t.since.slice(0, 7).replace('-', '.') : '');
	let evidence = $state(false);

	function onKey(e: KeyboardEvent) {
		if (e.key === 'Escape') evidence = false;
	}
</script>

<svelte:window onkeydown={onKey} onclick={() => (evidence = false)} />

{#if t}
	<section class="px-4 pt-4" aria-label="러닝 아카이브">
		<div
			class="relative flex flex-col gap-3 rounded-xl border border-border-subtle p-4"
			style="background-color: var(--color-surface-2); background-image: radial-gradient(120% 90% at 0% 0%, rgba(20,184,166,0.16), transparent 62%)"
		>
			<p class="text-xs text-fg-muted">{sinceLabel}부터 내가 달린 거리</p>
			<div class="flex items-end gap-2">
				<span class="font-mono text-5xl font-bold leading-none tabular-nums"
					>{Math.round(t.distance_km).toLocaleString('ko-KR')}</span
				>
				<span class="pb-1 text-lg text-fg-muted">km</span>
			</div>
			<button
				type="button"
				class="w-fit text-left text-sm text-fg-secondary underline decoration-dotted underline-offset-4"
				aria-expanded={evidence}
				onclick={(e) => {
					e.stopPropagation();
					evidence = !evidence;
				}}
			>
				<span class="font-mono font-semibold">{t.runs.toLocaleString('ko-KR')}</span>회 ·
				<span class="font-mono font-semibold">{Math.round(t.hours).toLocaleString('ko-KR')}</span>시간 ·
				최근 1년 <span class="font-mono font-semibold">{t.active_days_365}</span>일 러닝
			</button>
			{#if evidence}
				<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions, a11y_no_noninteractive_element_interactions -->
				<div
					class="rounded-lg border border-border-subtle bg-surface-3 p-3 text-xs text-fg-secondary"
					role="note"
					onclick={(e) => e.stopPropagation()}
				>
					연결된 소스의 러닝 활동을 같은 활동끼리 합쳐 센 값이에요. 시간은 움직인 시간 합계이고,
					최근 1년 일수는 1회 이상 달린 날이에요.
					<a href="{base}/library/activities" class="ml-1 underline">활동 목록 ›</a>
				</div>
			{/if}
			{#if archive.longest}
				<a
					href="{base}/library/{archive.longest.id}?from=home"
					class="text-xs text-fg-muted hover:text-fg-secondary"
					>가장 멀리 달린 날 · {archive.longest.name} {archive.longest.distance_km}km ({archive.longest.date}) →</a
				>
			{/if}
		</div>
	</section>
{/if}

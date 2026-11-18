<script lang="ts">
	// 능동 인사이트 배너 — Today 는 최상위 1건(compact=false), Coach 는 최대 3건 목록(limit).
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import { dismissInsight, getInsights, seenInsight, type InsightEvent } from '$lib/api/insights';
	import { SEVERITY_TONE, signalChip, topInsight } from '$lib/insightView';

	let { limit = 1 }: { limit?: number } = $props();
	let events = $state<InsightEvent[]>([]);
	let openId = $state<number | null>(null);

	const shown = $derived(limit === 1 ? [topInsight(events)].filter((e): e is InsightEvent => !!e) : events.slice(0, limit));

	onMount(async () => {
		try {
			events = (await getInsights(10)).events;
		} catch {
			events = []; // 알림은 부가 정보 — 실패해도 화면을 막지 않는다
		}
	});

	function toggle(e: InsightEvent) {
		openId = openId === e.id ? null : e.id;
		if (openId === e.id && e.state === 'open') void seenInsight(e.id).catch(() => {});
	}
	async function dismiss(e: InsightEvent) {
		events = events.filter((x) => x.id !== e.id);
		await dismissInsight(e.id).catch(() => {});
	}
</script>

{#each shown as e (e.id)}
	<section class="rounded-lg border px-3 py-2 {SEVERITY_TONE[e.severity]}" aria-label="알림">
		<button type="button" class="flex min-h-11 w-full items-center justify-between gap-2 text-left text-sm text-fg-primary" aria-expanded={openId === e.id} onclick={() => toggle(e)}>
			<span>{e.text}</span>
			<span aria-hidden="true" class="text-fg-muted">{openId === e.id ? '▴' : '▾'}</span>
		</button>
		{#if openId === e.id}
			<div class="flex flex-col gap-2 pb-1">
				{#if e.signals.length > 0}
					<ul class="flex flex-wrap gap-1.5">
						{#each e.signals as s (s.signal)}
							<li class="rounded-full bg-surface-1 px-2 py-0.5 text-xs text-fg-secondary">{signalChip(s)}</li>
						{/each}
					</ul>
				{/if}
				<div class="flex gap-2">
					{#if e.action}
						<button type="button" class="min-h-11 rounded-lg bg-surface-1 px-3 text-sm font-medium text-fg-primary" onclick={() => goto(`${base}${e.action!.route}`)}>{e.action.label}</button>
					{/if}
					<button type="button" class="min-h-11 px-3 text-sm text-fg-muted" onclick={() => dismiss(e)}>닫기</button>
				</div>
			</div>
		{/if}
	</section>
{/each}

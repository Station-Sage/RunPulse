<script lang="ts">
	// 내러티브(L2) — 지연 로드 Promise를 {#await}로 소비. 실패 시 규칙 기반 fallback 한 줄.
	import EvidenceQuote from '$lib/components/EvidenceQuote.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import { milestoneIconName } from '$lib/milestoneIcon';
	import { adaptEvidence, type DrillTarget } from '$lib/evidence';
	import { base } from '$app/paths';
	import type { NarrativeResponse } from '$lib/types';

	let { narrative, ctl, onEvidence, onMonth, onMilestones }: {
		narrative: Promise<NarrativeResponse | null>;
		ctl: number | null;
		onEvidence: (t: DrillTarget) => void;
		onMonth: () => void;
		onMilestones: () => void;
	} = $props();
</script>

{#await narrative}
	<div class="flex animate-pulse flex-col gap-2" aria-label="이야기 불러오는 중">
		<div class="h-3 w-3/4 rounded bg-surface-2"></div>
		<div class="h-3 w-1/2 rounded bg-surface-2"></div>
	</div>
{:then n}
	{#if n}
		{#each n.text.split('\n').filter((p) => p.trim()) as paragraph}
			<p class="text-sm leading-relaxed text-fg-primary">{paragraph}</p>
		{/each}
		{#if n.evidence.length > 0}
			<div class="flex flex-wrap gap-2">
				{#each n.evidence as ev}
					<EvidenceQuote {...adaptEvidence(ev, onEvidence)} />
				{/each}
			</div>
		{:else}
			<p class="text-xs text-fg-muted">(데이터 부족 — 추후 업데이트)</p>
		{/if}
		{#if n.milestones.length > 0}
			<div class="flex flex-col gap-1">
				{#each n.milestones as m (m.id)}
					{#if m.activity_id != null}
						<a href="{base}/library/{m.activity_id}?from=today" class="flex items-start gap-2 text-sm hover:text-fg-primary">
							<Icon name={milestoneIconName(m.type)} class="h-4 w-4 shrink-0 text-fg-muted" />
							<span class="text-fg-muted">{m.date}</span>
							<span class="flex-1">{m.title}</span>
							<span class="shrink-0 text-fg-muted">›</span>
						</a>
					{:else}
						<div class="flex items-start gap-2 text-sm">
							<Icon name={milestoneIconName(m.type)} class="h-4 w-4 shrink-0 text-fg-muted" />
							<span class="text-fg-muted">{m.date}</span>
							<span class="flex-1">{m.title}</span>
						</div>
					{/if}
				{/each}
			</div>
			<button class="self-start text-sm text-fg-secondary hover:text-fg-primary" onclick={onMilestones}>전체 마일스톤 →</button>
		{/if}
		{#if n.source === 'rule'}<p class="text-xs text-fg-muted">규칙 기반 요약</p>{/if}
		<button class="self-start text-sm text-fg-secondary hover:text-fg-primary" onclick={onMonth}>이번 달 전체 이야기 보기 →</button>
	{:else}
		<p class="text-sm text-fg-secondary">
			현재 CTL {ctl ?? '—'} · <span class="text-fg-muted">상세 이야기를 불러올 수 없습니다.</span>
		</p>
	{/if}
{/await}

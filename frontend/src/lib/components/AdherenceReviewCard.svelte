<script lang="ts">
	// 지난주 이행 리뷰(AI 해설) — 검증을 통과해 저장된 경우에만 보인다. 없거나 실패하면 아무것도 그리지 않는다.
	import { onMount } from 'svelte';
	import AiMark from './AiMark.svelte';
	import { evidenceLabel, getAdherenceReview, type AdherenceReview } from '$lib/api/adherence';

	let review = $state<AdherenceReview | null>(null);

	onMount(async () => {
		try {
			review = (await getAdherenceReview()).review;
		} catch {
			review = null; // 부가 정보 — 실패해도 화면을 막지 않는다
		}
	});
</script>

{#if review}
	<section class="border-b border-border-subtle px-4 py-3" aria-label="지난주 리뷰" data-testid="adherence-review">
		<h2 class="mb-2 text-xs uppercase tracking-wide text-fg-muted">지난주 리뷰 <AiMark source="ai" prefix /></h2>
		<p class="text-sm text-fg-primary">{review.summary}</p>
		{#if review.points.length}
			<ul class="mt-2 flex flex-col gap-1.5">
				{#each review.points as p (p.text)}
					<li class="flex flex-wrap items-center gap-2 text-sm text-fg-secondary">
						<span>{p.text}</span>
						<span class="rounded-full bg-surface-1 px-2 py-0.5 text-xs text-fg-muted">{evidenceLabel(p.evidence_key)}</span>
					</li>
				{/each}
			</ul>
		{/if}
		<p class="mt-2 text-xs text-fg-muted">다음 주 집중: <span class="text-fg-secondary">{review.next_focus}</span></p>
	</section>
{/if}

<script lang="ts">
	// 활동 요약 L0 — 판정 문구 + 근거 칩(≤3). drill 근거는 onDrill(slug), info 근거는 InfoTag.
	import type { ActivityVerdict } from '$lib/types';
	import EvidenceQuote from '$lib/components/EvidenceQuote.svelte';
	import { pickVerdictEvidence, verdictDrillSlug } from '$lib/activityVerdict';

	let { verdict, onDrill }: { verdict: ActivityVerdict | null | undefined; onDrill: (slug: string) => void } =
		$props();
	const chips = $derived(pickVerdictEvidence(verdict?.evidence ?? []));
</script>

{#if verdict?.text}
	<section class="flex flex-col gap-2" aria-label="활동 판정" data-testid="activity-verdict">
		<p class="text-base font-semibold text-fg-primary">{verdict.text}</p>
		{#if chips.length > 0}
			<div class="flex flex-wrap items-center gap-2">
				{#each chips as e (e.label)}
					{@const slug = verdictDrillSlug(e)}
					<EvidenceQuote
						type="metric"
						label={e.label}
						onOpen={slug ? () => onDrill(slug) : undefined}
					/>
				{/each}
			</div>
		{/if}
	</section>
{/if}

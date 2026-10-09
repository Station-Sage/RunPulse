<script lang="ts">
	// 계획 다시 맞추기 안내 — 정보 띠, 알림 아님 (ADR-035 A6).
	import { base } from '$app/paths';
	import { replanHref, type PlanAdvisory } from '$lib/replanBanner';

	let { advisory, onHide }: { advisory: PlanAdvisory; onHide: () => void } = $props();
	const href = $derived(replanHref(base, advisory));
</script>

<div role="note" aria-label="계획 안내" data-testid="replan-banner" class="mt-2 rounded-lg bg-surface-2 p-3 text-xs text-fg-secondary">
	<p>{advisory.text}</p>
	<div class="mt-1 flex flex-wrap gap-x-4">
		{#if href}
			<a {href} class="flex min-h-11 items-center text-fg-primary underline">계획 다시 맞추기 <span aria-hidden="true">›</span></a>
		{/if}
		<button type="button" data-testid="replan-hide" class="min-h-11 text-fg-muted" onclick={onHide}>이번 주 숨기기</button>
	</div>
</div>

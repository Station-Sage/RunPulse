<script lang="ts">
	import type { ReplanPreview } from '$lib/types';
	import { externalNotice, preservedNotice, skippedNotice } from '$lib/replanView';

	let { preview }: { preview: ReplanPreview } = $props();
	const notices = $derived(
		[externalNotice(preview.external), preservedNotice(preview.preserved), skippedNotice(preview.skipped_dates)].filter(
			(x): x is string => x != null
		)
	);
</script>

{#each notices as n}
	<p class="rounded-lg bg-surface-2 p-3 text-xs text-fg-secondary">{n}</p>
{/each}

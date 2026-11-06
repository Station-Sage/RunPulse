<script lang="ts">
	// 활동 상세 신발 칩(V2-SHOES T10) — "신발 · 페가수스 40 (기본 규칙)" → 탭하면 ShoeAssignSheet. 비러닝(shoe=null)은 미표시.
	import type { ActivityShoe } from '$lib/api/shoes';
	import { shoeChipText, statusMeta } from '$lib/shoeView';
	import Icon from './Icon.svelte';
	import ShoeAssignSheet from './ShoeAssignSheet.svelte';

	let { activityId, shoe }: { activityId: number; shoe: ActivityShoe | null | undefined } = $props();

	// svelte-ignore state_referenced_locally
	let current = $state<ActivityShoe | null>(shoe ?? null);
	let open = $state(false);
	$effect(() => {
		current = shoe ?? null;
	});

	const text = $derived(shoeChipText(current));
	const warn = $derived(current?.status === 'soon' || current?.status === 'replace');
</script>

{#if current}
	{#if open}
		<ShoeAssignSheet {activityId} {current} onChanged={(s) => (current = s)} onClose={() => (open = false)} />
	{:else}
		<button type="button" onclick={() => (open = true)} data-testid="activity-shoe-chip"
			class="flex min-h-11 items-center gap-2 self-start rounded-full border border-border-subtle bg-surface-2 px-3 py-1.5 text-sm text-fg-secondary hover:bg-surface-3">
			<Icon name="shoe" class="h-4 w-4 text-fg-muted" />
			<span>신발 · {text}</span>
			{#if warn}<span class="text-xs {statusMeta(current.status).text}">{statusMeta(current.status).label}</span>{/if}
			{#if current.conflict}<span class="text-xs text-semantic-amber">소스 불일치</span>{/if}
		</button>
	{/if}
{/if}

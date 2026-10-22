<script lang="ts">
	// 화면 단위 로드 실패 — 404는 EmptyState형 안내, 그 외는 ErrorState + 다시 시도(ERR-6·8). 재시도는 invalidate(key).
	import { invalidate } from '$app/navigation';
	import ErrorState from '$lib/components/ErrorState.svelte';
	import type { Failure } from '$lib/loadFailure';

	let {
		failure,
		retryKey,
		backHref,
		backLabel,
		notFoundText = '찾을 수 없어요'
	}: { failure: Failure; retryKey: string; backHref: string; backLabel: string; notFoundText?: string } = $props();
</script>

<div class="flex flex-col items-center gap-2 px-4 py-8 text-center">
	{#if failure.kind === 'not_found'}
		<p class="text-sm text-fg-secondary">{notFoundText}</p>
	{:else}
		<ErrorState {failure} onRetry={() => invalidate(retryKey)} />
	{/if}
	<a href={backHref} class="text-xs text-fg-muted underline">{backLabel}</a>
</div>

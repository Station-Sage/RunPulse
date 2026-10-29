<script lang="ts">
	// §C5 오류 — 블록 단위 '불러오지 못했어요 · [다시 시도]' + 접힌 상세(오류 코드).
	// compact=true는 보조 블록용(전체 화면을 막지 않음, 40 design §6.1 "블록 자리에 ErrorState compact").
	// failure 를 주면 문구·상세를 분류 결과에서 만든다(ERR-1·9). onRetry 가 Promise 를 돌려주면 끝날 때까지 버튼 비활성(ERR-4).
	import type { Snippet } from 'svelte';
	import { failureMessage, type Failure } from '$lib/loadFailure';

	let {
		message,
		detail,
		failure,
		onRetry,
		compact = false,
		secondary
	}: {
		message?: string;
		detail?: string;
		failure?: Failure;
		onRetry?: () => void | Promise<unknown>;
		compact?: boolean;
		secondary?: Snippet;
	} = $props();

	let showDetail = $state(false);
	let retrying = $state(false);

	const text = $derived(message ?? (failure ? failureMessage(failure.kind) : '불러오지 못했어요'));
	const detailText = $derived(detail ?? failure?.detail);

	async function retry() {
		if (retrying || !onRetry) return;
		retrying = true;
		try {
			await onRetry();
		} finally {
			retrying = false;
		}
	}
</script>

<div data-testid="error-state"
	class="flex flex-col items-start gap-1.5 rounded-lg border border-border-subtle bg-surface-2 text-fg-secondary"
	class:p-3={!compact}
	class:p-2={compact}
>
	<div class="flex w-full items-center justify-between gap-2">
		<span class="text-sm">{text}</span>
		{#if onRetry}
			<button
				type="button"
				onclick={retry}
				disabled={retrying}
				aria-busy={retrying}
				class="shrink-0 rounded px-2 py-1 text-xs font-medium text-fg-primary hover:bg-surface-3 disabled:opacity-50"
			>
				{retrying ? '불러오는 중…' : '다시 시도'}
			</button>
		{/if}
	</div>
	{#if secondary}{@render secondary()}{/if}
	{#if detailText}
		<button
			type="button"
			onclick={() => (showDetail = !showDetail)}
			class="text-xs text-fg-muted hover:text-fg-secondary"
		>
			{showDetail ? '상세 접기' : '상세 보기'}
		</button>
		{#if showDetail}
			<p class="font-mono text-xs text-fg-muted">{detailText}</p>
		{/if}
	{/if}
</div>

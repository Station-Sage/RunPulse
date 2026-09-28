<script lang="ts">
	// §C5 오류 — 블록 단위 '불러오지 못했어요 · [다시 시도]' + 접힌 상세(오류 코드).
	// compact=true는 보조 블록용(전체 화면을 막지 않음, 40 design §6.1 "블록 자리에 ErrorState compact").
	let {
		message = '불러오지 못했어요',
		detail,
		onRetry,
		compact = false
	}: {
		message?: string;
		detail?: string;
		onRetry?: () => void;
		compact?: boolean;
	} = $props();

	let showDetail = $state(false);
</script>

<div
	class="flex flex-col items-start gap-1.5 rounded-lg border border-border-subtle bg-surface-2 text-fg-secondary"
	class:p-3={!compact}
	class:p-2={compact}
	role="alert"
>
	<div class="flex w-full items-center justify-between gap-2">
		<span class="text-sm">{message}</span>
		{#if onRetry}
			<button
				type="button"
				onclick={onRetry}
				class="shrink-0 rounded px-2 py-1 text-xs font-medium text-fg-primary hover:bg-surface-3"
			>
				다시 시도
			</button>
		{/if}
	</div>
	{#if detail}
		<button
			type="button"
			onclick={() => (showDetail = !showDetail)}
			class="text-xs text-fg-muted hover:text-fg-secondary"
		>
			{showDetail ? '상세 접기' : '상세 보기'}
		</button>
		{#if showDetail}
			<p class="font-mono text-xs text-fg-muted">{detail}</p>
		{/if}
	{/if}
</div>

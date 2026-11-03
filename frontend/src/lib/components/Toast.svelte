<script lang="ts">
	// §C5 — 쓰기 성공 토스트 + [되돌리기](5s). 호출부가 표시 여부(open)와 내용을 들고 있는다
	// (전역 스토어는 아직 두지 않음 — 소비처가 하나씩 생길 때 필요하면 승격).
	import { announce } from '$lib/a11y/announce';
	import { toastPolicy, type ToastLevel } from '$lib/a11y/toastPolicy';
	import IconButton from '$lib/components/ui/IconButton.svelte';

	let {
		open,
		message,
		onUndo,
		onDismiss,
		durationMs = 5000,
		level = 'info'
	}: {
		open: boolean;
		message: string;
		onUndo?: () => void;
		onDismiss: () => void;
		durationMs?: number;
		level?: ToastLevel;
	} = $props();

	$effect(() => {
		if (!open) return;
		const policy = toastPolicy(level, durationMs);
		announce(message, policy.politeness);
		if (policy.autoCloseMs === null) return;
		const t = setTimeout(onDismiss, policy.autoCloseMs);
		return () => clearTimeout(t);
	});
</script>

{#if open}
	<div
		class="fixed inset-x-4 bottom-[calc(var(--shell-bottom)+1.5rem)] z-[70] mx-auto flex max-w-sm items-center justify-between gap-3 rounded-lg bg-surface-3 px-4 py-3 text-sm text-fg-primary shadow-lg lg:bottom-6 lg:left-auto lg:right-6 lg:mx-0"
	>
		<span>{message}</span>
		{#if onUndo}
			<button
				type="button"
				onclick={() => {
					onUndo();
					onDismiss();
				}}
				class="shrink-0 font-medium text-series-1 hover:underline"
			>
				되돌리기
			</button>
		{/if}
		{#if level === 'error'}
			<IconButton label="알림 닫기" onclick={onDismiss} class="-mr-2 shrink-0 rounded text-fg-secondary hover:text-fg-primary">✕</IconButton>
		{/if}
	</div>
{/if}

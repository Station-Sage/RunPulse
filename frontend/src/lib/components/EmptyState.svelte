<script lang="ts">
	// §C5 빈 상태 — '무엇이 없는지 + 왜 + 행동 버튼 1개'. "데이터 없음"과 "불러오기 실패"를
	// 구분한다(그 구분은 ErrorState가 맡는다 — 이 컴포넌트는 '있어야 할 게 아직/여기 없다' 쪽).
	import Icon from '$lib/components/Icon.svelte';
	import type { IconName } from '$lib/icon';

	let {
		icon = 'info',
		title,
		description,
		actionLabel,
		onAction,
		actionHref
	}: {
		icon?: IconName;
		title: string;
		description?: string;
		actionLabel?: string;
		onAction?: () => void;
		actionHref?: string;
	} = $props();
</script>

<div class="flex flex-col items-center gap-2 px-4 py-8 text-center">
	<Icon name={icon} class="h-8 w-8 text-fg-muted" />
	<p class="text-sm font-medium text-fg-primary">{title}</p>
	{#if description}
		<p class="max-w-xs text-xs text-fg-muted">{description}</p>
	{/if}
	{#if actionLabel && actionHref}
		<a
			href={actionHref}
			class="mt-2 rounded-full bg-surface-3 px-4 py-2 text-sm font-medium text-fg-primary hover:bg-surface-3/70"
		>
			{actionLabel}
		</a>
	{:else if actionLabel && onAction}
		<button
			type="button"
			onclick={onAction}
			class="mt-2 rounded-full bg-surface-3 px-4 py-2 text-sm font-medium text-fg-primary hover:bg-surface-3/70"
		>
			{actionLabel}
		</button>
	{/if}
</div>

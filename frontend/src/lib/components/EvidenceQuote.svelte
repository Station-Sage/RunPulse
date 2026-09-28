<script lang="ts">
	// §C2 근거 칩 2종(ux-review-2026-09/10-today/design.md) — DrillChip(목적지 있음)/InfoTag(없음).
	// onOpen이 없으면(드릴 대상이 없는 근거 — metric_store 행이 없는 지표 등) 비대화형 span으로
	// 렌더링한다 — 누르면 아무 일도 안 일어나는 가짜 버튼을 피한다. 이모지 금지(§C8) — SVG 아이콘만.
	import type { EvidenceQuoteProps } from '$lib/types';
	import Icon from '$lib/components/Icon.svelte';
	import type { IconName } from '$lib/icon';

	let { type, label, metric, activity, user_input, unavailable, onOpen }: EvidenceQuoteProps =
		$props();

	const icon: IconName | null = $derived(
		unavailable ? null : type === 'activity' ? 'activity' : type === 'user_input' ? 'note' : 'metric'
	);

	const text = $derived.by(() => {
		if (unavailable) return '데이터 수집 중';
		if (label) return label;
		if (metric) return `${metric.slug} ${metric.value}${metric.unit ?? ''}`;
		if (activity) return `${activity.field} ${activity.value}${activity.unit ?? ''}`;
		if (user_input) return `${user_input.field} ${user_input.value}`;
		return '';
	});

	function handleOpen() {
		if (!unavailable && onOpen) onOpen({ type, label, metric, activity, user_input, unavailable });
	}
</script>

{#if onOpen && !unavailable}
	<!-- DrillChip: 목적지가 있는 근거 — 44px 히트, 값 semibold, 끝에 › -->
	<button
		type="button"
		onclick={handleOpen}
		class="inline-flex min-h-[32px] items-center gap-1 rounded-full border border-fg-secondary/40 bg-surface-2 px-2.5 py-1.5 text-xs text-fg-secondary transition-transform hover:bg-surface-3 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-fg-secondary active:scale-[.97]"
	>
		{#if icon}<Icon name={icon} class="h-3 w-3 shrink-0 text-fg-muted" />{/if}
		<span class="num font-semibold">{text}</span>
		<Icon name="chevron" class="h-3 w-3 shrink-0" />
	</button>
{:else}
	<!-- InfoTag: 목적지가 없는 근거 — 테두리·배경 없음, › 없음 -->
	<span
		class="inline-flex items-center gap-1 text-xs"
		class:opacity-60={unavailable}
		class:text-fg-secondary={!unavailable}
		class:text-fg-muted={unavailable}
	>
		{#if icon}<Icon name={icon} class="h-3 w-3 shrink-0 text-fg-muted" />{/if}{text}
	</span>
{/if}

<script lang="ts">
	// C1 — 04-component-catalog.md. AI 결론에 인라인으로 삽입되는 근거 칩.
	// onOpen이 없으면(드릴 대상이 없는 근거 — metric_store 행이 없는 지표 등)
	// 비대화형 span으로 렌더링한다 — 누르면 아무 일도 안 일어나는 가짜 버튼을 피한다.
	import type { EvidenceQuoteProps } from '$lib/types';

	let { type, label, metric, activity, user_input, unavailable, onOpen }: EvidenceQuoteProps =
		$props();

	const icon = $derived(unavailable ? '⋯' : type === 'activity' ? '🏃' : type === 'user_input' ? '📝' : '📊');

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
	<button
		type="button"
		onclick={handleOpen}
		class="inline-flex items-center gap-1 rounded-full border border-border-subtle bg-surface-2 px-2 py-1 font-mono text-xs text-fg-secondary hover:bg-surface-3"
	>
		<span aria-hidden="true">{icon}</span>{text}
	</button>
{:else}
	<span
		class="inline-flex items-center gap-1 rounded-full border border-border-subtle bg-surface-2 px-2 py-1 font-mono text-xs"
		class:opacity-60={unavailable}
		class:text-fg-secondary={!unavailable}
		class:text-fg-muted={unavailable}
	>
		<span aria-hidden="true">{icon}</span>{text}
	</span>
{/if}

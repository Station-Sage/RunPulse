<script lang="ts">
	// C2 — 04-component-catalog.md. 단일 메트릭 + Provider 배지(P3, 생략 불가) + 상태.
	// drillable=true라도 7a엔 열어줄 MetricBreakdown 패널이 없다(07 로드맵 7b 몫) —
	// Today 화면에서는 항상 drillable=false로 사용한다.
	import type { MetricCellProps } from '$lib/types';
	import { providerLabel, providerBadgeClass } from '$lib/provider';

	let {
		slug,
		label,
		value,
		unit,
		provider,
		status = 'neutral',
		trend,
		size = 'md',
		drillable = true,
		unavailable = false,
		onDrill
	}: MetricCellProps = $props();

	const statusClass = $derived(
		{
			excellent: 'text-semantic-green',
			good: 'text-semantic-teal',
			neutral: 'text-fg-primary',
			caution: 'text-semantic-amber',
			poor: 'text-semantic-red'
		}[status]
	);

	const statusLabel = $derived(
		{ excellent: '매우 좋음', good: '양호', neutral: '보통', caution: '주의', poor: '나쁨' }[status]
	);

	const sizeClass = $derived({ sm: 'p-2 text-sm', md: 'p-3', lg: 'p-4 text-lg' }[size]);

	function handleClick() {
		if (drillable && !unavailable && onDrill) onDrill({ slug, provider });
	}

	const interactive = $derived(drillable && !!onDrill);
</script>

<!-- svelte-ignore a11y_no_noninteractive_tabindex -- role/tabindex는 interactive일 때만 같이 붙는다 -->
<div
	role={interactive ? 'button' : undefined}
	tabindex={interactive ? 0 : undefined}
	onclick={interactive ? handleClick : undefined}
	onkeydown={interactive
		? (e: KeyboardEvent) => (e.key === 'Enter' || e.key === ' ') && handleClick()
		: undefined}
	class="flex flex-col gap-1 rounded-lg border border-border-subtle bg-surface-2 {sizeClass} {interactive
		? 'cursor-pointer hover:bg-surface-3'
		: ''}"
>
	<div class="flex items-center justify-between gap-2">
		<span class="text-xs text-fg-secondary">{label}</span>
		<span class="rounded px-1.5 py-0.5 text-[10px] text-white {providerBadgeClass(provider)}">
			{providerLabel(provider)}
		</span>
	</div>

	<div class="font-mono text-xl font-bold">
		{#if unavailable || value === null}
			<span class="text-fg-muted">—</span>
		{:else}
			{value}{#if unit}<span class="ml-0.5 text-sm font-normal text-fg-secondary">{unit}</span>{/if}
		{/if}
	</div>

	{#if !unavailable}
		<div class="flex items-center gap-2 text-xs {statusClass}">
			<span aria-hidden="true">●</span>{statusLabel}
			{#if trend}
				<span class="text-fg-secondary">
					{trend.direction === 'up' ? '↑' : trend.direction === 'down' ? '↓' : '→'}
					{trend.change ?? ''}
				</span>
			{/if}
		</div>
	{/if}
</div>

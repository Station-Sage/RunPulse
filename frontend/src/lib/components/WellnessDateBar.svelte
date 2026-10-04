<script lang="ts">
	// 웰니스 날짜 바 + 이번 주 7일 점. 이동은 모두 replace(히스토리 누적 방지).
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import { statusColorVar } from '$lib/statusColor';
	import { dateLabel } from '$lib/wellnessDay';
	import type { WellnessDetailData } from '$lib/types';

	let { detail }: { detail: WellnessDetailData } = $props();

	const go = (d: string | null) => {
		if (d) goto(`${base}/library/wellness/${d}`, { replaceState: true, keepFocus: true });
	};
	const dayNum = (d: string) => Number(d.slice(8));
	const WD = ['월', '화', '수', '목', '금', '토', '일'];
</script>

<div class="flex items-center justify-between px-4 pt-3">
	<button
		type="button"
		aria-label="이전 기록"
		disabled={!detail.nav.prev}
		onclick={() => go(detail.nav.prev)}
		class="h-9 w-9 rounded-full text-lg text-fg-secondary disabled:opacity-30">‹</button
	>
	<h1 class="text-base font-semibold">
		{dateLabel(detail.date)}{#if detail.is_today}<span class="ml-1 text-xs font-normal text-fg-muted">오늘</span>{/if}
	</h1>
	<button
		type="button"
		aria-label="다음 기록"
		disabled={!detail.nav.next}
		onclick={() => go(detail.nav.next)}
		class="h-9 w-9 rounded-full text-lg text-fg-secondary disabled:opacity-30">›</button
	>
</div>
<div class="flex justify-between px-6 pb-1 pt-2" role="group" aria-label="이번 주">
	{#each detail.week as w, i (w.date)}
		<button
			type="button"
			onclick={() => go(w.date)}
			aria-label="{dateLabel(w.date)}{w.status === 'none' ? ' 기록 없음' : ''}"
			aria-current={w.date === detail.date ? 'date' : undefined}
			class="flex w-9 flex-col items-center gap-1 text-xs {w.date === detail.date ? 'text-fg-primary' : 'text-fg-muted'}"
		>
			<span>{WD[i]}</span>
			<span
				class="h-3 w-3 rounded-full {w.date === detail.date ? 'ring-2 ring-fg-primary ring-offset-2 ring-offset-surface-1' : ''}"
				style="background:{w.status === 'none' ? 'transparent' : statusColorVar(w.status)};{w.status === 'none'
					? 'border:1px solid var(--color-fg-muted)'
					: ''}"
			></span>
			<span class="font-mono">{dayNum(w.date)}</span>
		</button>
	{/each}
</div>

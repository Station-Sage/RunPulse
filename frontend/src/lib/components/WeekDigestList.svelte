<script lang="ts">
	// 월간 뷰 L2 — 주별 다이제스트 접힘 목록(DESIGN-U17 U17g). 월요일 시작 주.
	import type { WeekDigest } from '$lib/types';

	let { weeks }: { weeks: WeekDigest[] } = $props();
	let open = $state(false);

	const FLAG_LABEL: Record<string, string> = {
		tsb_low: 'TSB 낮음',
		sleep_low: '수면 부족',
		plan_missed: '계획 미이행'
	};
	const md = (iso: string) => `${Number(iso.slice(5, 7))}/${Number(iso.slice(8, 10))}`;
</script>

<div class="rounded-lg border border-border-subtle bg-surface-2 p-3" data-testid="week-digest">
	<button
		class="flex w-full items-center justify-between text-xs text-fg-muted hover:text-fg-secondary"
		onclick={() => (open = !open)}
		aria-expanded={open}
	>
		<span>주별 요약 ({weeks.length}주)</span>
		<span aria-hidden="true">{open ? '▲' : '▼'}</span>
	</button>
	{#if open}
		<ol class="mt-2 flex flex-col gap-2">
			{#each weeks as w, i (w.week_start)}
				<li id={`week-${i + 1}`} class="flex flex-col gap-0.5 text-xs" data-testid="week-row">
					<div class="flex items-baseline justify-between">
						<span class="font-medium">W{i + 1} · {md(w.week_start)}~{md(w.week_end)}{w.partial ? ' (진행 중)' : ''}</span>
						<span class="font-mono">{w.distance_km ?? '—'}km</span>
					</div>
					{#if w.run_count === 0}
						<span class="text-fg-muted">러닝 없음</span>
					{:else}
						<span class="text-fg-muted">
							{w.run_count}회 · 롱런 {w.long_run_km}km
							{#if w.ctl_end !== null}· CTL {w.ctl_end.toFixed(1)}{/if}
							{#if w.tsb_min !== null}· 최저 TSB {w.tsb_min}{/if}
							{#if w.sleep_avg !== null}· 수면 {w.sleep_avg}{/if}
							{#if w.plan_total > 0}· 계획 {w.plan_done}/{w.plan_total}{/if}
						</span>
					{/if}
					{#if w.flags.length > 0}
						<span class="text-semantic-amber">{w.flags.map((f) => FLAG_LABEL[f] ?? f).join(' · ')}</span>
					{/if}
				</li>
			{/each}
		</ol>
	{/if}
</div>

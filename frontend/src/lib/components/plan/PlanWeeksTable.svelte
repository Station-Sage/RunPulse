<script lang="ts">
	// R3 PLN-1/5 — 목표 전체 주간 개요 표(단계·계획/실제 km·러닝/휴식일·롱런·품질·준수율).
	import type { PlanWeekRow } from '$lib/types';

	let { weeks, currentWeek }: { weeks: PlanWeekRow[]; currentWeek: string } = $props();
</script>

{#if weeks.length > 0}
	<div class="overflow-x-auto border-b border-border-subtle px-4 py-3" data-testid="plan-weeks">
		<p class="mb-2 text-xs uppercase tracking-wide text-fg-muted">전체 주간 개요</p>
		<table class="w-full min-w-[480px] text-xs">
			<thead class="text-fg-muted">
				<tr>
					<th class="py-1 text-left font-normal">주</th>
					<th class="text-left font-normal">단계</th>
					<th class="text-right font-normal">계획</th>
					<th class="text-right font-normal">실제</th>
					<th class="text-right font-normal">러닝/휴식</th>
					<th class="text-right font-normal">롱런</th>
					<th class="text-right font-normal">품질</th>
					<th class="text-right font-normal">준수</th>
				</tr>
			</thead>
			<tbody>
				{#each weeks as w (w.week_start)}
					<tr class="border-t border-border-subtle" class:bg-surface-2={w.week_start === currentWeek}>
						<td class="py-1.5 font-mono">
							{(w.start_date ?? w.week_start).slice(5)}{#if w.start_date}<span class="text-fg-muted"> 시작</span>{/if}
						</td>
						<td>{w.phase ?? '-'}</td>
						<td class="text-right font-mono">{w.planned_km}km</td>
						<td class="text-right font-mono">{w.actual_km != null ? `${w.actual_km}km` : '-'}</td>
						<td class="text-right font-mono">{w.run_days}/{w.rest_days}</td>
						<td class="text-right font-mono">{w.long_km ? `${w.long_km}km` : '-'}</td>
						<td class="text-right font-mono">{w.quality_n}</td>
						<td class="text-right font-mono">{w.compliance_pct != null ? `${w.compliance_pct}%` : '-'}</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
{/if}

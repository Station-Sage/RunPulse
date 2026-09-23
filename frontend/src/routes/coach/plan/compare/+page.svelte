<script lang="ts">
	// 03e-coach.md 5-E — 프로그램 비교: 템플릿 카드 3개, 선택 시 플랜 생성.
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import { createPlan } from '$lib/api/plan';
	import type { ComparePlanData } from './+page';

	let { data }: { data: ComparePlanData } = $props();

	let loading = $state<number | null>(null);
	let error = $state<string | null>(null);

	function fmtTime(sec: number | null): string {
		if (sec == null) return '—';
		const h = Math.floor(sec / 3600);
		const m = Math.floor((sec % 3600) / 60);
		const s = sec % 60;
		if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
		return `${m}:${String(s).padStart(2, '0')}`;
	}

	function riskColor(risk: string | null): string {
		if (risk === '낮음') return 'text-semantic-green';
		if (risk === '중간') return 'text-semantic-yellow';
		if (risk === '높음') return 'text-semantic-red';
		return 'text-fg-muted';
	}

	async function handleSelect(weeks: number) {
		loading = weeks;
		error = null;
		try {
			const goalId = await createPlan({
				distance_km: data.distanceKm,
				race_date: data.raceDate,
				weeks,
				...(data.targetTimeSec != null ? { target_time_sec: data.targetTimeSec } : {})
			});
			await goto(`${base}/coach/plan/${goalId}`);
		} catch {
			error = '플랜 생성에 실패했습니다. 다시 시도해주세요.';
		} finally {
			loading = null;
		}
	}
</script>

<div class="flex flex-col">
	<div class="border-b border-border-subtle px-4 py-3">
		<div class="mb-1">
			<a href="{base}/coach/plan/new" class="text-xs text-fg-muted hover:underline">← 새 프로그램</a>
		</div>
		<h1 class="text-base font-semibold">프로그램 비교</h1>
		<p class="text-xs text-fg-muted">단계 3/3 — 원하는 프로그램을 선택하세요</p>
	</div>

	<div class="flex flex-col gap-4 px-4 py-5">
		{#each data.templates as t}
			<div class="rounded-xl border border-border-subtle bg-surface-2 p-4">
				<div class="mb-3 flex items-start justify-between">
					<div>
						<p class="text-sm font-semibold text-fg-primary">{t.label}</p>
						<p class="text-xs text-fg-muted">{t.weeks}주 프로그램</p>
					</div>
					{#if t.risk_level != null}
						<span class="text-xs font-medium {riskColor(t.risk_level)}">
							위험도 {t.risk_level}
						</span>
					{/if}
				</div>

				<div class="mb-3 grid grid-cols-2 gap-2 text-xs">
					<div>
						<p class="text-fg-muted">주간 최대 거리</p>
						<p class="font-medium text-fg-secondary">
							{t.weekly_km_target != null ? `${Math.round(t.weekly_km_target)} km` : '—'}
						</p>
					</div>
					<div>
						<p class="text-fg-muted">달성 가능성</p>
						<p class="font-medium text-fg-secondary">
							{t.achievability_pct != null ? `${Math.round(t.achievability_pct)}%` : '—'}
						</p>
					</div>
					<div>
						<p class="text-fg-muted">예상 완주 시간</p>
						<p class="font-medium text-fg-secondary">{fmtTime(t.projected_time_end)}</p>
					</div>
				</div>

				{#if t.status_summary}
					<p class="mb-3 text-xs text-fg-muted">{t.status_summary}</p>
				{/if}

				<button
					type="button"
					onclick={() => handleSelect(t.weeks)}
					disabled={loading != null}
					class="w-full rounded-lg bg-fg-primary py-2 text-sm font-medium text-surface-1 disabled:opacity-40"
				>
					{loading === t.weeks ? '생성 중…' : '이 프로그램 선택'}
				</button>
			</div>
		{/each}

		{#if error}
			<p class="text-sm text-semantic-red">{error}</p>
		{/if}
	</div>
</div>

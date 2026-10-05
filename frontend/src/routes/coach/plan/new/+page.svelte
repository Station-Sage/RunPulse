<script lang="ts">
	// 03e-coach.md 5-D — 새 프로그램 생성: 거리/날짜/목표 입력.
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import { page } from '$app/state';
	import { parsePrefill, parseReportedLoad, REPORTED_MAX_KM, reportedLoadEntries } from '$lib/planPrefill';

	const DISTANCES: { label: string; km: number }[] = [
		{ label: '5km', km: 5 },
		{ label: '10km', km: 10 },
		{ label: '하프', km: 21.097 },
		{ label: '마라톤', km: 42.195 }
	];

	const pre = parsePrefill(page.url.searchParams);

	let selectedKm = $state<number | null>(pre.km);
	let raceDate = $state(pre.raceDate);
	let isCompletion = $state(false);
	let goalHH = $state(pre.hh);
	let goalMM = $state(pre.mm);
	let goalSS = $state(pre.ss);
	const reported = parseReportedLoad(page.url.searchParams);
	let recentWeekly = $state(reported.weeklyKm != null ? String(reported.weeklyKm) : '');
	let recentLong = $state(reported.longKm != null ? String(reported.longKm) : '');
	let loading = $state(false);
	let error = $state<string | null>(null);

	function targetTimeSec(): number | undefined {
		if (isCompletion) return undefined;
		const h = parseInt(goalHH) || 0;
		const m = parseInt(goalMM) || 0;
		const s = parseInt(goalSS) || 0;
		const total = h * 3600 + m * 60 + s;
		return total > 0 ? total : undefined;
	}

	async function handleSubmit() {
		if (selectedKm == null) {
			error = '거리를 선택해주세요.';
			return;
		}
		loading = true;
		error = null;
		try {
			const { getPlanTemplates } = await import('$lib/api/plan');
			const tts = targetTimeSec();
			await getPlanTemplates(selectedKm, tts);
			const params = new URLSearchParams({ distance_km: String(selectedKm) });
			if (raceDate) params.set('race_date', raceDate);
			if (tts != null) params.set('target_time_sec', String(tts));
			for (const [k, v] of reportedLoadEntries(String(recentWeekly ?? ''), String(recentLong ?? ''))) params.set(k, v);
			await goto(`${base}/coach/plan/compare?${params}`);
		} catch {
			error = '템플릿을 불러올 수 없습니다. 다시 시도해주세요.';
		} finally {
			loading = false;
		}
	}
</script>

<svelte:head><title>새 플랜 · RunPulse</title></svelte:head>

<div class="flex flex-col">
	<div class="border-b border-border-subtle px-4 py-3">
		<div class="mb-1">
			<a href="{base}/coach" class="text-xs text-fg-muted hover:underline">← 코치</a>
		</div>
		<h1 class="text-base font-semibold">새 프로그램</h1>
		<p class="text-xs text-fg-muted">단계 1/3</p>
	</div>

	<div class="flex flex-col gap-5 px-4 py-5">
		<!-- 거리 선택 -->
		<div>
			<p class="mb-2 text-sm font-medium text-fg-primary">목표 거리</p>
			<div class="flex flex-wrap gap-2">
				{#each DISTANCES as d}
					<button
						type="button"
						onclick={() => (selectedKm = d.km)}
						class="rounded-full border px-4 py-1.5 text-sm transition-colors
							{selectedKm === d.km
							? 'border-fg-primary bg-fg-primary text-surface-1'
							: 'border-border-subtle bg-surface-2 text-fg-secondary hover:bg-surface-3'}"
					>
						{d.label}
					</button>
				{/each}
			</div>
		</div>

		<!-- 날짜 입력 -->
		<div>
			<label class="mb-2 block text-sm font-medium text-fg-primary" for="race-date">
				레이스 날짜 (선택)
			</label>
			<input
				id="race-date"
				type="date"
				bind:value={raceDate}
				class="rounded-lg border border-border-subtle bg-surface-2 px-3 py-2 text-sm text-fg-primary focus:outline-none"
			/>
		</div>

		<!-- 목표 시간 -->
		<div>
			<p class="mb-2 text-sm font-medium text-fg-primary">목표</p>
			<div class="flex items-center gap-3">
				<label class="flex items-center gap-1.5 text-sm text-fg-secondary">
					<input type="radio" bind:group={isCompletion} value={false} class="accent-fg-primary" />
					목표 시간
				</label>
				<label class="flex items-center gap-1.5 text-sm text-fg-secondary">
					<input type="radio" bind:group={isCompletion} value={true} class="accent-fg-primary" />
					완주
				</label>
			</div>
			{#if !isCompletion}
				<div class="mt-2 flex items-center gap-1.5">
					<input
						type="number"
						bind:value={goalHH}
						placeholder="HH"
						min="0"
						max="23"
						class="w-14 rounded-lg border border-border-subtle bg-surface-2 px-2 py-1.5 text-center text-sm text-fg-primary focus:outline-none"
					/>
					<span class="text-fg-muted">:</span>
					<input
						type="number"
						bind:value={goalMM}
						placeholder="MM"
						min="0"
						max="59"
						class="w-14 rounded-lg border border-border-subtle bg-surface-2 px-2 py-1.5 text-center text-sm text-fg-primary focus:outline-none"
					/>
					<span class="text-fg-muted">:</span>
					<input
						type="number"
						bind:value={goalSS}
						placeholder="SS"
						min="0"
						max="59"
						class="w-14 rounded-lg border border-border-subtle bg-surface-2 px-2 py-1.5 text-center text-sm text-fg-primary focus:outline-none"
					/>
				</div>
			{/if}
		</div>

		<!-- 최근 훈련량(선택) — 기록이 적을 때 시작 볼륨으로 사용 -->
		<div>
			<p class="mb-1 text-sm font-medium text-fg-primary">최근 훈련량 (선택)</p>
			<p class="mb-2 text-xs text-fg-muted">최근 4주 기록이 적을 때 시작 볼륨으로 사용합니다.</p>
			<div class="flex flex-wrap items-center gap-3">
				<label class="flex items-center gap-1.5 text-sm text-fg-secondary" for="recent-weekly">
					주간
					<input
						id="recent-weekly"
						type="number"
						bind:value={recentWeekly}
						placeholder="km"
						min="0"
						max={REPORTED_MAX_KM.weekly}
						step="0.1"
						class="w-20 rounded-lg border border-border-subtle bg-surface-2 px-2 py-1.5 text-center text-sm text-fg-primary focus:outline-none"
					/>
					km
				</label>
				<label class="flex items-center gap-1.5 text-sm text-fg-secondary" for="recent-long">
					최장
					<input
						id="recent-long"
						type="number"
						bind:value={recentLong}
						placeholder="km"
						min="0"
						max={REPORTED_MAX_KM.long}
						step="0.1"
						class="w-20 rounded-lg border border-border-subtle bg-surface-2 px-2 py-1.5 text-center text-sm text-fg-primary focus:outline-none"
					/>
					km
				</label>
			</div>
		</div>

		{#if error}
			<p class="text-sm text-semantic-red">{error}</p>
		{/if}

		<button
			type="button"
			onclick={handleSubmit}
			disabled={loading || selectedKm == null}
			class="self-start rounded-lg bg-fg-primary px-6 py-2.5 text-sm font-medium text-surface-1 disabled:opacity-40"
		>
			{loading ? '분석 중…' : '프로그램 생성 →'}
		</button>
	</div>
</div>

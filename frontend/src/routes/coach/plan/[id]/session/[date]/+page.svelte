<script lang="ts">
	// 03e-coach.md 5-G — 일일 세션 상세.
	import type { SessionDetailPageData } from './+page';
	import { saveSessionNote } from '$lib/api/plan';
	import { workoutLabel } from '$lib/format';
	import { base } from '$app/paths';

	let { data }: { data: SessionDetailPageData } = $props();

	const DAY_KO = ['월', '화', '수', '목', '금', '토', '일'];

	function dayLabel(dateStr: string): string {
		const d = new Date(dateStr + 'T00:00:00');
		return DAY_KO[d.getDay() === 0 ? 6 : d.getDay() - 1];
	}

	function paceRange(min: number | null, max: number | null): string {
		if (min == null && max == null) return '';
		const fmt = (s: number) => {
			const m = Math.floor(s);
			const sec = Math.round((s - m) * 60);
			return `${m}:${String(sec).padStart(2, '0')}`;
		};
		if (min != null && max != null) return `${fmt(min)}–${fmt(max)}/km`;
		if (min != null) return `>${fmt(min)}/km`;
		return `<${fmt(max!)}/km`;
	}

	let noteText = $state(data.session?.note ?? '');
	let noteSaving = $state(false);
	let noteSaved = $state(false);
	let noteError = $state<string | null>(null);

	async function handleNoteSave() {
		if (!noteText.trim()) return;
		noteSaving = true;
		noteError = null;
		try {
			await saveSessionNote(data.date, noteText);
			noteSaved = true;
			setTimeout(() => { noteSaved = false; }, 2000);
		} catch {
			noteError = '저장 실패. 다시 시도해 주세요.';
		} finally {
			noteSaving = false;
		}
	}
</script>

<div class="flex flex-col">
	{#if data.errorMessage && !data.session}
		<div class="flex flex-col items-center gap-2 px-4 py-10 text-center">
			<p class="text-fg-secondary">세션을 불러올 수 없습니다</p>
			<p class="text-xs text-fg-muted">{data.errorMessage}</p>
			<a href="{base}/coach/plan/{data.goalId}" class="mt-2 text-sm text-semantic-amber hover:underline">← 플랜 상세</a>
		</div>
	{:else if data.session}
		<!-- 헤더 -->
		<div class="border-b border-border-subtle px-4 py-4">
			<div class="mb-1 flex items-center gap-1 text-xs text-fg-muted">
				<a href="{base}/coach" class="hover:underline">코치</a>
				<span>/</span>
				<a href="{base}/coach/plan/{data.session.goal.id}" class="hover:underline">{data.session.goal.name}</a>
				<span>/</span>
				<span>{data.session.week_index}주차 {dayLabel(data.date)}</span>
			</div>
			{#if data.session.adjustment?.adjusted}
				<span class="inline-block rounded-full bg-semantic-amber/10 px-2 py-0.5 text-xs text-semantic-amber">상태 기반 조정</span>
			{/if}
		</div>

		<!-- 원래 계획 -->
		<div class="border-b border-border-subtle px-4 py-4">
			<p class="mb-2 text-xs uppercase tracking-wide text-fg-muted">원래 계획</p>
			<p class="text-sm font-semibold">
				{workoutLabel(data.session.workout.workout_type)}
			</p>
			<div class="mt-1 flex flex-wrap gap-3 text-xs text-fg-secondary">
				{#if data.session.workout.distance_km}
					<span>{data.session.workout.distance_km}km</span>
				{/if}
				{#if paceRange(data.session.workout.target_pace_min, data.session.workout.target_pace_max)}
					<span>{paceRange(data.session.workout.target_pace_min, data.session.workout.target_pace_max)}</span>
				{/if}
			</div>
			{#if data.session.workout.description}
				<p class="mt-1.5 text-xs text-fg-secondary">{data.session.workout.description}</p>
			{/if}
		</div>

		<!-- 조정 섹션 -->
		<div class="border-b border-border-subtle px-4 py-4">
			{#if data.session.adjustment?.adjusted}
				<p class="mb-2 text-xs uppercase tracking-wide text-fg-muted">오늘 상태 기반 조정</p>
				<p class="text-sm font-semibold">
					{workoutLabel(data.session.adjustment.original_type)}
					<span class="font-normal text-fg-muted">→</span>
					{workoutLabel(data.session.adjustment.adjusted_type)}
				</p>
				{#if data.session.adjustment.adjustment_reason_parts.length > 0}
					<div class="mt-2 flex flex-wrap gap-1.5">
						{#each data.session.adjustment.adjustment_reason_parts as part}
							<span class="rounded-full bg-surface-3 px-2.5 py-0.5 text-xs text-fg-secondary">{part}</span>
						{/each}
					</div>
				{/if}
			{:else}
				<p class="text-sm text-fg-muted">조정 없음 — 계획대로 진행</p>
			{/if}
		</div>

		<!-- 세션 메모 -->
		<div class="px-4 py-4">
			<p class="mb-2 text-xs uppercase tracking-wide text-fg-muted">세션 메모</p>
			<textarea
				class="w-full rounded-md border border-border-subtle bg-surface-2 px-3 py-2 text-sm text-fg-primary placeholder:text-fg-muted focus:outline-none focus:ring-1 focus:ring-semantic-teal"
				rows="4"
				placeholder="세션 후 메모 입력..."
				bind:value={noteText}
			></textarea>
			{#if noteError}
				<p class="mt-1 text-xs text-semantic-red">{noteError}</p>
			{/if}
			<div class="mt-2 flex items-center gap-2">
				<button
					class="rounded-md bg-semantic-teal px-4 py-1.5 text-sm font-medium text-white disabled:opacity-50"
					onclick={handleNoteSave}
					disabled={noteSaving || !noteText.trim()}
				>
					{#if noteSaving}저장 중...{:else if noteSaved}저장됨 ✓{:else}저장{/if}
				</button>
			</div>
		</div>
	{/if}
</div>

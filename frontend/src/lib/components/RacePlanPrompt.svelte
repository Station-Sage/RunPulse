<script lang="ts">
	import { say } from '$lib/a11y/say';
	// 대회 → 플랜 반영 질문 (RC §2.6) — 영향 미리보기를 보고 반영 / 나중에 / 조정 안 함 / 되돌리기를 고른다.
	import { modal } from '$lib/overlay';
	import { onMount } from 'svelte';
	import { getRaceImpact, setRacePlan, type ImpactChange, type RaceRow, type RaceView } from '$lib/api/raceCalendar';

	let { race, onClose, onDone }: { race: RaceRow; onClose: () => void; onDone: (r: RaceView) => void } = $props();
	let changes = $state<ImpactChange[] | null>(null);
	let busy = $state(false);
	let error = $state<string | null>(null);
	const applied = $derived(race.plan_state === 'applied' || race.plan_state === 'stale');

	onMount(async () => {
		try { changes = (await getRaceImpact(race.id)).changes; }
		catch (e) { error = e instanceof Error ? e.message : '영향을 불러오지 못했어요'; changes = []; }
	});

	async function choose(action: 'adapt' | 'later' | 'no_adapt' | 'undo') {
		busy = true; error = null;
		try { onDone(await setRacePlan(race.id, action)); }
		catch (e) { error = e instanceof Error ? e.message : '저장하지 못했어요'; busy = false; }
	}
	const label = (r: { workout_type: string; distance_km: number | null }) => r.workout_type === 'rest' ? '휴식' : `${r.workout_type}${r.distance_km ? ` ${r.distance_km}km` : ''}`;
	const btn = 'min-h-11 flex-1 rounded-lg bg-surface-2 disabled:opacity-50';
</script>

<div class="fixed inset-0 z-50 flex items-end bg-scrim lg:items-center lg:justify-center" role="dialog" aria-modal="true" aria-labelledby="race-plan-title" use:modal={{ onClose: () => { if (!busy) onClose(); } }}>
	<div class="max-h-[90vh] w-full space-y-3 overflow-y-auto rounded-t-2xl bg-surface-1 p-4 lg:max-w-md lg:rounded-2xl">
		<p id="race-plan-title" class="text-sm font-medium text-fg-primary">{race.name}에 맞춰 훈련 계획을 조정할까요?</p>
		{#if changes === null}<p class="text-xs text-fg-muted">영향을 확인하는 중…</p>
		{:else if changes.length === 0}<p class="text-xs text-fg-muted">바꿀 계획 행이 없어요. 플랜을 먼저 만들면 반영할 수 있어요.</p>
		{:else}
			<ul class="space-y-1 text-xs">
				{#each changes as c}<li class="flex justify-between gap-2 text-fg-secondary"><span>{c.before.date}</span><span>{label(c.before)} → <b class="text-fg-primary">{label(c.after)}</b></span></li>{/each}
			</ul>
		{/if}
		{#if error}<p class="text-xs text-semantic-red" use:say={{ text: error, level: 'assertive' }}>{error}</p>{/if}
		<div class="flex flex-wrap gap-2">
			<button type="button" class="{btn} bg-semantic-teal text-fg-on-accent" disabled={busy || !changes?.length} onclick={() => choose('adapt')}>{applied ? '다시 반영' : '반영'}</button>
			{#if applied}<button type="button" class={btn} disabled={busy} onclick={() => choose('undo')}>되돌리기</button>{/if}
			<button type="button" class={btn} disabled={busy} onclick={() => choose('later')}>나중에</button>
			<button type="button" class={btn} disabled={busy} onclick={() => choose('no_adapt')}>조정 안 함</button>
		</div>
		<button type="button" class="min-h-11 w-full text-xs text-fg-muted" disabled={busy} onclick={onClose}>닫기</button>
	</div>
</div>

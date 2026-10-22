<script lang="ts">
	// 대회 추가·수정 시트 (RC §2.5) — 과거 날짜는 확인 문장을 한 번 더 보인다. 저장은 부모가 refresh 한다.
	import { modal } from '$lib/overlay';
	import { ApiError } from '$lib/api/client';
	import { createRace, updateRace, type RaceDraft, type RacePriority, type RaceRow } from '$lib/api/raceCalendar';

	let { race = null, today, onClose, onSaved }: {
		race?: RaceRow | null; today: string; onClose: () => void; onSaved: (r: RaceRow, created: boolean) => void;
	} = $props();

	let name = $state(race?.name ?? '');
	let date = $state(race?.race_date ?? '');
	let km = $state(race ? String(race.distance_km) : '');
	let priority = $state<RacePriority>(race?.priority ?? 'B');
	let goalType = $state<string>(race?.goal_type ?? '');
	let goalMin = $state(race?.goal_value ? String(Math.round(race.goal_value / 60)) : '');
	let more = $state(false);
	let taper = $state(race?.taper_days != null ? String(race.taper_days) : '');
	let recovery = $state(race?.recovery_days != null ? String(race.recovery_days) : '');
	let note = $state(race?.note ?? '');
	let pastOk = $state(false);
	let busy = $state(false);
	let error = $state<string | null>(null);

	const isPast = $derived(!!date && date < today);
	const valid = $derived(name.trim() !== '' && !!date && Number(km) > 0 && (!isPast || pastOk) && (goalType !== 'time' || Number(goalMin) > 0));

	async function save() {
		busy = true; error = null;
		const d: RaceDraft = { name: name.trim(), race_date: date, distance_km: Number(km), priority };
		if (goalType) d.goal_type = goalType as RaceDraft['goal_type'];
		if (goalType === 'time') d.goal_value = Math.round(Number(goalMin) * 60);
		if (taper !== '') d.taper_days = Number(taper);
		if (recovery !== '') d.recovery_days = Number(recovery);
		if (note.trim()) d.note = note.trim();
		try {
			const out = race ? await updateRace(race.id, d) : await createRace(d);
			onSaved(out, !race);
		} catch (e) {
			error = e instanceof ApiError && e.code === 'DUPLICATE' ? '같은 날짜·거리의 대회가 이미 있어요' : e instanceof Error ? e.message : '저장하지 못했어요';
			busy = false;
		}
	}
	const inp = 'min-h-11 w-full rounded-lg border border-border-subtle bg-surface-2 px-3 text-sm text-fg-primary focus-visible:outline focus-visible:outline-2 focus-visible:outline-semantic-teal';
</script>

<div class="fixed inset-0 z-50 flex items-end bg-black/40 lg:items-center lg:justify-center" role="dialog" aria-modal="true" aria-labelledby="race-entry-title" use:modal={{ onClose: () => { if (!busy) onClose(); } }}>
	<form class="max-h-[90vh] w-full space-y-3 overflow-y-auto rounded-t-2xl bg-surface-1 p-4 lg:max-w-md lg:rounded-2xl" onsubmit={(e) => { e.preventDefault(); if (valid && !busy) save(); }}>
		<p id="race-entry-title" class="text-sm font-medium text-fg-primary">{race ? '대회 수정' : '대회 추가'}</p>
		<label class="block text-xs text-fg-secondary">이름<input class={inp} bind:value={name} maxlength="80" required /></label>
		<div class="flex gap-2">
			<label class="block flex-1 text-xs text-fg-secondary">날짜<input type="date" class={inp} bind:value={date} required /></label>
			<label class="block w-28 text-xs text-fg-secondary">거리(km)<input class={inp} bind:value={km} inputmode="decimal" required /></label>
		</div>
		{#if isPast}
			<label class="flex min-h-11 items-center gap-2 text-xs text-semantic-amber">
				<input type="checkbox" bind:checked={pastOk} />이미 지난 날짜예요. 지난 대회로 기록할게요
			</label>
		{/if}
		<fieldset class="space-y-1"><legend class="text-xs text-fg-secondary">우선순위</legend>
			<div class="flex gap-2">
				{#each ['A', 'B', 'C'] as p}
					<button type="button" aria-pressed={priority === p} class="min-h-11 flex-1 rounded-lg {priority === p ? 'bg-semantic-teal text-white' : 'bg-surface-2'}" onclick={() => (priority = p as RacePriority)}>{p}</button>
				{/each}
			</div>
		</fieldset>
		{#if priority === 'A'}<p class="text-xs text-fg-muted">A 대회는 한 번에 하나만 둘 수 있어요. 목표와 연결되는 대회예요.</p>{/if}
		<label class="block text-xs text-fg-secondary">목표
			<select class={inp} bind:value={goalType}>
				<option value="">정하지 않음</option><option value="finish">완주</option><option value="time">목표 시간</option><option value="pb">PB 갱신</option>
			</select>
		</label>
		{#if goalType === 'time'}<label class="block text-xs text-fg-secondary">목표 시간(분)<input class={inp} bind:value={goalMin} inputmode="numeric" /></label>{/if}
		<button type="button" class="min-h-11 text-xs text-fg-muted" aria-expanded={more} onclick={() => (more = !more)}>{more ? '접기' : '더 설정'}</button>
		{#if more}
			<div class="flex gap-2">
				<label class="block flex-1 text-xs text-fg-secondary">테이퍼(일)<input class={inp} bind:value={taper} inputmode="numeric" placeholder="자동" /></label>
				<label class="block flex-1 text-xs text-fg-secondary">회복(일)<input class={inp} bind:value={recovery} inputmode="numeric" placeholder="자동" /></label>
			</div>
			<label class="block text-xs text-fg-secondary">메모<input class={inp} bind:value={note} maxlength="500" /></label>
		{/if}
		{#if error}<p class="text-xs text-semantic-red" role="alert">{error}</p>{/if}
		<div class="flex gap-2">
			<button type="button" class="min-h-11 flex-1 rounded-lg bg-surface-2" disabled={busy} onclick={onClose}>닫기</button>
			<button type="submit" class="min-h-11 flex-1 rounded-lg bg-semantic-teal text-white disabled:opacity-50" disabled={!valid || busy}>저장</button>
		</div>
	</form>
</div>

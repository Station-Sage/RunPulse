<script lang="ts">
	// 대회 상세·동작 시트 (RC §2.7~2.13) — 수정·플랜 반영·취소(목표 연결 확인)·복원(과거 확인·A 충돌)·예정으로 되돌리기.
	import { ApiError } from '$lib/api/client';
	import {
		cancelRace, reopenRace, restoreRace, type ExistingA, type RaceRow
	} from '$lib/api/raceCalendar';
	import { chipOf, dDayLabel, goalLine, kmLabel } from '$lib/raceCalendarView';

	let { race, today, goalLinked, needsReview, onClose, onEdit, onPlan, onChanged }: {
		race: RaceRow; today: string; goalLinked: boolean; needsReview: boolean; onClose: () => void;
		onEdit: () => void; onPlan: () => void; onChanged: (message: string) => void;
	} = $props();

	type Ask = null | { kind: 'cancel_goal' } | { kind: 'past' } | { kind: 'a_conflict'; existing: ExistingA; op: 'restore' | 'reopen' };
	let ask = $state<Ask>(null);
	let busy = $state(false);
	let error = $state<string | null>(null);

	async function run(fn: () => Promise<string>) {
		busy = true; error = null;
		try { onChanged(await fn()); }
		catch (e) {
			busy = false;
			if (e instanceof ApiError) {
				const d = e.details as { needs_confirm?: boolean; existing_a?: ExistingA } | undefined;
				if (e.code === 'GOAL_LINKED' && d?.needs_confirm) { ask = { kind: 'cancel_goal' }; return; }
				if (e.code === 'CONFIRM_PAST') { ask = { kind: 'past' }; return; }
				if (e.code === 'A_CONFLICT' && d?.existing_a) { ask = { kind: 'a_conflict', existing: d.existing_a, op: needsReview ? 'reopen' : 'restore' }; return; }
			}
			error = e instanceof Error ? e.message : '처리하지 못했어요';
		}
	}
	const cancel = (withGoal: boolean) => run(async () => { await cancelRace(race.id, withGoal); return `${race.name}을 취소했어요`; });
	const restore = (o: { confirm_past?: boolean; demote?: boolean; link?: boolean } = {}) => run(async () => {
		const opts = { confirm_past: o.confirm_past, demote_existing_a: o.demote, goal_link: o.link ? { race_id: race.id } : undefined };
		const out = await restoreRace(race.id, opts);
		return out.restore.replan_applied === false ? `${race.name}을 복원했어요. 플랜에는 다시 반영하지 못해 '변경 후 미반영'으로 표시돼요` : `${race.name}을 복원했어요`;
	});
	const reopen = (o: { demote?: boolean; link?: boolean } = {}) => run(async () => {
		await reopenRace(race.id, { demote_existing_a: o.demote, goal_link: o.link ? { race_id: race.id } : undefined });
		return `${race.name}을 예정으로 되돌렸어요`;
	});
	function confirmConflict(a: Extract<Ask, { kind: 'a_conflict' }>) {
		const o = { demote: true, link: !!a.existing.active_goal_id };
		return a.op === 'reopen' ? reopen(o) : restore({ confirm_past: race.race_date < today, ...o });
	}
	const btn = 'min-h-11 flex-1 rounded-lg bg-surface-2 disabled:opacity-50';
</script>

<svelte:window onkeydown={(e) => e.key === 'Escape' && !busy && (ask ? (ask = null) : onClose())} />
<div class="fixed inset-0 z-50 flex items-end bg-black/40 lg:items-center lg:justify-center" role="dialog" aria-modal="true" aria-labelledby="race-detail-title">
	<div class="max-h-[90vh] w-full space-y-3 overflow-y-auto rounded-t-2xl bg-surface-1 p-4 lg:max-w-md lg:rounded-2xl">
		<p id="race-detail-title" class="text-sm font-medium text-fg-primary">{race.name} <span class="text-fg-muted">({race.priority})</span></p>
		<p class="text-xs text-fg-secondary">{race.race_date}{needsReview ? '' : ` · ${dDayLabel(race.race_date, today)}`} · {kmLabel(race.distance_km)}{goalLine(race) ? ` · ${goalLine(race)}` : ''}</p>
		<p class="text-xs text-fg-muted">{needsReview ? '확인 필요' : chipOf(race, goalLinked)}</p>
		{#if race.note}<p class="text-xs text-fg-secondary">{race.note}</p>{/if}
		{#if ask?.kind === 'cancel_goal'}
			<p class="text-sm text-fg-primary">연결된 목표도 함께 취소됩니다. 취소하시겠습니까?</p>
			<div class="flex gap-2"><button type="button" class={btn} disabled={busy} onclick={() => (ask = null)}>아니요</button><button type="button" class="{btn} bg-semantic-red text-white" disabled={busy} onclick={() => cancel(true)}>취소하기</button></div>
		{:else if ask?.kind === 'past'}
			<p class="text-sm text-fg-primary">지난 날짜의 대회예요. 지난 대회로 복원할까요?</p>
			<div class="flex gap-2"><button type="button" class={btn} disabled={busy} onclick={() => (ask = null)}>아니요</button><button type="button" class="{btn} bg-semantic-teal text-white" disabled={busy} onclick={() => restore({ confirm_past: true })}>복원</button></div>
		{:else if ask?.kind === 'a_conflict'}
			{@const a = ask}
			<p class="text-sm text-fg-primary">이미 A 대회 '{a.existing.name}'({a.existing.race_date})가 있어요. 그 대회를 B로 바꾸고 이 대회를 A로 둘까요?{a.existing.active_goal_id ? ' 활성 목표는 이 대회로 옮겨져요.' : ''}</p>
			<div class="flex gap-2"><button type="button" class={btn} disabled={busy} onclick={() => (ask = null)}>아니요</button><button type="button" class="{btn} bg-semantic-teal text-white" disabled={busy} onclick={() => confirmConflict(a)}>바꾸기</button></div>
		{:else}
			<div class="flex flex-wrap gap-2">
				{#if race.status === 'cancelled'}
					<button type="button" class="{btn} bg-semantic-teal text-white" disabled={busy} onclick={() => restore()}>복원</button>
				{:else if needsReview}
					<button type="button" class="{btn} bg-semantic-teal text-white" disabled={busy} onclick={() => reopen()}>예정으로 되돌리기</button>
				{:else if race.status === 'planned'}
					<button type="button" class={btn} onclick={onEdit}>수정</button>
					<button type="button" class={btn} onclick={onPlan}>플랜 반영</button>
					<button type="button" class="{btn} text-semantic-red" disabled={busy} onclick={() => cancel(false)}>취소</button>
				{/if}
			</div>
		{/if}
		{#if error}<p class="text-xs text-semantic-red" role="alert">{error}</p>{/if}
		<button type="button" class="min-h-11 w-full text-xs text-fg-muted" disabled={busy} onclick={onClose}>닫기</button>
	</div>
</div>

<script lang="ts">
	// 플랜 행 직접 조정 시트 — 줄이기/쉬기/건너뛰기 (ADR-035, DESIGN-PLAN-ROW-ACTION).
	import { base } from '$app/paths';
	import { previewWorkoutAction } from '$lib/api/plan';
	import { workoutLabel } from '$lib/format';
	import {
		MAX_REDUCE_PCT, REASONS, loadDeltaView, moveCandidates, opAvailability, reduceInput, reducePreview, weekPreview, type LoadDelta, type RowActionMode, type RowOp
	} from '$lib/rowActionView';
	import type { PlannedWorkout } from '$lib/types';

	let {
		workout,
		mode,
		weekKm = null,
		crsPending = false,
		busy = false,
		error = null,
		onApply,
		onClose,
		today = workout.date
	}: {
		workout: PlannedWorkout;
		mode: RowActionMode;
		weekKm?: number | null;
		crsPending?: boolean;
		busy?: boolean;
		error?: string | null;
		onApply: (op: RowOp, pct: number | undefined, reason: string | undefined, toDate?: string, reps?: number) => void;
		today?: string;
		onClose: () => void;
	} = $props();

	let op = $state<RowOp | null>(null);
	let pct = $state(20);
	$effect(() => { if (!inp.free && inp.options.length) { pct = inp.options[0]; reps = inp.options[0]; } });
	let custom = $state(false);
	let reason = $state<string | undefined>(undefined);
	let toDate = $state<string | undefined>(undefined);
	const days = $derived(moveCandidates(today));
	let root: HTMLElement | undefined = $state();

	const avail = $derived(opAvailability(workout));
	const km = $derived(workout.distance_km ?? 0);
	const inp = $derived(reduceInput(workout));
	let reps = $state(1);
	const isReps = $derived(inp.kind === 'reps');
	const prev = $derived(isReps ? { km, valid: inp.options.includes(reps), hint: null } : !inp.free && !inp.options.includes(pct) ? { km, valid: false, hint: null } : reducePreview(km, pct));
	const canApply = $derived(!busy && op !== null && (op !== 'reduce' || (avail.reduce.ok && prev.valid)) && (op !== 'move' || !!toDate));
	const cut = $derived(op === 'reduce' && !isReps ? km - prev.km : op === 'move' || (op === 'reduce' && isReps) ? 0 : km);
	const week = $derived(weekKm != null && op ? weekPreview(weekKm, cut) : null);

	let delta = $state<LoadDelta | null>(null);
	$effect(() => {
		const o = op, p = pct, r = reps, ok = canApply;
		delta = null;
		if (!o || o === 'move' || !ok || mode === 'locked') return;
		let live = true;
		previewWorkoutAction(workout.id, { op: o, pct: o === 'reduce' && !isReps ? p : undefined, reps: o === 'reduce' && isReps ? r : undefined })
			.then((x) => { if (live) delta = x.load_delta; })
			.catch(() => {});
		return () => { live = false; };
	});
	const dv = $derived(loadDeltaView(delta));

	$effect(() => {
		root?.querySelector<HTMLElement>('button:not([disabled]), a')?.focus();
	});

	function onKey(e: KeyboardEvent) {
		if (e.key === 'Escape') return onClose();
		if (e.key !== 'Tab' || !root) return;
		const f = [...root.querySelectorAll<HTMLElement>('button:not([disabled]), a, input')];
		if (!f.length) return;
		const first = f[0], last = f[f.length - 1];
		if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
		else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
	}

	const OPS: { key: RowOp; label: string; sub: string }[] = [
		{ key: 'reduce', label: '줄이기', sub: '거리를 비율로 줄여요' },
		{ key: 'easy', label: '이지로 바꾸기', sub: '같은 거리를 쉬운 러닝으로 해요' },
		{ key: 'rest', label: '쉬기', sub: '오늘은 휴식으로 바꿔요' },
		{ key: 'skip', label: '건너뛰기', sub: '이 세션을 하지 않아요' },
		{ key: 'move', label: '옮기기', sub: '같은 주 다른 날로 옮겨요' }
	];
</script>

<svelte:window onkeydown={onKey} />

<div class="fixed inset-0 z-[60] bg-black/50" role="presentation" onclick={onClose}></div>
<div
	bind:this={root}
	role="dialog"
	aria-modal="true"
	aria-label="세션 바꾸기"
	data-testid="row-action-sheet"
	class="fixed inset-x-0 bottom-0 z-[61] max-h-[85vh] overflow-y-auto rounded-t-2xl border border-border-subtle bg-surface-1 p-4 lg:inset-x-auto lg:bottom-auto lg:right-6 lg:top-24 lg:w-80 lg:rounded-2xl"
>
	<p class="text-sm font-semibold">
		{workoutLabel(workout.workout_type)}{km ? ` ${km}km` : ''} · {workout.date.slice(5)}
	</p>

	{#if mode === 'locked'}
		<p class="mt-2 text-sm text-fg-secondary">오늘 세션만 바꿀 수 있어요. 미래 세션은 당일에 조정하거나 코치와 상의해 보세요.</p>
		<div class="mt-3 flex gap-2">
			<a href="{base}/coach/new?ctx=plan_session:{workout.id}" class="flex h-11 flex-1 items-center justify-center rounded-lg bg-fg-primary text-sm font-medium text-surface-1">Coach에게 묻기</a>
			<button type="button" class="h-11 rounded-lg border border-border-subtle px-4 text-sm" onclick={onClose}>닫기</button>
		</div>
	{:else}
		{#if crsPending}
			<p class="mt-2 text-xs text-semantic-amber">코치 조정이 있어요 · 적용하면 직접 조정으로 대신해요</p>
		{/if}
		<div role="radiogroup" aria-label="조정 방식" class="mt-3 flex flex-col gap-2">
			{#each OPS as o (o.key)}
				{@const ok = o.key === 'reduce' ? avail.reduce.ok : true}
				<button
					type="button"
					role="radio"
					aria-checked={op === o.key}
					disabled={!ok}
					data-testid="row-op-{o.key}"
					class="flex min-h-11 flex-col items-start rounded-lg border px-3 py-2 text-left disabled:opacity-40 {op === o.key ? 'border-fg-primary bg-surface-2' : 'border-border-subtle'}"
					onclick={() => (op = o.key)}
				>
					<span class="text-sm font-medium">{o.label}</span>
					<span class="text-xs text-fg-muted">{o.key === 'reduce' && avail.reduce.hint ? avail.reduce.hint : o.key === 'move' && avail.move.hint ? avail.move.hint : o.key === 'easy' && avail.easy.hint ? avail.easy.hint : o.sub}</span>
				</button>
			{/each}
		</div>

		{#if op === 'reduce'}
			<div class="mt-3 flex flex-wrap items-center gap-2" role="group" aria-label={isReps ? '줄일 반복 수' : '줄일 비율'}>
				{#each inp.options as p (p)}
					{@const sel = isReps ? reps === p : !custom && pct === p}
					<button type="button" data-testid="reduce-chip-{p}" class="h-11 rounded-full border px-4 text-sm {sel ? 'border-fg-primary bg-surface-2' : 'border-border-subtle'}" onclick={() => { if (isReps) reps = p; else { pct = p; custom = false; } }}>{isReps ? `−${p}회` : `−${p}%`}</button>
				{/each}
				{#if inp.free}
					<button type="button" class="h-11 rounded-full border px-4 text-sm {custom ? 'border-fg-primary bg-surface-2' : 'border-border-subtle'}" onclick={() => (custom = true)}>다른 비율</button>
					{#if custom}
						<input type="number" min="1" max={MAX_REDUCE_PCT} bind:value={pct} aria-label="줄일 비율(%)" class="h-11 w-20 rounded-lg border border-border-subtle bg-surface-2 px-2 text-sm" />
					{/if}
				{/if}
			</div>
		{/if}

		{#if op === 'move'}
			<div class="mt-3 flex flex-wrap gap-2" role="group" aria-label="옮길 날짜">
				{#each days as d (d.date)}
					<button type="button" aria-pressed={toDate === d.date} data-testid="move-day-{d.date}" class="h-11 rounded-full border px-4 text-sm {toDate === d.date ? 'border-fg-primary bg-surface-2' : 'border-border-subtle'}" onclick={() => (toDate = d.date)}>{d.label}</button>
				{/each}
			</div>
		{/if}

		{#if op}
			<div class="mt-3 flex gap-2" role="group" aria-label="이유">
				{#each REASONS as r (r.key)}
					<button type="button" aria-pressed={reason === r.key} class="h-11 rounded-full border px-4 text-sm {reason === r.key ? 'border-fg-primary bg-surface-2' : 'border-border-subtle'}" onclick={() => (reason = reason === r.key ? undefined : r.key)}>{r.label}</button>
				{/each}
			</div>
		{/if}

		<p class="mt-3 min-h-5 text-xs text-fg-secondary" aria-live="polite">
			{#if op === 'reduce'}{isReps ? `반복 ${reps}회 줄여요` : (prev.hint ?? `${km}km → ${prev.km}km`)}{:else if op === 'easy'}같은 거리를 이지 페이스로 해요{:else if op === 'rest'}휴식으로 바꿔요{:else if op === 'skip'}이 세션을 건너뛰어요{:else if op === 'move'}{toDate ? `${toDate.slice(5).replace('-', '/')}로 옮겨요 · 그날이 쉬운 날이면 서로 맞바꿔요` : '옮길 날을 골라 주세요'}{/if}
			{#if week && op !== 'move'} · 이번 주 {week.before}→{week.after}km{/if}
		</p>
		{#if dv}<p data-testid="load-delta" class="text-xs {dv.tone === 'warn' ? 'text-semantic-amber' : 'text-fg-muted'}">{dv.text}</p>{/if}
		{#if error}<p class="mt-1 text-xs text-semantic-red" role="alert">{error}</p>{/if}

		<div class="mt-3 flex gap-2">
			<button type="button" data-testid="row-action-apply" class="h-11 flex-1 rounded-lg bg-fg-primary text-sm font-medium text-surface-1 disabled:opacity-40" disabled={!canApply} onclick={() => op && onApply(op, op === 'reduce' && !isReps ? pct : undefined, reason, op === 'move' ? toDate : undefined, op === 'reduce' && isReps ? reps : undefined)}>적용</button>
			<button type="button" class="h-11 rounded-lg border border-border-subtle px-4 text-sm" onclick={onClose}>취소</button>
		</div>
	{/if}
</div>

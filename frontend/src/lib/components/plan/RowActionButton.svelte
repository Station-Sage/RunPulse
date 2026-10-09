<script lang="ts">
	// 행 액션 진입 버튼 + 시트 + 성공 토스트(되돌리기). via 로 진입점을 구분한다.
	import { revertAdjustment, workoutAction } from '$lib/api/plan';
	import Toast from '$lib/components/Toast.svelte';
	import RowActionSheet from './RowActionSheet.svelte';
	import { actionErrorText, rowActionMode, toastText, type RowOp } from '$lib/rowActionView';
	import type { PlannedWorkout } from '$lib/types';

	let {
		workout,
		today,
		via,
		weekKm = null,
		crsPending = false,
		label = '⋯',
		onChange
	}: {
		workout: PlannedWorkout;
		today: string;
		via: 'plan' | 'session' | 'today';
		weekKm?: number | null;
		crsPending?: boolean;
		label?: string;
		onChange?: () => void;
	} = $props();

	let open = $state(false);
	let busy = $state(false);
	let error = $state<string | null>(null);
	let toast = $state<{ message: string; id: number } | null>(null);
	let btn: HTMLButtonElement | undefined = $state();

	const mode = $derived(rowActionMode(workout, today));

	function close() {
		open = false;
		error = null;
		btn?.focus();
	}

	async function apply(op: RowOp, pct: number | undefined, reason: string | undefined, toDate?: string, reps?: number) {
		if (busy) return;
		busy = true;
		error = null;
		try {
			const res = await workoutAction(workout.id, { op, pct, reps, reason, to_date: toDate, via });
			toast = { message: toastText(op, res), id: res.adjustment.id };
			open = false;
			btn?.focus();
			onChange?.();
		} catch (e) {
			error = actionErrorText(e);
		} finally {
			busy = false;
		}
	}

	async function undo() {
		if (!toast) return;
		try {
			await revertAdjustment(toast.id, via);
			toast = { message: '원래 계획으로 돌렸어요', id: 0 };
		} catch (e) {
			toast = { message: actionErrorText(e), id: 0 };
		}
		onChange?.();
	}
</script>

{#if mode !== 'hidden'}
	<button
		bind:this={btn}
		type="button"
		data-testid="row-action-btn"
		aria-haspopup="dialog"
		aria-label="이 세션 바꾸기"
		class="flex h-11 min-w-11 shrink-0 items-center justify-center rounded-lg text-sm text-fg-secondary hover:bg-surface-2"
		onclick={() => (open = true)}>{label}</button
	>
{/if}
{#if open}
	<RowActionSheet {today} {workout} {mode} {weekKm} {crsPending} {busy} {error} onApply={apply} onClose={close} />
{/if}
<Toast open={toast !== null} message={toast?.message ?? ''} onUndo={toast && toast.id ? undo : undefined} onDismiss={() => (toast = null)} />

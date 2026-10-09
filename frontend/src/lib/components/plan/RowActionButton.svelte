<script lang="ts">
	// 행 액션 진입 버튼 + 시트 + 성공 토스트(되돌리기). via 로 진입점을 구분한다.
	import { revertAdjustment, workoutAction } from '$lib/api/plan';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import Toast from '$lib/components/Toast.svelte';
	import { toastAdvisory } from '$lib/replanBanner';
	import RowActionSheet from './RowActionSheet.svelte';
	import { actionErrorText, rowActionMode, rowSheetParam, toastText, type RowOp } from '$lib/rowActionView';
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
	let bannerShown = false;
	let error = $state<string | null>(null);
	let toast = $state<{ message: string; id: number } | null>(null);
	let btn: HTMLButtonElement | undefined = $state();

	const mode = $derived(rowActionMode(workout, today));
	const sheetKey = $derived(rowSheetParam(workout.id));

	function syncUrl(v: boolean) {
		const u = new URL(page.url);
		if (v) u.searchParams.set('sheet', sheetKey);
		else if (u.searchParams.get('sheet') === sheetKey) u.searchParams.delete('sheet');
		else return;
		goto(u, { replaceState: true, keepFocus: true, noScroll: true });
	}

	// ?sheet=row-<id> 딥링크·새로고침 복원 (숨김 모드는 열지 않는다)
	$effect(() => {
		if (mode !== 'hidden' && page.url.searchParams.get('sheet') === sheetKey) open = true;
	});

	function close() {
		open = false;
		syncUrl(false);
		error = null;
		btn?.focus();
	}

	async function apply(op: RowOp, pct: number | undefined, reason: string | undefined, toDate?: string, reps?: number, pain?: { level: string; sites: string[] }) {
		if (busy) return;
		busy = true;
		error = null;
		try {
			const res = await workoutAction(workout.id, { op, pct, reps, reason, pain_level: pain?.level, pain_sites: pain?.sites, to_date: toDate, via });
			const adv = toastAdvisory(res.advisories, bannerShown);
			toast = { message: toastText(op, res) + (adv ? ` · ${adv}` : ''), id: res.adjustment.id };
			open = false;
			syncUrl(false);
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
		onclick={() => { open = true; syncUrl(true); }}>{label}</button
	>
{/if}
{#if open}
	<RowActionSheet {today} {workout} {mode} {weekKm} {crsPending} {busy} {error} onBanner={(v) => (bannerShown = v)} onApply={apply} onClose={close} />
{/if}
<Toast open={toast !== null} message={toast?.message ?? ''} onUndo={toast && toast.id ? undo : undefined} onDismiss={() => (toast = null)} />

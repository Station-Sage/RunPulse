<script lang="ts">
	// 새 플랜 생성 화면의 훈련 방식 선택 — 거리·운동 요일·목표 시간이 바뀌면 후보와 추천을 다시 받는다.
	import MethodPicker from './MethodPicker.svelte';
	import { getMethodDraft } from '$lib/api/plan';
	import type { PlanMethodDraft } from '$lib/types/planMethods';

	let {
		distanceKm,
		runDays,
		targetTimeSec,
		selected = $bindable<string | null>(null)
	}: { distanceKm: number | null; runDays: number; targetTimeSec: number | undefined; selected: string | null } = $props();

	let draft = $state<PlanMethodDraft | null>(null);
	let failed = $state(false);
	let seq = 0;

	$effect(() => {
		const km = distanceKm;
		const days = runDays;
		const tts = targetTimeSec;
		if (km == null || days < 1) {
			draft = null;
			return;
		}
		const my = ++seq;
		getMethodDraft(km, days, tts)
			.then((d) => {
				if (my !== seq) return;
				draft = d;
				failed = false;
				if (!selected || !d.methods.some((m) => m.id === selected)) selected = d.recommended;
			})
			.catch(() => {
				if (my === seq) failed = true;
			});
	});

</script>

{#if draft && draft.methods.length > 1}
	<div data-testid="new-plan-method">
		<p class="mb-2 text-xs text-fg-muted">
			{draft.pending ? 'AI가 기록을 보고 추천을 준비하고 있어요. 지금은 기본 추천이에요.' : '내 기록 기준 추천이에요. 직접 고를 수도 있어요.'}
		</p>
		<MethodPicker methods={draft.methods} current={draft.current} selected={selected ?? draft.recommended} rec={draft} onselect={(id) => (selected = id)} />
	</div>
{:else if failed}
	<p class="text-xs text-fg-muted">훈련 방식 후보를 불러오지 못했어요. 기본 방식으로 만들어져요.</p>
{/if}

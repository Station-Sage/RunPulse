<script lang="ts">
	// 03e-coach.md 5-C — 플랜 없음 화면.
	import type { PlanGatewayData } from './+page';
	import { base } from '$app/paths';
	import { tick } from 'svelte';
	import { inlineConfirm } from '$lib/overlay';
	import { goto, invalidateAll } from '$app/navigation';
	import { planNewHref, roadmapLabel } from '$lib/planPrefill';
	import { restorePlan } from '$lib/api/plan';
	import { ApiError } from '$lib/api/client';

	let { data }: { data: PlanGatewayData } = $props();
	let confirmId = $state<number | null>(null);
	let busy = $state(false);
	async function cancelRestore(id: number) {
		confirmId = null;
		await tick();
		document.getElementById(`restore-open-${id}`)?.focus();
	}
	let err = $state<string | null>(null);

	async function doRestore(id: number) {
		busy = true;
		err = null;
		try {
			await restorePlan(id, data.activeId);
			await invalidateAll();
			await goto(`${base}/coach/plan/${id}`);
		} catch (e) {
			err = e instanceof ApiError && e.code === 'ACTIVE_PLAN_EXISTS'
				? '그 사이 활성 플랜이 바뀌었어요. 새로고침 후 다시 시도해주세요.'
				: '플랜을 복원하지 못했어요. 다시 시도해주세요.';
		} finally {
			busy = false;
			confirmId = null;
		}
	}
</script>

<svelte:head><title>훈련 플랜 · RunPulse</title></svelte:head>

<div class="flex flex-col items-center justify-center gap-6 px-4 py-16 text-center">
	<div>
		{#if data.goal}
			<p class="text-base font-medium">{data.goal.name} D-{data.goal.days_left}</p>
		{/if}
		<p class="text-base text-fg-secondary">
			목표 레이스를 입력하면 맞춤 프로그램을 만들어드립니다.
		</p>
		{#if data.ctlCurrent != null}
			<p class="mt-2 text-sm text-fg-muted">
				현재 피트니스 수준: CTL {Math.round(data.ctlCurrent)} (분석 완료)
			</p>
		{/if}
	</div>

	<a
		href={data.goal ? planNewHref(base, data.goal) : `${base}/coach/plan/new`}
		class="rounded-lg bg-fg-primary px-6 py-3 text-sm font-medium text-surface-1"
	>
		{data.goal ? roadmapLabel(data.goal.days_left) + ' →' : '새 프로그램 만들기 →'}
	</a>
</div>

{#if data.restorable.length > 0}
	<section class="px-4 pb-10" aria-label="지난 플랜">
		<h2 class="mb-2 text-sm font-medium text-fg-primary">지난 플랜 복원</h2>
		{#if data.activeId != null}
			<p class="mb-2 text-xs text-fg-muted">복원하면 현재 활성 플랜의 남은 일정은 지난 플랜으로 보관돼요.</p>
		{/if}
		<ul class="flex flex-col gap-2">
			{#each data.restorable as p (p.goal_id)}
				<li class="rounded-lg border border-border-subtle bg-surface-2 p-3 text-sm" data-testid="restorable-plan">
					<p class="font-medium">{p.name}</p>
					<p class="text-xs text-fg-muted">
						{p.distance_km}km{p.race_date ? ` · 레이스 ${p.race_date}` : ''} · 남은 일정 {p.rows}개
					</p>
					{#if confirmId === p.goal_id}
						<span role="group" aria-label="복원 확인" class="mt-2 flex flex-wrap items-center gap-2" data-testid="restore-confirm" use:inlineConfirm={{ onCancel: () => cancelRestore(p.goal_id) }}>
							<button class="min-h-11 underline" disabled={busy} onclick={() => doRestore(p.goal_id)}>복원</button>
							<button class="min-h-11 underline" data-autofocus disabled={busy} onclick={() => cancelRestore(p.goal_id)}>취소</button>
						</span>
					{:else}
						<button id="restore-open-{p.goal_id}" class="mt-1 min-h-11 text-xs underline" disabled={busy} onclick={() => (confirmId = p.goal_id)}>복원하기</button>
					{/if}
				</li>
			{/each}
		</ul>
		{#if err}<p class="mt-2 text-xs text-semantic-red" role="alert">{err}</p>{/if}
	</section>
{/if}

<script lang="ts">
	// /welcome — 신규 계정 4단계 온보딩(40 design §2.10). 진행은 서버(/me/preferences)에 저장.
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import Step0Intro from '$lib/components/welcome/Step0Intro.svelte';
	import Step1Connect from '$lib/components/welcome/Step1Connect.svelte';
	import Step2Range from '$lib/components/welcome/Step2Range.svelte';
	import Step3Goal from '$lib/components/welcome/Step3Goal.svelte';
	import Step4Baseline from '$lib/components/welcome/Step4Baseline.svelte';
	import { patchPreferences } from '$lib/api/me';
	import { isLast, nextStep, prevStep, startStep } from '$lib/onboarding';

	let { data }: { data: { saved: number; query: string | null } } = $props();
	let step = $state(startStep(data.query, data.saved));

	async function go(n: number) {
		step = n;
		await patchPreferences({ onboarding_step: n }).catch(() => {});
	}
	async function finish(state: 'done' | 'skipped') {
		await patchPreferences({ onboarding: state }).catch(() => {});
		await goto(`${base}/today`);
	}
</script>

<svelte:head><title>시작하기 · RunPulse</title></svelte:head>

<div class="mx-auto flex max-w-md flex-col gap-4 px-4 py-8">
	{#if step === 0}<Step0Intro onStart={() => go(1)} />
	{:else if step === 1}<Step1Connect onConnectedChange={() => {}} />
	{:else if step === 2}<Step2Range onStarted={() => go(3)} />
	{:else if step === 3}<Step3Goal />
	{:else}<Step4Baseline />{/if}

	{#if step > 0}
		<div class="flex items-center justify-between border-t border-border-subtle pt-3 text-sm">
			<button type="button" class="text-fg-muted underline" onclick={() => finish('skipped')}>건너뛰고 둘러보기</button>
			<span class="flex gap-3">
				<button type="button" class="text-fg-secondary" onclick={() => go(prevStep(step))}>이전</button>
				{#if isLast(step)}
					<button type="button" class="rounded-lg bg-fg-primary px-3 py-1.5 text-surface-1" onclick={() => finish('done')}>완료</button>
				{:else}
					<button type="button" class="rounded-lg bg-fg-primary px-3 py-1.5 text-surface-1" onclick={() => go(nextStep(step))}>다음</button>
				{/if}
			</span>
		</div>
	{/if}
</div>

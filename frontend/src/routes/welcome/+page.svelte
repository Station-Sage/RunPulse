<script lang="ts">
	import PageHead from '$lib/components/ui/PageHead.svelte';
	// /welcome — 신규 계정 4단계 온보딩(40 design §2.10). 진행은 서버(/me/preferences)에 저장.
	// E-25/S-20: 단계는 `?step=` 에 반영(뒤로가기 = 이전 단계), 저장 실패는 화면에 알린다.
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import { page } from '$app/state';
	import { onMount } from 'svelte';
	import { say } from '$lib/a11y/say';
	import Step0Intro from '$lib/components/welcome/Step0Intro.svelte';
	import Step1Connect from '$lib/components/welcome/Step1Connect.svelte';
	import Step2Range from '$lib/components/welcome/Step2Range.svelte';
	import Step3Goal from '$lib/components/welcome/Step3Goal.svelte';
	import Step4Baseline from '$lib/components/welcome/Step4Baseline.svelte';
	import { patchPreferences } from '$lib/api/me';
	import { isLast, nextStep, prevStep, startStep, stepHref } from '$lib/onboarding';

	let { data }: { data: { saved: number; query: string | null } } = $props();
	const step = $derived(startStep(page.url.searchParams.get('step'), data.saved));
	let notice = $state<string | null>(null);

	onMount(() => {
		// 첫 진입(쿼리 없음)도 주소에 단계를 남겨, 다음 단계에서 뒤로가면 이 단계로 돌아온다
		if (page.url.searchParams.get('step') === null) void goto(stepHref(base, step), { replaceState: true, noScroll: true, keepFocus: true });
	});

	async function go(n: number) {
		notice = null;
		await goto(stepHref(base, n), { noScroll: true });
		await patchPreferences({ onboarding_step: n }).catch(() => {
			notice = '진행 상황을 저장하지 못했어요. 다음에 들어오면 이 단계부터 이어지지 않을 수 있어요.';
		});
	}
	async function finish(state: 'done' | 'skipped') {
		notice = null;
		try {
			await patchPreferences({ onboarding: state });
		} catch {
			notice = '설정을 저장하지 못했어요. 네트워크를 확인하고 다시 눌러 주세요.';
			return;
		}
		await goto(`${base}/today`);
	}
</script>

<PageHead title="시작하기" heading={null} />

<div class="mx-auto flex max-w-md flex-col gap-4 px-4 py-8">
	{#if step === 0}<Step0Intro onStart={() => go(1)} />
	{:else if step === 1}<Step1Connect onConnectedChange={() => {}} />
	{:else if step === 2}<Step2Range onStarted={() => go(3)} />
	{:else if step === 3}<Step3Goal />
	{:else}<Step4Baseline />{/if}

	{#if notice}
		<p class="text-xs text-semantic-red" data-testid="welcome-notice" use:say={{ text: notice, level: 'assertive' }}>{notice}</p>
	{/if}

	{#if step > 0}
		<div class="flex items-center justify-between border-t border-border-subtle pt-3 text-sm">
			<button type="button" class="min-h-11 text-fg-muted underline" onclick={() => finish('skipped')}>건너뛰고 둘러보기</button>
			<span class="flex gap-3">
				<button type="button" class="min-h-11 text-fg-secondary" onclick={() => go(prevStep(step))}>이전</button>
				{#if isLast(step)}
					<button type="button" class="min-h-11 rounded-lg bg-fg-primary px-3 py-1.5 text-surface-1" onclick={() => finish('done')}>완료</button>
				{:else}
					<button type="button" class="min-h-11 rounded-lg bg-fg-primary px-3 py-1.5 text-surface-1" onclick={() => go(nextStep(step))}>다음</button>
				{/if}
			</span>
		</div>
	{/if}
</div>

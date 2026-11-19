<script lang="ts">
	// 오늘 훈련 상세 분석 — 큐 사용 가능할 때만 노출. 누르면 코치 스레드가 열리고 분석이 첫 답변으로 채워진다.
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import { onMount } from 'svelte';
	import { announce } from '$lib/a11y/announce';
	import { getDeepAnalysis, startDeepAnalysis, type DeepState } from '$lib/api/deepAnalysis';

	let st = $state<DeepState | null>(null);
	let busy = $state(false);
	let msg = $state('');

	async function start() {
		busy = true;
		msg = '';
		try {
			const res = await startDeepAnalysis(st?.activity_id ?? undefined);
			await goto(`${base}/coach/${res.thread.id}?from=coach`);
		} catch (e) {
			msg = (e as { message?: string }).message ?? '분석을 시작하지 못했어요';
			busy = false;
			announce(msg);
		}
	}

	onMount(async () => {
		st = await getDeepAnalysis().catch(() => null);
	});
</script>

{#if st?.available && st.activity_id}
	<section class="mx-4 my-3 space-y-2 rounded-lg bg-surface-2 p-3 text-sm" data-testid="deep-analysis" aria-label="오늘 훈련 상세 분석">
		<p class="font-medium">오늘 훈련 상세 분석</p>
		<p class="text-xs text-fg-secondary">최근 러닝을 AI가 심박·페이스·랩까지 살펴보고 풀이해요. 1~3분 걸리고, 결과는 코칭 대화로 이어져요.</p>
		{#if msg}<p class="text-xs text-semantic-red">{msg}</p>{/if}
		<button class="min-h-11 rounded-lg bg-surface-1 px-4" disabled={busy} onclick={start}>{busy ? '여는 중…' : '분석 시작'}</button>
	</section>
{/if}

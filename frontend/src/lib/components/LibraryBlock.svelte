<script lang="ts" generics="T">
	// Library 홈 블록 — 자체 로드·스켈레톤·오류(재시도). 한 블록 실패가 다른 블록을 막지 않는다.
	import type { Snippet } from 'svelte';
	import Skeleton from './Skeleton.svelte';
	import ErrorState from './ErrorState.svelte';

	let {
		load,
		skeletonClass = 'h-24',
		children
	}: { load: () => Promise<T>; skeletonClass?: string; children: Snippet<[T]> } = $props();

	let status: 'loading' | 'ok' | 'error' = $state('loading');
	let value: T | undefined = $state();
	let err = $state('');
	let seq = 0;

	async function run() {
		const my = ++seq;
		status = 'loading';
		try {
			const v = await load();
			if (my !== seq) return;
			value = v;
			status = 'ok';
		} catch (e) {
			if (my !== seq) return;
			err = (e as Error).message ?? '';
			status = 'error';
		}
	}

	$effect(() => {
		run();
	});
</script>

{#if status === 'loading'}
	<Skeleton kind="chart" class={skeletonClass} />
{:else if status === 'error'}
	<ErrorState compact detail={err} onRetry={run} />
{:else}
	{@render children(value as T)}
{/if}

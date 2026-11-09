<script lang="ts">
	// E-17 — 오프라인 전환 시 상단 안내 배너, 복구되면 3초간 "다시 연결됐어요". 낭독은 공지 단일 경로(say).
	import { onMount } from 'svelte';
	import { say } from '$lib/a11y/say';
	import { connectivityText, watchConnectivity, type ConnectivityPhase } from '$lib/connectivity';

	let phase = $state<ConnectivityPhase>('online');
	const text = $derived(connectivityText(phase));

	onMount(() => watchConnectivity(window, () => navigator.onLine, (p) => (phase = p)));
</script>

{#if text}
		<p
			data-testid="offline-banner"
			use:say={{ text }}
			class="border-b border-border-subtle px-4 py-2 text-center text-xs {phase === 'offline' ? 'bg-surface-3 text-semantic-amber' : 'bg-surface-2 text-fg-secondary'}"
		>
			{text}
		</p>
{/if}

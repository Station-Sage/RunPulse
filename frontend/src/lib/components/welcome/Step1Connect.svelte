<script lang="ts">
	// 1/4 기기 연결 — Garmin은 연결 시트(이 화면 안), Strava는 OAuth(return_to), 키 방식은 소스 상세로.
	import { base } from '$app/paths';
	import { onMount } from 'svelte';
	import { connectSource, getSyncState } from '$lib/api/data';
	import GarminConnectSheet from '../data/GarminConnectSheet.svelte';

	let { onConnectedChange }: { onConnectedChange: (count: number) => void } = $props();
	let connected = $state<string[]>([]);
	let error = $state<string | null>(null);
	let failures = $state(0);
	let garminOpen = $state(false);

	async function refresh() {
		try {
			const s = await getSyncState();
			connected = s.sources.filter((x) => x.connection === 'connected').map((x) => x.provider);
			failures = 0;
			onConnectedChange(connected.length);
		} catch {
			failures += 1;
		}
	}
	onMount(() => {
		void refresh();
		window.addEventListener('focus', refresh);
		return () => window.removeEventListener('focus', refresh);
	});

	async function strava() {
		error = null;
		try {
			const r = await connectSource('strava', { return_to: `${base}/welcome?step=2` });
			if (r.redirect_url) window.location.href = r.redirect_url;
		} catch {
			error = 'Strava 연결을 시작하지 못했어요. 다시 시도해 주세요.';
		}
	}
	const rows = [
		{ id: 'intervals', label: 'Intervals.icu', href: `${base}/data/sources/intervals`, note: 'API 키 입력' },
		{ id: 'runalyze', label: 'Runalyze', href: `${base}/data/sources/runalyze`, note: 'API 키 입력' }
	];
</script>

<div class="flex flex-col gap-3">
	<h2 class="text-base font-semibold text-fg-primary">1/4 · 기기 연결</h2>
	<ul class="flex flex-col gap-2">
		<li class="flex flex-col gap-2 rounded-lg border border-border-subtle bg-surface-2 p-3 text-sm">
			<div class="flex items-center justify-between">
				<span>Garmin <span class="text-xs text-fg-muted">{connected.includes('garmin') ? '연결됨' : '이메일·비밀번호 로그인'}</span></span>
				{#if !connected.includes('garmin') && !garminOpen}<button type="button" class="inline-flex min-h-11 items-center text-xs underline" onclick={() => (garminOpen = true)}>연결</button>{/if}
			</div>
			{#if garminOpen}<GarminConnectSheet onConnected={refresh} onClose={() => (garminOpen = false)} />{/if}
		</li>
		{#each rows as r (r.id)}
			<li class="flex items-center justify-between rounded-lg border border-border-subtle bg-surface-2 p-3 text-sm">
				<span>{r.label} <span class="text-xs text-fg-muted">{connected.includes(r.id) ? '연결됨' : r.note}</span></span>
				{#if !connected.includes(r.id)}<a class="inline-flex min-h-11 items-center text-xs underline" href={r.href}>연결 ↗</a>{/if}
			</li>
		{/each}
		<li class="flex items-center justify-between rounded-lg border border-border-subtle bg-surface-2 p-3 text-sm">
			<span>Strava <span class="text-xs text-fg-muted">{connected.includes('strava') ? '연결됨' : 'OAuth'}</span></span>
			{#if !connected.includes('strava')}<button type="button" class="inline-flex min-h-11 items-center text-xs underline" onclick={strava}>연결</button>{/if}
		</li>
	</ul>
	{#if error}<p class="text-xs text-semantic-red">{error}</p>{/if}
	{#if failures >= 3}<p class="text-xs text-fg-muted">연결 상태를 확인하지 못하고 있어요. 건너뛰고 둘러볼 수 있어요.</p>{/if}
</div>

<script lang="ts">
	// 소스 연결·재연결·연결 테스트·해제 — 키 입력(Intervals·Runalyze), Strava는 OAuth 이동, Garmin은 안내만.
	import { onMount } from 'svelte';
	import { base } from '$app/paths';
	import { goto, invalidateAll } from '$app/navigation';
	import { page } from '$app/state';
	import { ApiError } from '$lib/api/client';
	import { connectSource, disconnectSource, testSource } from '$lib/api/data';
	import { kick, runTrigger } from '$lib/syncStore.svelte';

	let { provider, connected, activityCount }: { provider: string; connected: boolean; activityCount: number } =
		$props();
	let apiKey = $state('');
	let athleteId = $state('');
	let busy = $state(false);
	let msg = $state<{ ok: boolean; text: string } | null>(null);
	let confirming = $state(false);

	// Strava OAuth에서 돌아온 직후: 결과를 알리고, 성공이면 막혔던 동기화를 한 번 다시 시작한다
	onMount(() => {
		const q = page.url.searchParams;
		const ok = q.get('connected') === '1';
		const err = q.get('connect_error') === '1';
		if (!ok && !err) return;
		if (ok) {
			msg = { ok: true, text: '연결됐어요. 동기화를 시작할게요' };
			runTrigger([provider]);
			invalidateAll();
		} else {
			msg = { ok: false, text: '연결하지 못했어요. 다시 시도해 주세요' };
		}
		goto(page.url.pathname, { replaceState: true, noScroll: true, keepFocus: true });
	});

	const needsKey = $derived(provider === 'intervals' || provider === 'runalyze');

	async function run(fn: () => Promise<void>, fail: string) {
		busy = true;
		msg = null;
		try {
			await fn();
		} catch (e) {
			msg = { ok: false, text: e instanceof ApiError && e.message ? e.message : fail };
		}
		busy = false;
	}

	const connect = () =>
		run(async () => {
			const r = await connectSource(provider, {
				api_key: apiKey.trim(),
				...(provider === 'intervals' ? { athlete_id: athleteId.trim() } : {})
			});
			if (r.redirect_url) {
				window.location.href = r.redirect_url;
				return;
			}
			msg = { ok: !!r.ok, text: r.message_ko ?? '' };
			if (r.ok) {
				apiKey = '';
				await Promise.all([kick(), invalidateAll()]);
			}
		}, '연결하지 못했어요. 잠시 후 다시 시도해 주세요');

	const oauth = () =>
		run(async () => {
			const r = await connectSource(provider, { return_to: `${base}/data/sources/${provider}?connected=1` });
			if (r.redirect_url) window.location.href = r.redirect_url;
		}, '연결을 시작하지 못했어요');

	const test = () =>
		run(async () => {
			const r = await testSource(provider);
			msg = { ok: r.ok, text: r.message_ko };
		}, '확인하지 못했어요. 잠시 후 다시 시도해 주세요');

	const disconnect = () =>
		run(async () => {
			await disconnectSource(provider);
			confirming = false;
			await Promise.all([kick(), invalidateAll()]);
		}, '해제하지 못했어요. 잠시 후 다시 시도해 주세요');
</script>

<section aria-label="연결" class="flex flex-col gap-2 rounded-lg border border-border-subtle bg-surface-2 p-3">
	<h2 class="text-sm font-semibold text-fg-primary">{connected ? '연결 관리' : '연결하기'}</h2>

	{#if provider === 'garmin'}
		<p class="text-xs text-fg-secondary">Garmin은 아직 이 화면에서 연결할 수 없어요. 기존 설정 화면에서 연결해 주세요.</p>
		<a class="text-xs underline" href="/connect/garmin">Garmin 연결 화면</a>
	{:else if provider === 'strava'}
		<button type="button" class="rounded-lg bg-fg-primary px-4 py-2 text-sm text-surface-1 disabled:opacity-50" disabled={busy} onclick={oauth}>
			{connected ? 'Strava 재연결' : 'Strava로 연결'}
		</button>
	{:else if needsKey}
		<form class="flex flex-col gap-2" onsubmit={(e) => { e.preventDefault(); connect(); }}>
			{#if provider === 'intervals'}
				<label class="text-xs text-fg-secondary">Athlete ID
					<input class="mt-1 w-full rounded border border-border-subtle bg-surface-1 p-2 text-sm" bind:value={athleteId} autocomplete="off" />
				</label>
			{/if}
			<label class="text-xs text-fg-secondary">{provider === 'runalyze' ? 'API 토큰' : 'API 키'}
				<input type="password" class="mt-1 w-full rounded border border-border-subtle bg-surface-1 p-2 text-sm" bind:value={apiKey} autocomplete="off" />
			</label>
			<button type="submit" class="rounded-lg bg-fg-primary px-4 py-2 text-sm text-surface-1 disabled:opacity-50" disabled={busy || !apiKey.trim()}>
				{connected ? '키 바꾸기' : '연결'}
			</button>
		</form>
	{/if}

	{#if connected}
		<div class="flex gap-3 text-xs">
			<button type="button" class="underline disabled:opacity-50" disabled={busy} onclick={test}>연결 테스트</button>
			{#if provider !== 'garmin'}
				<button type="button" class="underline text-semantic-red" onclick={() => (confirming = true)}>연결 해제…</button>
			{/if}
		</div>
	{/if}

	{#if confirming}
		<div role="alertdialog" aria-label="연결 해제 확인" class="rounded border border-border-subtle bg-surface-1 p-3 text-xs">
			<p class="text-fg-primary">연결을 해제해도 가져온 활동 {activityCount.toLocaleString()}건은 그대로 남아요. 다시 연결하면 이어서 동기화돼요.</p>
			<div class="mt-2 flex gap-3">
				<button type="button" class="rounded bg-semantic-red px-3 py-1.5 text-surface-1 disabled:opacity-50" disabled={busy} onclick={disconnect}>연결 해제</button>
				<button type="button" class="underline" onclick={() => (confirming = false)}>취소</button>
			</div>
		</div>
	{/if}

	{#if msg}<p class="text-xs {msg.ok ? 'text-fg-secondary' : 'text-semantic-red'}" role="status">{msg.text}</p>{/if}
</section>

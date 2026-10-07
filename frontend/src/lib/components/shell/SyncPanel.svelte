<script lang="ts">
	// §2.2 동기화 패널 — 소스 행 + "지금 동기화"(POST /data/sync) + 오류 행 조치 링크.
	// 기간 지정 동기화는 v1 /sync 화면으로 연결한다(D11).
	import { onMount } from 'svelte';
	import { runTrigger, syncStore } from '$lib/syncStore.svelte';
	import {
		skipLine,
		sourceLine,
		syncProviderName,
		triggerButtonView,
		type SyncSource,
		type SyncState
	} from '$lib/syncState';

	let { state: sync, onClose }: { state: SyncState; onClose: () => void } = $props();
	let now = $state(Date.now());

	onMount(() => {
		const t = setInterval(() => (now = Date.now()), 1000);
		return () => clearInterval(t);
	});

	const btn = $derived(
		triggerButtonView(sync, { triggering: syncStore.triggering, cooldownUntil: syncStore.cooldownUntil, now })
	);

	function errorAction(src: SyncSource): { href: string; label: string } | null {
		if (src.state === 'error-auth') return { href: '/settings', label: '다시 연결' };
		if (src.state === 'error-access') return { href: '/settings', label: '설정 확인' };
		return null;
	}
</script>

<div class="flex flex-col gap-3 p-4" role="dialog" aria-label="동기화 상태">
	<div class="flex items-center justify-between">
		<h2 class="text-sm font-medium">동기화</h2>
		<button type="button" onclick={onClose} class="text-xs text-fg-muted hover:text-fg-primary">닫기</button>
	</div>
	<ul class="flex flex-col gap-2">
		{#each sync.sources as src (src.provider)}
			{@const line = sourceLine(src, new Date(now))}
			{@const action = errorAction(src)}
			<li class="flex items-center justify-between gap-2 text-sm">
				<span>{syncProviderName(src.provider)}</span>
				<span class="text-fg-secondary" class:text-red-500={src.state.startsWith('error-')}>
					<span aria-hidden="true">{line.glyph}</span>
					{line.text}
					{#if action}
						<a href={action.href} data-sveltekit-reload class="ml-1 underline">{action.label}</a>
					{/if}
				</span>
			</li>
		{/each}
	</ul>
	{#if sync.caveats.length}
		<p class="text-xs text-fg-muted">일부 소스는 {sync.caveats[0].days}일 이상 새 데이터가 없어요.</p>
	{/if}
	{#if btn.settingsLink}
		<a href="/settings" data-sveltekit-reload class="flex h-11 w-full items-center justify-center rounded-lg bg-surface-3 text-sm text-fg-secondary">
			{btn.label} · 설정에서 연결 →
		</a>
	{:else}
		<button
			type="button"
			disabled={btn.disabled}
			onclick={() => runTrigger()}
			class="h-11 w-full rounded-lg bg-teal-500 text-sm font-medium text-white disabled:bg-surface-3 disabled:text-fg-muted"
		>
			{btn.label}
		</button>
	{/if}
	<div role="status" aria-live="polite" class="flex flex-col gap-1 text-xs">
		{#if syncStore.summary}
			<p class="font-medium text-fg-primary">{syncStore.summary}</p>
		{/if}
		{#if syncStore.notice}
			<p class="text-fg-secondary">{syncStore.notice}</p>
		{/if}
		{#each syncStore.skipped as sk (sk.provider)}
			<p class="text-fg-muted">{skipLine(sk)}</p>
		{/each}
	</div>
	<div class="flex items-center justify-between border-t border-border-subtle pt-3 text-sm">
		<a href="/sync" data-sveltekit-reload class="text-fg-secondary hover:text-fg-primary">기간 지정 ›</a>
		<a href="/settings" data-sveltekit-reload class="text-fg-secondary hover:text-fg-primary">설정에서 관리 →</a>
	</div>
</div>

<script lang="ts">
	// §2.1 헤더 우측 동기화 Pill — 색+모양+문구 3중 표기, 폭 고정(레이아웃 점프 방지).
	// 클릭 시 SyncPanel(모바일 하단 시트 / 데스크톱 360px 팝오버). ?sheet=sync로 딥링크.
	import { onMount } from 'svelte';
	import { closeSheet, openSheet, sheetOpen } from '$lib/sheetHistory';
	import { modal } from '$lib/overlay';
	import { pillView } from '$lib/syncState';
	import { syncStore, loadSyncState, startSyncPolling } from '$lib/syncStore.svelte';
	import SyncPanel from './SyncPanel.svelte';

	const sync = $derived(syncStore.data);
	const urlOpen = $derived(sheetOpen('sync'));

	onMount(() => startSyncPolling());

	$effect(() => {
		syncStore.panelOpen = urlOpen;
	});

	function setOpen(v: boolean) {
		if (v) openSheet('sync');
		else closeSheet('sync');
	}

	const view = $derived(
		syncStore.failed && !sync
			? { tone: 'error', glyph: '▲', text: '상태 확인 실패 · 다시' }
			: pillView(sync)
	);
	const toneClass: Record<string, string> = {
		ok: 'text-teal-500',
		stale: 'text-amber-500',
		error: 'text-red-500',
		running: 'text-fg-secondary',
		empty: 'text-fg-muted'
	};

	function onClick() {
		if (syncStore.failed && !sync) loadSyncState();
		else setOpen(!syncStore.panelOpen);
	}
</script>

<div class="relative ml-auto">
	<button
		type="button"
		onclick={onClick}
		aria-haspopup="dialog"
		aria-expanded={syncStore.panelOpen}
		class="flex max-w-[60vw] items-center gap-1.5 truncate rounded-full border border-border-subtle px-2.5 py-1 text-xs {toneClass[view.tone]}"
	>
		<span aria-hidden="true" class:animate-spin={view.tone === 'running'}>{view.glyph}</span>
		<span class="truncate">{view.text}</span>
	</button>
	{#if syncStore.panelOpen && sync}
		<button class="fixed inset-0 z-40 cursor-default bg-black/30 sm:bg-transparent" aria-label="닫기" tabindex="-1" aria-hidden="true" onclick={() => setOpen(false)}></button>
		<div use:modal={{ onClose: () => setOpen(false) }} role="dialog" aria-modal="true" aria-labelledby="sync-panel-h" class="fixed inset-x-0 bottom-0 z-50 rounded-t-2xl bg-surface-1 pb-[env(safe-area-inset-bottom)] shadow-lg sm:absolute sm:inset-x-auto sm:right-0 sm:bottom-auto sm:top-full sm:mt-2 sm:w-[360px] sm:rounded-xl sm:border sm:border-border-subtle">
			<SyncPanel state={sync} onClose={() => setOpen(false)} />
		</div>
	{/if}
</div>

<script lang="ts">
	// §2.2/§2.3(40-v2-unimplemented/design.md), 40:S0 "과도기 드로어" — 첫 행은 동기화 요약(탭하면
	// ?sheet=sync 패널), 나머지는 v2 화면 바로가기.
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import Icon from '$lib/components/Icon.svelte';
	import DevUserSwitch from '$lib/components/DevUserSwitch.svelte';
	import { base } from '$app/paths';
	import { pillView } from '$lib/syncState';
	import { syncStore } from '$lib/syncStore.svelte';
	import { EXPORT_LABEL, EXPORT_PATH, DATA_LINKS, QUICK_LINKS } from '$lib/menuLinks';

	let { open, onClose }: { open: boolean; onClose: () => void } = $props();

	const summary = $derived(pillView(syncStore.data));

	function openSyncPanel() {
		onClose();
		const u = new URL(page.url);
		u.searchParams.set('sheet', 'sync');
		goto(u, { replaceState: true, noScroll: true });
	}
</script>

{#if open}
	<div class="fixed inset-0 z-50 flex" role="dialog" aria-modal="true" aria-label="메뉴">
		<button class="absolute inset-0 bg-black/40" onclick={onClose} aria-label="닫기"></button>

		<div
			class="relative flex h-full w-72 max-w-[85vw] flex-col overflow-y-auto bg-surface-1 pt-[env(safe-area-inset-top)] shadow-lg"
		>
			<div class="flex items-center justify-between border-b border-border-subtle px-4 py-3">
				<h2 class="font-medium">메뉴</h2>
				<button
					onclick={onClose}
					class="rounded p-1 text-fg-secondary hover:text-fg-primary"
					aria-label="닫기"
				>
					<Icon name="close" class="h-5 w-5" />
				</button>
			</div>

			<div class="border-b border-border-subtle px-2 py-3">
				<button
					type="button"
					onclick={openSyncPanel}
					class="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm text-fg-primary hover:bg-surface-2"
				>
					<span aria-hidden="true">{summary.glyph}</span>
					<span class="truncate">{summary.text}</span>
				</button>
			</div>

			<div class="flex flex-col gap-1 px-2 py-3">
				<p class="px-2 py-1 text-xs text-fg-muted">바로가기</p>
				{#each QUICK_LINKS as link (link.href)}
					<a
						href="{base}{link.href}"
						onclick={onClose}
						class="rounded-lg px-3 py-2 text-sm text-fg-primary hover:bg-surface-2"
					>
						{link.label}
					</a>
				{/each}
			</div>

			<div class="flex flex-col gap-1 border-t border-border-subtle px-2 py-3">
				<p class="px-2 py-1 text-xs text-fg-muted">데이터·설정</p>
				<a
					href="{base}/data"
					onclick={onClose}
					class="rounded-lg px-3 py-2 text-sm text-fg-primary hover:bg-surface-2"
				>
					데이터 (동기화·소스)
				</a>
				<!-- V1-11 (b): v1 CSV 라우트 대신 v2 내보내기(EXP) 화면 -->
				<a
					href="{base}{EXPORT_PATH}"
					onclick={onClose}
					data-testid="menu-export-link"
					class="rounded-lg px-3 py-2 text-sm text-fg-primary hover:bg-surface-2"
				>
					{EXPORT_LABEL}
				</a>
				{#each DATA_LINKS as link (link.href)}
					<a
						href="{base}{link.href}"
						onclick={onClose}
						class="rounded-lg px-3 py-2 text-sm text-fg-primary hover:bg-surface-2"
					>
						{link.label}
					</a>
				{/each}
			</div>

			<div class="mt-auto border-t border-border-subtle px-2 py-3">
				<!-- 개발 전용(V1-8): 서버가 production 이면 /dev/users 가 404 라 렌더되지 않는다 -->
				<DevUserSwitch {onClose} />
			</div>
		</div>
	</div>
{/if}

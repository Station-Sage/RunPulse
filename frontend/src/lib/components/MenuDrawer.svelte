<script lang="ts">
	import IconButton from '$lib/components/ui/IconButton.svelte';
	// 첫 행은 동기화 요약(탭하면 ?sheet=sync 패널). 그 아래는 v1 일몰 후 정보 구조(MENUDRAWER-POST-V1, S4-90):
	// 데이터(주 탭 없는 영역) · 설정 · 바로가기 그룹 — 그룹·링크는 $lib/menuLinks. 맨 아래 개발용 사용자 전환·로그아웃.
	import Icon from '$lib/components/Icon.svelte';
	import DevUserSwitch from '$lib/components/DevUserSwitch.svelte';
	import { base } from '$app/paths';
	import { demoActive } from '$lib/demoMode';
	import { modal } from '$lib/overlay';
	import { openSheet } from '$lib/sheetHistory';
	import { pillView } from '$lib/syncState';
	import { syncStore } from '$lib/syncStore.svelte';
	import { MENU_GROUPS } from '$lib/menuLinks';

	let { open, onClose }: { open: boolean; onClose: () => void } = $props();

	const summary = $derived(pillView(syncStore.data));

	function openSyncPanel() {
		onClose();
		openSheet('sync');
	}
</script>

{#if open}
	<div
		class="fixed inset-0 z-50 flex"
		role="dialog"
		aria-modal="true"
		aria-labelledby="menu-drawer-h"
		use:modal={{ onClose }}
	>
		<button
			class="absolute inset-0 bg-scrim"
			onclick={onClose}
			tabindex="-1"
			aria-hidden="true"
			aria-label="닫기"
		></button>

		<div
			class="relative flex h-full w-72 max-w-[85vw] flex-col overflow-y-auto bg-surface-1 pt-[env(safe-area-inset-top)] shadow-lg"
		>
			<div class="flex items-center justify-between border-b border-border-subtle px-4 py-3">
				<h2 id="menu-drawer-h" class="font-medium">메뉴</h2>
				<IconButton label="닫기" onclick={onClose} class="rounded text-fg-secondary hover:text-fg-primary"><Icon name="close" class="h-5 w-5" /></IconButton>
			</div>

			<div class="border-b border-border-subtle px-2 py-3">
				<button
					type="button"
					onclick={openSyncPanel}
					class="flex w-full items-center gap-2 min-h-11 rounded-lg px-3 py-2 text-left text-sm text-fg-primary hover:bg-surface-2"
				>
					<span aria-hidden="true">{summary.glyph}</span>
					<span class="truncate">{summary.text}</span>
				</button>
			</div>

			{#each MENU_GROUPS as group, i (group.id)}
				<div class="flex flex-col gap-1 px-2 py-3 {i > 0 ? 'border-t border-border-subtle' : ''}" role="group" aria-labelledby="menu-group-{group.id}">
					<p id="menu-group-{group.id}" class="px-2 py-1 text-xs text-fg-muted">{group.title}</p>
					{#each group.links as link (link.href)}
						<a
							href="{base}{link.href}"
							onclick={onClose}
							data-testid={link.testid}
							class="min-h-11 rounded-lg px-3 py-2 text-sm text-fg-primary hover:bg-surface-2"
						>
							{link.label}
						</a>
					{/each}
				</div>
			{/each}

			<div class="mt-auto border-t border-border-subtle px-2 py-3">
				<!-- 개발 전용(V1-8): 서버가 production 이면 /dev/users 가 404 라 렌더되지 않는다 -->
				<DevUserSwitch {onClose} />
				{#if !$demoActive}
					<form method="POST" action="/auth/logout">
						<button type="submit" data-testid="menu-logout" class="min-h-11 w-full rounded-lg px-3 py-2 text-left text-sm text-fg-secondary hover:bg-surface-2">로그아웃</button>
					</form>
				{/if}
			</div>
		</div>
	</div>
{/if}

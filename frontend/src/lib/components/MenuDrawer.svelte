<script lang="ts">
	// §2.2/§2.3(40-v2-unimplemented/design.md), 40:S0 "과도기 드로어" — 첫 행은 동기화 요약(탭하면
	// ?sheet=sync 패널), 나머지는 v1 화면으로의 상호 링크. v1 경로는 SvelteKit 라우터 밖이라
	// 각 링크에 data-sveltekit-reload로 전체 새로고침을 강제한다.
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import Icon from '$lib/components/Icon.svelte';
	import { pillView } from '$lib/syncState';
	import { syncStore } from '$lib/syncStore.svelte';

	let { open, onClose }: { open: boolean; onClose: () => void } = $props();

	const summary = $derived(pillView(syncStore.data));

	function openSyncPanel() {
		onClose();
		const u = new URL(page.url);
		u.searchParams.set('sheet', 'sync');
		goto(u, { replaceState: true, noScroll: true });
	}

	const quickLinks = [
		{ href: '/dashboard', label: '대시보드' },
		{ href: '/activities', label: '활동 목록' },
		{ href: '/wellness', label: '웰니스' },
		{ href: '/training', label: '훈련 계획' },
		{ href: '/race', label: '레이스' },
		{ href: '/ai-coach', label: 'AI 코치' },
		{ href: '/shoes', label: '신발' }
	];

	const dataLinks = [
		{ href: '/sync', label: '동기화' },
		{ href: '/settings', label: '설정' },
		{ href: '/guide', label: '지표 가이드' },
		{ href: '/activities/export.csv', label: 'CSV 내보내기' }
	];
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
				<p class="px-2 py-1 text-xs text-fg-muted">기존 화면(v1)</p>
				{#each quickLinks as link (link.href)}
					<a
						href={link.href}
						data-sveltekit-reload
						class="rounded-lg px-3 py-2 text-sm text-fg-primary hover:bg-surface-2"
					>
						{link.label}
					</a>
				{/each}
			</div>

			<div class="flex flex-col gap-1 border-t border-border-subtle px-2 py-3">
				<p class="px-2 py-1 text-xs text-fg-muted">데이터·설정</p>
				{#each dataLinks as link (link.href)}
					<a
						href={link.href}
						data-sveltekit-reload
						class="rounded-lg px-3 py-2 text-sm text-fg-primary hover:bg-surface-2"
					>
						{link.label}
					</a>
				{/each}
			</div>

			<div class="mt-auto border-t border-border-subtle px-2 py-3">
				<a
					href="/switch-user"
					data-sveltekit-reload
					class="block rounded-lg px-3 py-2 text-sm text-fg-secondary hover:bg-surface-2"
				>
					계정 전환
				</a>
			</div>
		</div>
	</div>
{/if}

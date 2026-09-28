<script lang="ts">
	// §6.3(40-v2-unimplemented/design.md) — 전역 오류 화면. 셸(헤더·탭) 안에 렌더된다(+layout.svelte에
	// load가 없어 레이아웃은 그대로 유지됨). 404는 가장 가까운 상위 경로로, 그 외는 다시 시도.
	import { page } from '$app/state';
	import { base } from '$app/paths';
	import Icon from '$lib/components/Icon.svelte';

	const is404 = $derived(page.status === 404);

	const parentPath = $derived.by(() => {
		const segments = page.url.pathname.replace(base, '').split('/').filter(Boolean);
		segments.pop();
		return segments.length ? `${base}/${segments.join('/')}` : `${base}/today`;
	});
</script>

<div class="flex flex-col items-center gap-3 px-4 py-16 text-center">
	<Icon name="warning" class="h-8 w-8 text-fg-muted" />
	<h1 class="text-lg font-medium">{is404 ? '찾는 화면이 없어요' : '불러오지 못했어요'}</h1>
	<p class="max-w-xs text-sm text-fg-secondary">
		{is404 ? '주소가 바뀌었거나 삭제된 화면일 수 있어요.' : '잠시 후 다시 시도해 주세요.'}
	</p>
	<div class="mt-2 flex items-center gap-3">
		{#if is404}
			<a
				href={parentPath}
				class="rounded-full bg-surface-3 px-4 py-2 text-sm font-medium text-fg-primary hover:bg-surface-3/70"
			>
				이전 화면으로
			</a>
		{:else}
			<button
				type="button"
				onclick={() => location.reload()}
				class="rounded-full bg-surface-3 px-4 py-2 text-sm font-medium text-fg-primary hover:bg-surface-3/70"
			>
				다시 시도
			</button>
		{/if}
		<a href="{base}/today" class="text-sm text-fg-secondary hover:text-fg-primary">Today로</a>
	</div>
	<p class="mt-4 text-xs text-fg-muted">{page.status}</p>
</div>

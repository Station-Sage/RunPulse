<script lang="ts">
	// §2.2 동기화 패널(읽기 전용 슬라이스) — 소스 4행 + 지금 동기화/Data 이동.
	// '지금 동기화'는 v2 동기화 엔드포인트가 생기기 전까지 v1 /sync 화면으로 연결한다.
	import { sourceLine, syncProviderName, type SyncState } from '$lib/syncState';

	let { state: sync, onClose }: { state: SyncState; onClose: () => void } = $props();
	const now = new Date();
</script>

<div class="flex flex-col gap-3 p-4" role="dialog" aria-label="동기화 상태">
	<div class="flex items-center justify-between">
		<h2 class="text-sm font-medium">동기화</h2>
		<button type="button" onclick={onClose} class="text-xs text-fg-muted hover:text-fg-primary">닫기</button>
	</div>
	<ul class="flex flex-col gap-2">
		{#each sync.sources as src (src.provider)}
			{@const line = sourceLine(src, now)}
			<li class="flex items-center justify-between gap-2 text-sm">
				<span>{syncProviderName(src.provider)}</span>
				<span class="text-fg-secondary" class:text-red-500={src.state.startsWith('error-')}>
					<span aria-hidden="true">{line.glyph}</span>
					{line.text}
				</span>
			</li>
		{/each}
	</ul>
	{#if sync.caveats.length}
		<p class="text-xs text-fg-muted">일부 소스는 {sync.caveats[0].days}일 이상 새 데이터가 없어요.</p>
	{/if}
	<div class="flex items-center justify-between border-t border-border-subtle pt-3 text-sm">
		<a href="/sync" data-sveltekit-reload class="rounded-lg bg-surface-3 px-3 py-1.5 text-fg-primary">지금 동기화</a>
		<a href="/settings" data-sveltekit-reload class="text-fg-secondary hover:text-fg-primary">설정에서 관리 →</a>
	</div>
</div>

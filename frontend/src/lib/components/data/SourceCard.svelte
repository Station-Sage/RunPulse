<script lang="ts">
	// 소스 카드 — 연결·상태(글리프+문구)·활동 수. 탭하면 소스 상세로.
	import { base } from '$app/paths';
	import { sourceLine, syncProviderName, type SyncSource } from '$lib/syncState';

	let { source, activityCount }: { source: SyncSource; activityCount: number } = $props();
	const line = $derived(sourceLine(source));
</script>

<a
	href="{base}/data/sources/{source.provider}"
	class="block rounded-lg border border-border-subtle bg-surface-2 p-3 hover:bg-surface-3"
>
	<div class="flex items-center justify-between">
		<span class="text-sm font-medium text-fg-primary">{syncProviderName(source.provider)}</span>
		<span class="text-xs text-fg-muted tabular-nums">
			{source.connection === 'connected' ? `${activityCount.toLocaleString()}건` : '연결'}
		</span>
	</div>
	<div class="mt-1 text-xs {source.state.startsWith('error-') ? 'text-semantic-red' : 'text-fg-secondary'}">
		<span aria-hidden="true">{line.glyph}</span>
		{line.text}
	</div>
</a>

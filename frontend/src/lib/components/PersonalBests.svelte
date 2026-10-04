<script lang="ts">
	// 개인 최고 기록 — 대회 기록과 활동 안 구간 기록 중 빠른 쪽, 출처 표시. 눌러서 해당 활동으로.
	import type { ArchivePb } from '$lib/types';
	import { formatDuration } from '$lib/format';
	import { base } from '$app/paths';

	let { pbs }: { pbs: ArchivePb[] } = $props();
</script>

{#if pbs.length > 0}
	<section class="flex flex-col gap-2" aria-label="개인 최고 기록">
		<p class="text-xs uppercase tracking-wide text-fg-muted">개인 최고 기록</p>
		<div class="grid grid-cols-3 gap-2">
			{#each pbs as p (p.key)}
				<a
					href="{base}/library/{p.activity_id}?from=pb"
					class="flex flex-col gap-0.5 rounded-lg border border-border-subtle bg-surface-2 px-3 py-2 hover:bg-surface-3"
				>
					<span class="text-[11px] text-fg-muted">{p.label}</span>
					<span class="font-mono text-lg font-bold">{formatDuration(p.time_sec)}</span>
					<span class="text-[10px] text-fg-muted">{p.date}{#if p.source} · {p.source}{/if}</span>
				</a>
			{/each}
		</div>
	</section>
{/if}

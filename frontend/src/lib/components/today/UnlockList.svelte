<script lang="ts">
	// 아직 열리지 않은 지표의 진행도 — 0이나 가짜 기본값 대신 "곧 열려요"를 보인다(DESIGN-P7-REVIEW03 §2.5).
	import { lockedRows, type UnlockMap } from '$lib/unlock';

	let { unlock = null }: { unlock?: UnlockMap | null } = $props();
	const rows = $derived(lockedRows(unlock));
</script>

{#if rows.length > 0}
	<ul class="flex flex-col gap-2" aria-label="아직 열리지 않은 지표">
		{#each rows as r (r.key)}
			<li class="rounded-lg border border-border-subtle bg-surface-2 px-3 py-2">
				<div class="flex items-center justify-between text-xs">
					<span class="text-fg-primary">{r.label}</span>
					<span class="text-fg-muted">곧 열려요</span>
				</div>
				<div class="mt-1.5 h-1 rounded bg-surface-3" role="progressbar" aria-valuenow={r.pct} aria-valuemin="0" aria-valuemax="100">
					<div class="h-1 rounded bg-semantic-blue" style="width: {r.pct}%"></div>
				</div>
				<p class="mt-1 text-[11px] text-fg-muted">{r.hint}</p>
			</li>
		{/each}
	</ul>
{/if}

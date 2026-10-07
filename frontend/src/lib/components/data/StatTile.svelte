<script lang="ts">
	// Data 개요 통계 타일 — 라벨 + 큰 값 + 보조 문구.
	let { label, value, sub }: { label: string; value: string; sub?: string } = $props();
</script>

<div class="rounded-lg border border-border-subtle bg-surface-2 p-3">
	<div class="text-xs text-fg-muted">{label}</div>
	<div class="mt-1 text-xl font-semibold text-fg-primary tabular-nums">{value}</div>
	{#if sub}<div class="mt-0.5 text-xs text-fg-muted">{sub}</div>{/if}
</div>

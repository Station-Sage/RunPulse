<script lang="ts">
	// 허브 ⑤: 레이스 아침 폼(TSB) 시나리오 — 등급은 서버 status만 렌더(design 10-today §3 ⑤).
	import type { RaceProjection } from '$lib/types';
	import { signedTsb } from '$lib/raceHub';
	import { base } from '$app/paths';

	let { proj }: { proj: RaceProjection } = $props();

	const FORM_TONE: Record<string, string> = {
		excellent: 'text-semantic-green',
		good: 'text-semantic-teal',
		neutral: 'text-fg-secondary',
		caution: 'text-semantic-amber',
		poor: 'text-semantic-red'
	};
</script>

<section aria-label="레이스 아침 폼" class="flex flex-col gap-2 rounded-lg border border-border-subtle bg-surface-2 p-4">
	<div class="flex items-center justify-between">
		<span class="text-sm font-semibold">레이스 아침 폼</span>
		<a href="{base}/library/metrics/tsb" class="text-xs text-fg-muted underline-offset-2 hover:underline">TSB 추이 ›</a>
	</div>
	<div class="grid grid-cols-2 gap-3">
		{#each proj.scenarios as sc (sc.key)}
			<div class="flex flex-col gap-0.5">
				<span class="text-[11px] text-fg-muted">{sc.label}</span>
				<span class="font-mono text-2xl font-bold {FORM_TONE[sc.status ?? 'neutral']}">{signedTsb(sc.tsb)}</span>
				<span class="text-[11px] {FORM_TONE[sc.status ?? 'neutral']}">{sc.status_label ?? ''}</span>
			</div>
		{/each}
	</div>
	<p class="text-[10px] leading-tight text-fg-muted">{proj.assumptions} · 현재 폼 {signedTsb(proj.current.tsb)}</p>
</section>

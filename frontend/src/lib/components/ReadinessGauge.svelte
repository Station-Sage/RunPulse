<script lang="ts">
	// UTRS(링) / CIRS(3분할 위험 트랙) / TSB(0 중심 양방향 반원) — 값·등급은 서버(bands.py) 응답 그대로 렌더.
	import { ringFraction, ringDash } from '$lib/scoreRing';
	import { openDrill } from '$lib/drillStack';
	import { bipolarAngle, trackPct, deltaText } from '$lib/todayHero';
	import type { GaugeEntry, SemanticStatus } from '$lib/types';

	let { slug, label, entry, kind }: {
		slug: 'utrs' | 'cirs' | 'tsb';
		label: string;
		entry: GaugeEntry | null;
		kind: 'ring' | 'track' | 'bipolar';
	} = $props();

	const COLORS: Record<SemanticStatus, string> = {
		excellent: '#22c55e', good: '#22c55e', neutral: '#14b8a6', caution: '#f59e0b', poor: '#ef4444'
	};
	const color = $derived(entry?.status ? COLORS[entry.status] ?? '#14b8a6' : '#14b8a6');
	const delta = $derived(deltaText(entry?.delta_1d));

	// 반원: 중심 (50,50) 반지름 40, 각도 180°(왼쪽)~0°(오른쪽)
	function pt(deg: number, r = 40): [number, number] {
		const rad = (deg * Math.PI) / 180;
		return [50 + r * Math.cos(rad), 50 - r * Math.sin(rad)];
	}
	const needle = $derived(entry ? pt(bipolarAngle(entry.value)) : null);
	const zeroTick = [pt(90, 34), pt(90, 46)];
</script>

<button
	type="button"
	disabled={!entry}
	onclick={() => entry && openDrill(slug)}
	aria-label={entry ? `${label} ${entry.value} — 눌러서 계산 근거 보기` : `${label} 데이터 수집 중`}
	class="flex min-h-[132px] flex-col items-center justify-between gap-1 rounded-lg border border-border-subtle bg-surface-2 p-3 text-center enabled:cursor-pointer enabled:hover:bg-surface-3"
>
	<span class="text-xs font-medium">{label}</span>

	{#if !entry}
		<span class="flex flex-1 items-center justify-center text-[11px] leading-snug text-fg-muted">
			수면·HRV 데이터<br />수집 중
		</span>
	{:else if kind === 'ring'}
		<div class="relative">
			<svg viewBox="0 0 64 64" class="h-16 w-16 -rotate-90" aria-hidden="true">
				<circle cx="32" cy="32" r="26" fill="none" stroke-width="6" class="stroke-surface-3" />
				<circle cx="32" cy="32" r="26" fill="none" stroke-width="6" stroke-linecap="round"
					stroke-dasharray={ringDash(ringFraction(entry.value, 0, 100), 26)} style="stroke:{color}" />
			</svg>
			<div class="absolute inset-0 flex items-center justify-center font-mono text-lg font-bold">{Math.round(entry.value)}</div>
		</div>
	{:else if kind === 'track'}
		<div class="flex w-full flex-col items-center gap-1.5 py-2">
			<span class="font-mono text-lg font-bold">{Math.round(entry.value)}</span>
			<div class="relative h-2 w-full overflow-visible rounded-full">
				<div class="absolute inset-0 flex gap-0.5">
					<span class="flex-1 rounded-l-full" style="background:#22c55e66"></span>
					<span class="flex-1" style="background:#f59e0b66"></span>
					<span class="flex-1 rounded-r-full" style="background:#ef444466"></span>
				</div>
				<span class="absolute top-1/2 h-3.5 w-1.5 -translate-x-1/2 -translate-y-1/2 rounded-sm"
					style="left:{trackPct(entry.value)}%;background:{color}"></span>
			</div>
		</div>
	{:else}
		<div class="relative w-full max-w-[110px]">
			<svg viewBox="0 0 100 56" class="w-full" aria-hidden="true">
				<path d="M10 50 A40 40 0 0 1 90 50" fill="none" stroke-width="6" stroke-linecap="round" class="stroke-surface-3" />
				<line x1={zeroTick[0][0]} y1={zeroTick[0][1]} x2={zeroTick[1][0]} y2={zeroTick[1][1]} stroke-width="1.5" class="stroke-fg-muted" />
				{#if needle}
					<circle cx={needle[0]} cy={needle[1]} r="5" fill={color} />
				{/if}
			</svg>
			<span class="absolute inset-x-0 bottom-0 font-mono text-lg font-bold">{Math.round(entry.value)}</span>
		</div>
	{/if}

	{#if entry}
		<span class="text-[11px]" style="color:{color}">{entry.status_label ?? ''}</span>
		<span class="text-[10px] text-fg-muted">{delta ? `어제 대비 ${delta}` : ' '}</span>
	{/if}
</button>

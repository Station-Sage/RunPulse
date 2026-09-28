<script lang="ts">
	// 재사용 가능한 SVG 스파크라인 컴포넌트.
	// null 지점은 선을 끊고 여러 <polyline> 세그먼트로 분할된다.
	// interactive=true면 §C1 ChartScrub를 붙인다(탭/드래그로 값 확인) — 목록처럼 한 화면에
	// 수십 개가 나열되는 곳(예: library/metrics)은 지금은 interactive를 켜지 않는다(성능·터치
	// 혼선 우려, 2026-09-28 사용자 확인 — 그 화면 재구성 때 재검토).
	import ChartScrub from '$lib/components/ChartScrub.svelte';

	let {
		data,
		width = 600,
		height = 48,
		color = 'currentColor',
		invert = false,
		interactive = false,
		dates,
		formatValue = (v: number) => String(Math.round(v * 10) / 10)
	}: {
		data: (number | null)[];
		width?: number;
		height?: number;
		color?: string;
		/** 낮을수록 좋은 값(페이스 초/km 등)은 true — 좋아지는 방향이 위로 그려진다. */
		invert?: boolean;
		/** true면 ChartScrub로 탭/드래그 스크럽을 붙인다(§C1). */
		interactive?: boolean;
		/** 각 데이터 포인트의 날짜 라벨(툴팁용, data와 같은 길이). */
		dates?: string[];
		/** 툴팁에 값을 표시할 때 쓸 포맷터. */
		formatValue?: (v: number) => string;
	} = $props();

	const validData = $derived(data.filter((v): v is number => v != null));
	const isEmpty = $derived(validData.length === 0);
	const n = $derived(data.length);
	const minVal = $derived(isEmpty ? 0 : Math.min(...validData));
	const maxVal = $derived(isEmpty ? 0 : Math.max(...validData));
	const range = $derived(maxVal - minVal);

	function toX(i: number): number {
		return n <= 1 ? 0 : (i / (n - 1)) * width;
	}
	function toY(v: number): number {
		if (range === 0) return height / 2;
		const frac = (v - minVal) / range;
		return invert ? frac * height : height - frac * height;
	}

	// 데이터 → SVG 좌표 계산
	const segments = $derived.by((): string[] => {
		if (isEmpty) return [];
		const segs: string[] = [];
		let current: string[] = [];
		for (let i = 0; i < data.length; i++) {
			const v = data[i];
			if (v == null) {
				if (current.length >= 2) segs.push(current.join(' '));
				current = [];
			} else {
				current.push(`${toX(i).toFixed(2)},${toY(v).toFixed(2)}`);
			}
		}
		if (current.length >= 2) segs.push(current.join(' '));
		return segs;
	});

	function scrubbedValue(index: number | null): number | null {
		if (index == null) return null;
		return data[index] ?? null;
	}
</script>

{#if isEmpty}
	<span class="text-xs text-fg-muted">데이터 없음</span>
{:else}
	{#snippet chart()}
		<svg
			viewBox="0 0 {width} {height}"
			preserveAspectRatio="none"
			style="display:block; width:100%; height:{height}px;"
			aria-hidden="true"
		>
			{#each segments as pts}
				<polyline
					points={pts}
					fill="none"
					stroke={color}
					stroke-width="2"
					stroke-linecap="round"
					stroke-linejoin="round"
					vector-effect="non-scaling-stroke"
				/>
			{/each}
		</svg>
	{/snippet}

	{#if interactive}
		<ChartScrub pointCount={n}>
			{#snippet children(index, pinned)}
				{@const v = scrubbedValue(index)}
				<div class="relative">
					{@render chart()}
					{#if pinned && v != null && index != null}
						<div
							class="pointer-events-none absolute inset-y-0 w-px bg-fg-secondary/60"
							style="left:{(toX(index) / width) * 100}%"
						></div>
						<div
							class="pointer-events-none absolute -top-1 flex -translate-y-full items-center gap-1 rounded border border-border-subtle bg-surface-2 px-1.5 py-0.5 text-[10px] whitespace-nowrap text-fg-primary"
							style="left:{Math.min(85, Math.max(0, (toX(index) / width) * 100))}%"
						>
							{#if dates?.[index]}<span class="text-fg-muted">{dates[index]}</span>{/if}
							<span class="num font-medium">{formatValue(v)}</span>
						</div>
					{/if}
				</div>
			{/snippet}
		</ChartScrub>
	{:else}
		{@render chart()}
	{/if}
{/if}

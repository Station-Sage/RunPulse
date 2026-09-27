<script lang="ts">
	// 재사용 가능한 정적 SVG 스파크라인 컴포넌트.
	// null 지점은 선을 끊고 여러 <polyline> 세그먼트로 분할된다.

	let {
		data,
		width = 600,
		height = 48,
		color = 'currentColor',
		invert = false
	}: {
		data: (number | null)[];
		width?: number;
		height?: number;
		color?: string;
		/** 낮을수록 좋은 값(페이스 초/km 등)은 true — 좋아지는 방향이 위로 그려진다. */
		invert?: boolean;
	} = $props();

	const validData = $derived(data.filter((v): v is number => v != null));
	const isEmpty = $derived(validData.length === 0);

	// 데이터 → SVG 좌표 계산
	const segments = $derived((): string[] => {
		if (isEmpty) return [];

		const minVal = Math.min(...validData);
		const maxVal = Math.max(...validData);
		const range = maxVal - minVal;
		const n = data.length;

		const toX = (i: number): number => (n <= 1 ? 0 : (i / (n - 1)) * width);
		const toY = (v: number): number => {
			if (range === 0) return height / 2;
			const frac = (v - minVal) / range;
			return invert ? frac * height : height - frac * height;
		};

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
</script>

{#if isEmpty}
	<span class="text-xs text-fg-muted">데이터 없음</span>
{:else}
	<svg
		viewBox="0 0 {width} {height}"
		preserveAspectRatio="none"
		style="display:block; width:100%; height:{height}px;"
		aria-hidden="true"
	>
		{#each segments() as pts}
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
{/if}

<script lang="ts">
	// 월 페이지 CTL 스파크라인(탭 → CTL+ATL 2단 확장). 기간 자르기는 호출부(monthSlice), 여기선 그리기만(T-24).
	import Sparkline from '$lib/components/Sparkline.svelte';
	import { formatLoad } from '$lib/format';

	type Pt = { date: string; value: number | null };
	let { ctl, atl, title, loading }: { ctl: Pt[]; atl: Pt[]; title: string; loading: boolean } = $props();

	let dual = $state(false);
	const ctlVals = $derived(ctl.map((p) => p.value));
	const atlVals = $derived(atl.map((p) => p.value));
	const dates = $derived(ctl.map((p) => p.date));
</script>

<div class="rounded-lg border border-border-subtle bg-surface-2 p-3">
	<button class="flex w-full items-center justify-between text-xs text-fg-muted hover:text-fg-secondary" onclick={() => (dual = !dual)}>
		<span>{title}</span>
		<span aria-hidden="true">{dual ? '▲' : '▼'}</span>
	</button>

	{#if loading}
		<p class="mt-2 text-xs text-fg-muted">불러오는 중…</p>
	{:else if ctlVals.length < 2}
		<p class="mt-2 text-xs text-fg-muted">이 기간의 CTL 기록이 없어요 (최근 1년까지 볼 수 있어요)</p>
	{:else if dual}
		<div class="mt-2 flex flex-col gap-3">
			<div>
				<p class="mb-1 text-[10px] text-fg-muted">CTL</p>
				<Sparkline data={ctlVals} height={40} color="var(--color-series-1)" interactive {dates} formatValue={formatLoad} />
			</div>
			<div>
				<p class="mb-1 text-[10px] text-fg-muted">ATL</p>
				<Sparkline data={atlVals} height={40} color="var(--color-semantic-amber)" interactive dates={atl.map((p) => p.date)} formatValue={formatLoad} />
			</div>
		</div>
	{:else}
		<div class="mt-2">
			<Sparkline data={ctlVals} height={40} color="var(--color-series-1)" interactive {dates} formatValue={formatLoad} />
		</div>
	{/if}
</div>

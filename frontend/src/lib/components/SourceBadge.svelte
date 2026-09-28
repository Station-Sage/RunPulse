<script lang="ts">
	// §C6 출처 배지 — 'runpulse_calc'(RunPulse 계산)·'user_input'(직접 입력) 중립 배지.
	// provider(기기·서비스) 배지는 lib/provider.ts의 providerBadgeClass를 그대로 쓴다
	// (색 대비 재검토는 별도 항목 — dataviz 팔레트 검증 필요, IMPL-PROGRESS.md 참조).
	let {
		kind,
		detail
	}: {
		kind: 'calc' | 'user_input';
		/** 예: 'pmc_v2 · 06:10 계산' */
		detail?: string;
	} = $props();

	const label = $derived(kind === 'calc' ? 'RunPulse 계산' : '직접 입력');
</script>

<span
	class="inline-flex items-center rounded border border-fg-muted/40 px-1.5 py-0.5 text-[10px] text-fg-secondary"
	title={detail}
>
	{label}
</span>

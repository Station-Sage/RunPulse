<script lang="ts">
	// 예측 근거(P7-PRED-74): 심박 기준(자체 vs 기기)과 두 존 체계, 기온 계수, 훈련 반응. 펼칠 때 한 번만 불러온다.
	import { onMount } from 'svelte';
	import type { PredictionProfile, ZoneBounds } from '$lib/types';
	import { getPredictionProfile } from '$lib/api/prediction';

	let profile = $state<PredictionProfile | null>(null);
	let failed = $state(false);

	onMount(() => {
		getPredictionProfile()
			.then((p) => (profile = p))
			.catch(() => (failed = true));
	});

	function zoneText(z: ZoneBounds | null | undefined): string {
		if (!z) return '—';
		return z.map(([lo, hi], i) => `Z${i + 1} ${Math.round(lo)}–${Math.round(hi)}`).join(' · ');
	}
</script>

<div class="flex flex-col gap-2" aria-label="예측 근거">
	<span class="text-xs text-fg-muted">예측 근거</span>
	{#if failed}
		<p class="text-[11px] text-fg-muted">근거를 불러오지 못했어요</p>
	{:else if !profile}
		<p class="text-[11px] text-fg-muted">불러오는 중…</p>
	{:else}
		{@const hp = profile.hr_profile}
		{#if hp}
			<div class="grid grid-cols-2 gap-2 text-[11px]">
				<div class="flex flex-col">
					<span class="text-fg-muted">자체 추정</span>
					<span class="font-mono">최대 {hp.self.hrmax ?? '—'} · LTHR {Math.round(hp.self.lthr)}</span>
					<span class="text-fg-muted">{hp.self.lthr_source === 'races' ? '최근 대회 심박 기준' : '최대심박의 91.7%'}</span>
				</div>
				<div class="flex flex-col">
					<span class="text-fg-muted">기기 제공{hp.ref ? ` (${hp.ref.source})` : ''}</span>
					<span class="font-mono">{hp.ref ? `최대 ${hp.ref.hrmax ?? '—'} · LTHR ${hp.ref.lthr ?? '—'}` : '없음'}</span>
				</div>
			</div>
			<p class="text-[11px] text-fg-muted">LTHR 존(자체) · {zoneText(hp.zones.self.lthr)}</p>
			<p class="text-[11px] text-fg-muted">HRR 존(자체) · {zoneText(hp.zones.self.hrr)}</p>
			{#if hp.zones.ref}
				<p class="text-[11px] text-fg-muted">LTHR 존(기기) · {zoneText(hp.zones.ref.lthr)}</p>
			{/if}
		{:else}
			<p class="text-[11px] text-fg-muted">심박 프로필 데이터 수집 중</p>
		{/if}
		{#if profile.heat_model}
			<p class="text-[11px] text-fg-muted">
				기온 영향 · 15℃보다 1℃ 더우면 {Math.abs(profile.heat_model.heat).toFixed(2)}%, 5℃보다 1℃ 추우면 {Math.abs(profile.heat_model.cold).toFixed(2)}% 느려짐
			</p>
		{/if}
		{#if profile.training_response}
			{@const tr = profile.training_response}
			<p class="text-[11px] text-fg-muted">
				품질 세트 · 최근 8주 주평균 {tr.quality_min_avg_8w}분 · 주 {tr.quality_sessions_avg_8w}회{tr.quality_min_avg_prev_8w != null ? ` (이전 8주 ${tr.quality_min_avg_prev_8w}분)` : ''}{tr.long_mp_km_8w != null ? ` · 롱런 속 마라톤 페이스 ${tr.long_mp_km_8w}km` : ''}
			</p>
		{/if}
	{/if}
</div>

<script lang="ts">
	// 03c-library.md 3-C "환경 컨텍스트" — 활동 시점 날씨(metric_store weather 카테고리, 활동 스코프).
	// AQI·체감 WBGT는 저장된 데이터가 없어 표시하지 않는다(지어내지 않음).
	import { providerLabel, providerBadgeClass } from '$lib/provider';
	import type { ActivityMetric, ProviderKey } from '$lib/types';
	let { metrics }: { metrics: ActivityMetric[] } = $props();
	const FIELDS = [
		{ name: 'weather_temp_c', label: '기온', unit: '°C' },
		{ name: 'avg_temperature', label: '기온(기기)', unit: '°C' },
		{ name: 'weather_humidity_pct', label: '습도', unit: '%' },
		{ name: 'weather_wind_speed_ms', label: '풍속', unit: 'm/s' },
		{ name: 'weather_dew_point_c', label: '이슬점', unit: '°C' },
		{ name: 'weather_pressure_hpa', label: '기압', unit: 'hPa' },
		{ name: 'weather_condition', label: '날씨', unit: '' }
	];
	function display(m: ActivityMetric): string | null {
		if (m.numeric_value != null) {
			return Number.isInteger(m.numeric_value) ? String(m.numeric_value) : m.numeric_value.toFixed(1);
		}
		return m.text_value || null;
	}
	// 기기 온도는 API 날씨 기온이 없을 때만 보조로 쓴다.
	const hasApiTemp = $derived(
		metrics.some((m) => m.metric_name === 'weather_temp_c' && display(m) != null)
	);
	const cells = $derived(
		FIELDS.filter((f) => !(f.name === 'avg_temperature' && hasApiTemp))
			.map((f) => {
				const m = metrics.find((x) => x.metric_name === f.name);
				return { f, m, v: m ? display(m) : null };
			})
			.filter((c) => c.v != null)
	);
	const provider = $derived((cells[0]?.m?.provider ?? null) as ProviderKey | null);
</script>
{#if cells.length > 0}
	<section class="flex flex-col gap-2 rounded-lg border border-border-subtle bg-surface-2 px-4 py-3">
		<div class="flex items-center justify-between">
			<p class="text-xs uppercase tracking-wide text-fg-muted">환경 컨텍스트</p>
			<span class="rounded px-1.5 py-0.5 text-[10px] text-white {providerBadgeClass(provider)}">{providerLabel(provider)}</span>
		</div>
		<div class="grid grid-cols-3 gap-x-3 gap-y-2">
			{#each cells as c (c.f.name)}
				<div class="flex flex-col">
					<span class="text-[10px] text-fg-muted">{c.f.label}</span>
					<span class="font-mono text-sm font-medium">{c.v}{#if c.f.unit}<span class="ml-0.5 text-xs font-normal text-fg-secondary">{c.f.unit}</span>{/if}</span>
				</div>
			{/each}
		</div>
	</section>
{/if}

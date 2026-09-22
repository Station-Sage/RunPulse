import type { ProviderKey } from '$lib/types';

// MetricCell(C2) 배지 규칙(04-component-catalog.md): 'runpulse:formula_v1' → "RunPulse · formula_v1".
// 최근 활동 목록의 소스 배지도 같은 규칙을 쓴다(Provider 표기 통일).
export function providerLabel(p: ProviderKey | null | undefined): string {
	if (!p) return '—';
	if (p.startsWith('runpulse:')) return `RunPulse · ${p.slice('runpulse:'.length)}`;
	const names: Record<string, string> = {
		garmin: 'Garmin',
		strava: 'Strava',
		intervals: 'Intervals',
		runalyze: 'Runalyze',
		runpulse: 'RunPulse'
	};
	return names[p] ?? p;
}

export function providerBadgeClass(p: ProviderKey | null | undefined): string {
	const base = p?.split(':')[0] ?? '';
	const map: Record<string, string> = {
		garmin: 'bg-provider-garmin',
		strava: 'bg-provider-strava',
		intervals: 'bg-provider-intervals',
		runalyze: 'bg-provider-runalyze',
		runpulse: 'bg-provider-runpulse'
	};
	return map[base] ?? 'bg-surface-3';
}

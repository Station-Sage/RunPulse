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

// 카드형 배지에서 사용하는 컴팩트 이름 — base provider만(공식 버전 제외).
// 공식 버전(formula_v1 등)은 title(호버/길게 누름)과 MetricBreakdown 패널에만 표시.
export function providerLabelCompact(p: ProviderKey | null | undefined): string {
	if (!p) return '—';
	const base = p.split(':')[0];
	const names: Record<string, string> = {
		garmin: 'Garmin',
		strava: 'Strava',
		intervals: 'Intervals',
		runalyze: 'Runalyze',
		runpulse: 'RunPulse'
	};
	return names[base] ?? base;
}

export function providerBadgeClass(p: ProviderKey | null | undefined): string {
	const base = p?.split(':')[0] ?? '';
	const map: Record<string, string> = {
		garmin: 'bg-provider-garmin text-provider-garmin-on',
		strava: 'bg-provider-strava text-provider-strava-on',
		intervals: 'bg-provider-intervals text-provider-intervals-on',
		runalyze: 'bg-provider-runalyze text-provider-runalyze-on',
		runpulse: 'bg-provider-runpulse text-provider-runpulse-on'
	};
	return map[base] ?? 'bg-surface-3 text-fg-primary';
}

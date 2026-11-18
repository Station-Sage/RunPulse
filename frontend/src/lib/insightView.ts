import type { InsightEvent, InsightSignal } from '$lib/api/insights';

const RANK = { act: 0, watch: 1, info: 2 } as const;
const LABELS: Record<string, string> = { acwr: 'ACWR', crs: 'CRS', checkin_fatigue: '피로', checkin_pain: '통증' };

/** 가장 중요한 사건 1건 — 심각도 우선, 같으면 최신(id 큰 것). */
export function topInsight(events: InsightEvent[]): InsightEvent | null {
	return [...events].sort((a, b) => RANK[a.severity] - RANK[b.severity] || b.id - a.id)[0] ?? null;
}

export function signalChip(s: InsightSignal): string {
	const name = LABELS[s.signal] ?? s.signal;
	return typeof s.value === 'number' ? `${name} ${s.value}` : name;
}

export const SEVERITY_TONE = {
	act: 'border-semantic-red/40 bg-semantic-red/10',
	watch: 'border-semantic-amber/40 bg-semantic-amber/10',
	info: 'border-border-subtle bg-surface-2'
} as const;

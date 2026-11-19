// 마일스톤 전체 이력 — GET /library/milestones (ADR-057).
import { apiFetch } from './client';
import type { MilestoneEntry } from '$lib/types';

export interface MilestoneHistory {
	items: MilestoneEntry[];
	next_before: string | null;
	type_counts: { type: string; count: number }[];
}

export function getMilestoneHistory(opts: { type?: string | null; before?: string | null; limit?: number } = {}): Promise<MilestoneHistory> {
	const p = new URLSearchParams();
	if (opts.type) p.set('type', opts.type);
	if (opts.before) p.set('before', opts.before);
	if (opts.limit != null) p.set('limit', String(opts.limit));
	const qs = p.toString();
	return apiFetch<MilestoneHistory>(`/library/milestones${qs ? `?${qs}` : ''}`);
}

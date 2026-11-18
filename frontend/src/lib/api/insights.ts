import { apiFetch } from './client';

export type InsightSeverity = 'info' | 'watch' | 'act';
export interface InsightSignal {
	signal: string;
	value: number | string | boolean | null;
	as_of?: string | null;
}
export interface InsightEvent {
	id: number;
	kind: string;
	severity: InsightSeverity;
	as_of: string;
	text: string;
	state: 'open' | 'seen' | 'dismissed' | 'resolved';
	signals: InsightSignal[];
	action: { label: string; route: string } | null;
}

export const getInsights = (limit = 20) => apiFetch<{ events: InsightEvent[] }>(`/insights?state=open&limit=${limit}`);
export const dismissInsight = (id: number) => apiFetch<{ id: number }>(`/insights/${id}/dismiss`, { method: 'POST' });
export const seenInsight = (id: number) => apiFetch<{ id: number }>(`/insights/${id}/seen`, { method: 'POST' });

import { apiFetch } from './client';

export interface StoryChip {
	label: string;
	value: number | null;
	drill: { scope_type: string; scope_id: string; metric: string } | null;
}
export interface StoryCompare {
	key: string;
	label: string;
	value: number;
	prev: number;
	delta_pct: number;
}
export interface StoryIntensity {
	status: 'ok' | 'insufficient';
	z12_pct?: number;
	z3_pct?: number;
	z45_pct?: number;
}
export interface StoryData {
	period: { id: string; label: string; start: string; end: string; prev: string; next: string };
	paragraph: string;
	chips: StoryChip[];
	compare: StoryCompare[];
	intensity: StoryIntensity | null;
	key_sessions: { id: number; name: string; date: string; distance_km: number }[];
	risk_peak: { slug: string; value: number; date: string } | null;
	milestones: { id?: number; title?: string; label?: string; achieved_date?: string; date?: string }[];
}

export const getStory = (period: string) =>
	apiFetch<StoryData>(`/library/story/${encodeURIComponent(period)}`);

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
	period: { id: string; label: string; start: string; end: string; prev: string; next: string | null };
	paragraph: string;
	chips: StoryChip[];
	compare: StoryCompare[];
	/** 진행 중인 기간을 같은 일수로 비교했을 때 안내 문구(M-14), 아니면 null. */
	compare_basis?: string | null;
	/** 아직 오지 않은 기간(M-16). */
	is_future?: boolean;
	intensity: StoryIntensity | null;
	key_sessions: { id: number; name: string; date: string; distance_km: number }[];
	risk_peak: { slug: string; value: number; date: string; status?: string | null; status_label?: string | null } | null;
	milestones: { id?: number; title?: string; label?: string; achieved_date?: string; date?: string }[];
}

export const getStory = (period: string) =>
	apiFetch<StoryData>(`/library/story/${encodeURIComponent(period)}`);

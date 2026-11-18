import { apiFetch } from './client';

export interface AdherenceReview {
	week: string;
	week_start: string;
	summary: string;
	points: { text: string; evidence_key: string }[];
	next_focus: string;
}

export const getAdherenceReview = () => apiFetch<{ review: AdherenceReview | null }>('/coach/plan/adherence-review');

const KEY_LABEL: Record<string, string> = { sessions: '세션 이행', volume: '볼륨', quality: '품질 세션', unplanned_runs: '계획 외 러닝' };
export function evidenceLabel(key: string): string {
	const m = /^day:\d{4}-(\d{2})-(\d{2})$/.exec(key);
	if (m) return `${Number(m[1])}/${Number(m[2])} 세션`;
	return KEY_LABEL[key] ?? key;
}

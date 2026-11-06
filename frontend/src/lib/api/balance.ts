// Training Balance Radar API — GET /library/metrics/training-balance.
import { apiFetch } from './client';
import type { TrainingBalance } from '$lib/types/trainingBalance';

export function getTrainingBalance(date?: string | null, compareDays?: number): Promise<TrainingBalance> {
	const p = new URLSearchParams();
	if (date) p.set('date', date);
	if (compareDays != null) p.set('compare_days', String(compareDays));
	const qs = p.toString();
	return apiFetch<TrainingBalance>(`/library/metrics/training-balance${qs ? `?${qs}` : ''}`);
}

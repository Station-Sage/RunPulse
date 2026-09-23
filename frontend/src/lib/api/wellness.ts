import { apiFetch } from './client';
import type { WellnessDetailData, WellnessTrendData } from '$lib/types';

export async function getWellnessDetail(date?: string): Promise<WellnessDetailData> {
	const params = date ? `?date=${encodeURIComponent(date)}` : '';
	return apiFetch<WellnessDetailData>(`/library/wellness${params}`);
}

export async function getWellnessTrend(days = 30): Promise<WellnessTrendData> {
	return apiFetch<WellnessTrendData>(`/library/wellness/trend?days=${days}`);
}

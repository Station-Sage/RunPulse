import { getWellnessDetail, getWellnessTrend } from '$lib/api/wellness';
import { ApiError } from '$lib/api/client';
import type { WellnessDetailData, WellnessTrendData } from '$lib/types';

export interface WellnessPageData {
	detail: WellnessDetailData | null;
	trend: WellnessTrendData | null;
	errorMessage: string | null;
}

export async function load(): Promise<WellnessPageData> {
	const [detailResult, trendResult] = await Promise.allSettled([
		getWellnessDetail(),
		getWellnessTrend(30),
	]);

	const detail =
		detailResult.status === 'fulfilled' ? detailResult.value : null;
	const trend =
		trendResult.status === 'fulfilled' ? trendResult.value : null;

	let errorMessage: string | null = null;
	if (detailResult.status === 'rejected') {
		const e = detailResult.reason;
		errorMessage = e instanceof ApiError ? e.message : '웰니스 데이터를 불러올 수 없습니다.';
	}

	return { detail, trend, errorMessage };
}

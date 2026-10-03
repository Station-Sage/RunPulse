import { getMetricTrend } from '$lib/api/metrics';
import { ApiError } from '$lib/api/client';
import type { MetricTrendData } from '$lib/types';

export interface MetricTrendPageData {
	slug: string;
	trend: MetricTrendData | null;
	period: string;
	date: string | null;
	errorMessage: string | null;
}

export async function load({
	params,
	url
}: {
	params: { slug: string };
	url: URL;
}): Promise<MetricTrendPageData> {
	const period = url.searchParams.get('period') ?? '3m';
	const rawDate = url.searchParams.get('date');
	const date = rawDate && /^\d{4}-\d{2}-\d{2}$/.test(rawDate) ? rawDate : null;
	try {
		const trend = await getMetricTrend(params.slug, period);
		return { slug: params.slug, trend, period, date, errorMessage: null };
	} catch (e) {
		const message = e instanceof ApiError ? e.message : '메트릭 데이터를 불러올 수 없습니다.';
		return { slug: params.slug, trend: null, period, date, errorMessage: message };
	}
}

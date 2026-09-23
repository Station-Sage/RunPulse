import { getMetricTrend } from '$lib/api/metrics';
import { ApiError } from '$lib/api/client';
import type { MetricTrendData } from '$lib/types';

export interface MetricTrendPageData {
	slug: string;
	trend: MetricTrendData | null;
	period: string;
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
	try {
		const trend = await getMetricTrend(params.slug, period);
		return { slug: params.slug, trend, period, errorMessage: null };
	} catch (e) {
		const message = e instanceof ApiError ? e.message : '메트릭 데이터를 불러올 수 없습니다.';
		return { slug: params.slug, trend: null, period, errorMessage: message };
	}
}

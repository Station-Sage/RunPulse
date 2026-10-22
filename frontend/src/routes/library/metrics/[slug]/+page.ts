import { getMetricTrend } from '$lib/api/metrics';
import { getToday } from '$lib/api/today';
import type { UnlockMap } from '$lib/unlock';
import { classifyFailure, type Failure } from '$lib/loadFailure';
import type { MetricTrendData } from '$lib/types';

export interface MetricTrendPageData {
	slug: string;
	trend: MetricTrendData | null;
	period: string;
	date: string | null;
	errorMessage: string | null;
	failure: Failure | null;
	unlock: UnlockMap | null;
}

export async function load({
	params,
	url,
	depends
}: {
	params: { slug: string };
	url: URL;
	depends: (k: string) => void;
}): Promise<MetricTrendPageData> {
	depends(`app:metric:${params.slug}`);
	const period = url.searchParams.get('period') ?? '3m';
	const rawDate = url.searchParams.get('date');
	const date = rawDate && /^\d{4}-\d{2}-\d{2}$/.test(rawDate) ? rawDate : null;
	const unlock = await getToday().then((t) => t.unlock ?? null).catch(() => null);
	try {
		const trend = await getMetricTrend(params.slug, period);
		return { slug: params.slug, trend, period, date, errorMessage: null, failure: null, unlock };
	} catch (e) {
		const failure = classifyFailure(e);
		return { slug: params.slug, trend: null, period, date, errorMessage: failure.detail, failure, unlock };
	}
}

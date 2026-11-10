import { getMetricTrend } from '$lib/api/metrics';
import { getToday } from '$lib/api/today';
import type { UnlockMap } from '$lib/unlock';
import { classifyFailure, type Failure } from '$lib/loadFailure';
import type { MetricTrendData } from '$lib/types';
import { parseDetailParams } from '$lib/metricDetail';

export interface MetricTrendPageData {
	slug: string;
	trend: MetricTrendData | null;
	period: string;
	date: string | null;
	errorMessage: string | null;
	failure: Failure | null;
	unlock: UnlockMap | null;
	/** M-25: 쓸 수 없어 뺀 주소 값 키(period·date). */
	dropped: string[];
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
	const { period, date, dropped } = parseDetailParams(url.searchParams);
	const unlock = await getToday().then((t) => t.unlock ?? null).catch(() => null);
	try {
		const trend = await getMetricTrend(params.slug, period);
		return { slug: params.slug, trend, period, date, errorMessage: null, failure: null, unlock, dropped };
	} catch (e) {
		const failure = classifyFailure(e);
		return { slug: params.slug, trend: null, period, date, errorMessage: failure.detail, failure, unlock, dropped };
	}
}

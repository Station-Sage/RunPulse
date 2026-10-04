import { getMetricsBrowser } from '$lib/api/metrics';
import { ApiError } from '$lib/api/client';
import { normalizeCategory } from '$lib/metricGroups';
import type { MetricBrowserData } from '$lib/types';

export interface MetricsBrowserPageData {
	browser: MetricBrowserData | null;
	errorMessage: string | null;
	initialCategory: string;
	initialQuery: string;
	initialProvider: string;
}

export async function load({ url }: { url: URL }): Promise<MetricsBrowserPageData> {
	const initialCategory = normalizeCategory(url.searchParams.get('category'));
	const initialQuery = url.searchParams.get('q') ?? '';
	const initialProvider = url.searchParams.get('provider') ?? 'all';
	try {
		const browser = await getMetricsBrowser();
		return { browser, errorMessage: null, initialCategory, initialQuery, initialProvider };
	} catch (e) {
		const message = e instanceof ApiError ? e.message : '메트릭 데이터를 불러올 수 없습니다.';
		return { browser: null, errorMessage: message, initialCategory, initialQuery, initialProvider };
	}
}

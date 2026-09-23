// 03c-library.md 3-A — Library 홈. 최근 활동(5건) + 메트릭 카테고리 칩.
import { getActivities } from '$lib/api/library';
import { getMetricsBrowser } from '$lib/api/metrics';
import type { ActivitySummary, MetricBrowserCategory } from '$lib/types';

export interface LibraryHomeData {
	recentActivities: ActivitySummary[];
	categories: MetricBrowserCategory[];
	activitiesError: string | null;
	metricsError: string | null;
}

export async function load(): Promise<LibraryHomeData> {
	const [activitiesRes, metricsRes] = await Promise.allSettled([
		getActivities({ per_page: 5 }),
		getMetricsBrowser()
	]);

	const recentActivities =
		activitiesRes.status === 'fulfilled' ? activitiesRes.value.activities : [];
	const activitiesError =
		activitiesRes.status === 'rejected'
			? (activitiesRes.reason as Error).message ?? '활동을 불러올 수 없습니다.'
			: null;

	const categories =
		metricsRes.status === 'fulfilled' ? metricsRes.value.categories : [];
	const metricsError =
		metricsRes.status === 'rejected'
			? (metricsRes.reason as Error).message ?? '메트릭을 불러올 수 없습니다.'
			: null;

	return { recentActivities, categories, activitiesError, metricsError };
}

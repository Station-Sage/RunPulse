// 03c-library.md 3-A — Library 홈. 최근 활동(5건) + 메트릭 카테고리 칩 + Provider 현황.
import { getActivities } from '$lib/api/library';
import { getMetricsBrowser } from '$lib/api/metrics';
import { getProviderStatus } from '$lib/api/providers';
import type { ActivitySummary, MetricBrowserCategory, ProviderStatusItem } from '$lib/types';

export interface LibraryHomeData {
	recentActivities: ActivitySummary[];
	categories: MetricBrowserCategory[];
	providerStatus: ProviderStatusItem[];
	activitiesError: string | null;
	metricsError: string | null;
	providerStatusError: string | null;
}

export async function load(): Promise<LibraryHomeData> {
	const [activitiesRes, metricsRes, providerRes] = await Promise.allSettled([
		getActivities({ per_page: 5 }),
		getMetricsBrowser(),
		getProviderStatus()
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

	const providerStatus =
		providerRes.status === 'fulfilled' ? providerRes.value.providers : [];
	const providerStatusError =
		providerRes.status === 'rejected'
			? (providerRes.reason as Error).message ?? 'Provider 현황을 불러올 수 없습니다.'
			: null;

	return { recentActivities, categories, providerStatus, activitiesError, metricsError, providerStatusError };
}

// 03c-library.md 3-A — Library 홈. 최근 활동(5건) + 메트릭 카테고리 칩 + 소스 커버리지.
import { getActivities, getArchive } from '$lib/api/library';
import { getMetricsBrowser } from '$lib/api/metrics';
import { getProviderStatus, getProviderCoverage } from '$lib/api/providers';
import { invalidate } from '$app/navigation';
import { swrLoad } from '$lib/loadCache';
import type { ArchiveData, ActivitySummary, MetricBrowserCategory, ProviderCoverage, ProviderStatusItem } from '$lib/types';

export interface LibraryHomeData {
	archive: ArchiveData | null;
	recentActivities: ActivitySummary[];
	categories: MetricBrowserCategory[];
	providerStatus: ProviderStatusItem[];
	coverage: ProviderCoverage | null;
	activitiesError: string | null;
	metricsError: string | null;
	providerStatusError: string | null;
}

async function fetchLibraryHome(): Promise<LibraryHomeData> {
	const [activitiesRes, metricsRes, providerRes, archiveRes, coverageRes] = await Promise.allSettled([
		getActivities({ per_page: 5 }),
		getMetricsBrowser(),
		getProviderStatus(),
		getArchive(),
		getProviderCoverage()
	]);
	const archive = archiveRes.status === 'fulfilled' ? archiveRes.value : null;

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

	const coverage = coverageRes.status === 'fulfilled' ? coverageRes.value : null;

	return { archive, recentActivities, categories, providerStatus, coverage, activitiesError, metricsError, providerStatusError };
}

// 탭 재방문 시 즉시 이전 값을 보여주고 조용히 갱신(02-performance.md P-5) — depends()가 있어야 invalidate가 먹는다.
export async function load({ depends }: { depends: (key: string) => void }): Promise<LibraryHomeData> {
	depends('app:library-home');
	return swrLoad('app:library-home', fetchLibraryHome, invalidate);
}

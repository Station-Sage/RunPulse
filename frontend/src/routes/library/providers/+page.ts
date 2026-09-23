// 03c-library.md 3-G-1 — Provider 정체성 매트릭스 로더.
import { getProviderMatrix } from '$lib/api/providers';
import type { ProviderMatrixData } from '$lib/types';

export interface ProvidersPageData {
	matrix: ProviderMatrixData | null;
	error: string | null;
	periodDays: number;
}

export async function load({ url }: { url: URL }): Promise<ProvidersPageData> {
	const periodDays = Number(url.searchParams.get('period') ?? 28);

	try {
		const res = await getProviderMatrix(periodDays);
		const matrix: ProviderMatrixData = {
			period_days: res.period_days,
			providers: res.providers,
			groups: res.groups,
			discrepancy_count: res.discrepancy_count
		};
		return { matrix, error: null, periodDays };
	} catch (e) {
		return {
			matrix: null,
			error: (e as Error).message ?? 'Provider 매트릭스를 불러올 수 없습니다.',
			periodDays
		};
	}
}

// 03c-library.md 3-G-1 — Provider 정체성 매트릭스 로더.
import { getProviderMatrix } from '$lib/api/providers';
import { ApiError } from '$lib/api/client';
import type { ProviderComparisonData } from '$lib/types';

export interface ProvidersMatrixPageData {
	comparison: ProviderComparisonData | null;
	days: number;
	errorMessage: string | null;
}

export async function load({ url }: { url: URL }): Promise<ProvidersMatrixPageData> {
	const days = Number(url.searchParams.get('days')) || 28;
	try {
		const res = await getProviderMatrix(days);
		return { comparison: res.comparison, days, errorMessage: null };
	} catch (e) {
		const message = e instanceof ApiError ? e.message : 'Provider 매트릭스를 불러올 수 없습니다.';
		return { comparison: null, days, errorMessage: message };
	}
}

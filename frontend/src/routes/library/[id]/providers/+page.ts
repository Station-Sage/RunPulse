import { getProviderComparison } from '$lib/api/providers';
import { ApiError } from '$lib/api/client';
import type { ProviderComparisonData } from '$lib/types';

export interface ProvidersPageData {
	activityId: number;
	comparison: ProviderComparisonData | null;
	errorMessage: string | null;
}

export async function load({ params }: { params: { id: string } }): Promise<ProvidersPageData> {
	const id = parseInt(params.id, 10);
	if (isNaN(id)) {
		return { activityId: NaN, comparison: null, errorMessage: '잘못된 활동 ID입니다.' };
	}
	try {
		const res = await getProviderComparison(id);
		return { activityId: id, comparison: res.comparison, errorMessage: null };
	} catch (e) {
		const message = e instanceof ApiError ? e.message : '소스 비교 데이터를 불러올 수 없습니다.';
		return { activityId: id, comparison: null, errorMessage: message };
	}
}

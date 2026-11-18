import { getProviderComparison } from '$lib/api/providers';
import { normalizeActivityIdParam } from '$lib/utils/validation';
import { BAD_ID_FAILURE } from '$lib/activityDetailView';
import { classifyFailure, type Failure } from '$lib/loadFailure';
import type { ProviderComparisonData } from '$lib/types';
import type { ActivityDetail } from '$lib/types';

export interface ProvidersPageData {
	activityId: number;
	comparison: ProviderComparisonData | null;
	errorMessage: string | null;
	failure: Failure | null;
	per100m: boolean;
}

export async function load({ params, depends, parent }: { params: { id: string }; depends: (k: string) => void; parent: () => Promise<{ activity?: ActivityDetail | null }> }): Promise<ProvidersPageData> {
	depends(`app:activity:${params.id}`);
	const parsed = normalizeActivityIdParam(params.id);
	if (!parsed) {
		return { activityId: NaN, comparison: null, errorMessage: '잘못된 활동 ID입니다.', failure: { ...BAD_ID_FAILURE }, per100m: false };
	}
	const id = parsed.id;
	const per100m = (await parent()).activity?.display?.pace?.unit === '/100m';
	try {
		const res = await getProviderComparison(id);
		return { activityId: id, comparison: res.comparison, errorMessage: null, failure: null, per100m };
	} catch (e) {
		const failure = classifyFailure(e);
		return { activityId: id, comparison: null, errorMessage: failure.detail, failure, per100m };
	}
}

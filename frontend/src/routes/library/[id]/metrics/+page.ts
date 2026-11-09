import type { ActivityMetric } from '$lib/types';
import type { Failure } from '$lib/loadFailure';
import type { ActivityLayoutData } from '../+layout';
import { normalizeActivityIdParam } from '$lib/utils/validation';
import { BAD_ID_FAILURE } from '$lib/activityDetailView';
export interface MetricsTabPageData {
	activityId: number;
	metricsByCategory: Record<string, ActivityMetric[]>;
	errorMessage: string | null;
	failure: Failure | null;
}
// +layout.ts가 이미 가져온 활동 상세를 재사용 — 서브탭 전환마다 650KB 재요청하지 않는다(P-4).
export async function load({
	params,
	parent
}: {
	params: { id: string };
	parent: () => Promise<ActivityLayoutData>;
}): Promise<MetricsTabPageData> {
	const parsed = normalizeActivityIdParam(params.id);
	if (!parsed) {
		return { activityId: NaN, metricsByCategory: {}, errorMessage: '잘못된 활동 ID입니다.', failure: { ...BAD_ID_FAILURE } };
	}
	const id = parsed.id;
	const { activity, errorMessage, failure } = await parent();
	return { activityId: id, metricsByCategory: activity?.metrics_by_category ?? {}, errorMessage, failure };
}

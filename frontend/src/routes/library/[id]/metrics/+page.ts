import type { ActivityMetric } from '$lib/types';
import type { ActivityLayoutData } from '../+layout';
export interface MetricsTabPageData {
	activityId: number;
	metricsByCategory: Record<string, ActivityMetric[]>;
	errorMessage: string | null;
}
// +layout.ts가 이미 가져온 활동 상세를 재사용 — 서브탭 전환마다 650KB 재요청하지 않는다(P-4).
export async function load({
	params,
	parent
}: {
	params: { id: string };
	parent: () => Promise<ActivityLayoutData>;
}): Promise<MetricsTabPageData> {
	const id = parseInt(params.id, 10);
	if (isNaN(id)) {
		return { activityId: NaN, metricsByCategory: {}, errorMessage: '잘못된 활동 ID입니다.' };
	}
	const { activity, errorMessage } = await parent();
	return { activityId: id, metricsByCategory: activity?.metrics_by_category ?? {}, errorMessage };
}

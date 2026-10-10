// 활동 컨텍스트 새 대화 — `?activity={id}`의 근거 카드·추천 질문과 엔진 상태를 로드한다.
import { getActivityContext, getEngine } from '$lib/api/coach';
import { getMetricExplain } from '$lib/api/metrics';
import { metricQuestions, parseMetricPrefill } from '$lib/coachMetricPrefill';
import { formatUnitValue } from '$lib/format';
import type { CoachActivityContext, CoachEngine } from '$lib/types';

export interface CoachNewPageData {
	activityId: number | null;
	activity: CoachActivityContext | null;
	engine: CoachEngine | null;
	metric: { slug: string; date: string; name: string; valueText: string; suggestions: string[] } | null;
}

export async function load({ url }: { url: URL }): Promise<CoachNewPageData> {
	const raw = url.searchParams.get('activity');
	const activityId = raw && /^\d+$/.test(raw) ? Number(raw) : null;
	const [activity, engine] = await Promise.all([
		activityId != null ? getActivityContext(activityId).catch(() => null) : Promise.resolve(null),
		getEngine().catch(() => null)
	]);
	const pre = activityId == null ? parseMetricPrefill(url.searchParams) : null;
	const ex = pre ? await getMetricExplain(pre.slug, 'daily', pre.date).catch(() => null) : null;
	const metric =
		pre && ex
			? (() => {
					const v = ex.value != null ? formatUnitValue(ex.value, ex.unit) : null;
					const valueText = v ? `${v.display}${v.unit ? ' ' + v.unit : ''}` : '값 없음';
					return { ...pre, name: ex.name_ko, valueText, suggestions: metricQuestions(ex.name_ko, valueText, pre.date) };
				})()
			: null;
	return { activityId, activity, engine, metric };
}

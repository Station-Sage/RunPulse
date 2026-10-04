import type { ActivityMetric } from '$lib/types';

export const METRIC_TAB_SECTIONS = [
	{ key: 'load', label: '얼마나 힘들었나', cats: ['load', 'hr', 'volume', 'stress'] },
	{ key: 'efficiency', label: '얼마나 효율적이었나', cats: ['efficiency', 'pace', 'running_dynamics', 'power'] },
	{ key: 'fitness', label: '체력 신호', cats: ['capacity', 'prediction', 'readiness', 'sleep', 'body'] },
	{ key: 'etc', label: '기타', cats: [] as string[] }
] as const;

const DEV_CATEGORY = '_unmapped';

export interface MetricSection {
	key: string;
	label: string;
	items: ActivityMetric[];
	conclusion: string;
}

/** 섹션 머리 결론 한 줄 — 서버 status 개수만 센다(경계값은 서버 소유). */
export function sectionConclusion(items: ActivityMetric[]): string {
	const poor = items.filter((m) => m.status === 'poor').length;
	const caution = items.filter((m) => m.status === 'caution').length;
	const good = items.filter((m) => m.status === 'good' || m.status === 'excellent').length;
	if (poor + caution > 0) return `주의할 지표 ${poor + caution}개 · 양호 ${good}개`;
	if (good > 0) return `대체로 양호 · ${good}개 지표`;
	return `${items.length}개 지표`;
}

/** 카테고리별 메트릭을 4개 섹션으로 재배치. 미매핑은 개발자 모드에서만 포함. */
export function buildMetricSections(
	byCategory: Record<string, ActivityMetric[]>,
	filter: (m: ActivityMetric) => boolean,
	devMode: boolean
): MetricSection[] {
	const mapped = new Set<string>(METRIC_TAB_SECTIONS.flatMap((s) => s.cats));
	return METRIC_TAB_SECTIONS.map((s) => {
		const cats = Object.keys(byCategory).filter((c) =>
			s.key === 'etc' ? !mapped.has(c) && (devMode || c !== DEV_CATEGORY) : (s.cats as readonly string[]).includes(c)
		);
		const items = cats.flatMap((c) => byCategory[c]).filter(filter);
		return { key: s.key, label: s.label, items, conclusion: sectionConclusion(items) };
	}).filter((s) => s.items.length > 0);
}

/** 신뢰도 0.8 미만은 추정 태그 대상. */
export function isEstimate(m: ActivityMetric): boolean {
	return m.confidence != null && m.confidence < 0.8;
}

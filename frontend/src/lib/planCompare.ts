// 프로그램 비교 표 — 행 정의와 "옵션 간 다른 값만 강조" 판정(F-UI-10).
import { formatDuration } from './format.ts';
import type { PlanTemplate } from './types';

export interface CompareRow {
	key: string;
	label: string;
	cells: string[];
	differs: boolean;
}

const RISK_CLASS: Record<string, string> = {
	낮음: 'text-semantic-green',
	중간: 'text-semantic-amber',
	높음: 'text-semantic-red'
};

export function riskClass(risk: string | null): string {
	return (risk && RISK_CLASS[risk]) || 'text-fg-muted';
}

export function isRecommended(t: PlanTemplate): boolean {
	return t.label === '권장';
}

export function buildCompareRows(templates: PlanTemplate[]): CompareRow[] {
	const defs: [string, string, (t: PlanTemplate) => string][] = [
		['weeks', '기간', (t) => `${t.weeks}주`],
		['km', '주간 최대', (t) => (t.weekly_km_target != null ? `${Math.round(t.weekly_km_target)} km` : '—')],
		['ach', '달성 가능성', (t) => (t.achievability_pct != null ? `${Math.round(t.achievability_pct)}%` : '—')],
		['time', '예상 기록', (t) => (t.projected_time_end != null ? formatDuration(t.projected_time_end) : '—')],
		['risk', '위험도', (t) => t.risk_level ?? '—']
	];
	return defs.map(([key, label, fn]) => {
		const cells = templates.map(fn);
		return { key, label, cells, differs: new Set(cells).size > 1 };
	});
}

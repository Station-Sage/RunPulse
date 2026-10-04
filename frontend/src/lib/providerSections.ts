import type { ComparisonRow } from '$lib/types';

export const SECTION_LABELS = {
	record: '기록 값',
	computed: '계산 지표',
	related: '관련 지표 (정의 다름, 비교 안 함)'
} as const;

export type SectionKey = keyof typeof SECTION_LABELS;

const ORDER: SectionKey[] = ['record', 'computed', 'related'];

/** 행을 section(없으면 record)별로 묶는다. 빈 섹션은 제외, 순서는 기록 → 계산 → 관련. */
export function groupBySection(rows: ComparisonRow[]): { key: SectionKey; label: string; rows: ComparisonRow[] }[] {
	return ORDER.map((key) => ({
		key,
		label: SECTION_LABELS[key],
		rows: rows.filter((r) => (r.section ?? 'record') === key)
	})).filter((s) => s.rows.length > 0);
}

/** `측정 차이 N건 · 정의가 달라 비교하지 않는 항목 N개` — 해당 항목이 없으면 그 조각을 생략. */
export function summaryLine(rows: ComparisonRow[]): string {
	const diffs = rows.filter((r) => r.section !== 'related' && r.discrepancy?.detected).length;
	const related = rows.filter((r) => r.section === 'related').length;
	const parts = [diffs > 0 ? `측정 차이 ${diffs}건` : '측정 차이 없음'];
	if (related > 0) parts.push(`정의가 달라 비교하지 않는 항목 ${related}개`);
	return parts.join(' · ');
}

/** 차이 열 표시: 유의하면 `+3.2%`, 아니면 `≈`; 비교 불가는 빈 문자열. */
export function diffText(row: ComparisonRow): { text: string; significant: boolean } {
	const d = row.diff;
	if (!d || row.section === 'related') return { text: '', significant: false };
	if (!d.significant) return { text: '≈', significant: false };
	const sign = d.pct > 0 ? '+' : '';
	return { text: `${sign}${d.pct.toFixed(Math.abs(d.pct) < 10 ? 1 : 0)}%`, significant: true };
}

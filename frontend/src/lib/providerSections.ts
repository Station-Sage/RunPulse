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

const TOTAL_TIME_SLUGS = new Set(['duration_sec', 'elapsed_time_sec']);

/** 총 시간 차이인데 이동 시간은 같은 행 — 측정 차이가 아니라 일시정지 처리 방식 차이(A-11). */
export function isPauseOnlyDiff(row: ComparisonRow, rows: ComparisonRow[]): boolean {
	if (!TOTAL_TIME_SLUGS.has(row.slug) || !row.discrepancy?.detected) return false;
	const moving = rows.find((r) => r.slug === 'moving_time_sec');
	return moving != null && !moving.discrepancy?.detected;
}

/** `측정 차이 N건 · 정의가 달라 비교하지 않는 항목 N개` — 해당 항목이 없으면 그 조각을 생략. 일시정지 차이는 따로 알린다. */
export function summaryLine(rows: ComparisonRow[]): string {
	const pause = rows.some((r) => isPauseOnlyDiff(r, rows));
	const diffs = rows.filter((r) => r.section !== 'related' && r.discrepancy?.detected && !isPauseOnlyDiff(r, rows)).length;
	const related = rows.filter((r) => r.section === 'related').length;
	const parts = [diffs > 0 ? `측정 차이 ${diffs}건` : '측정 차이 없음'];
	if (pause) parts.push('총 시간은 일시정지 처리 방식이 달라요(이동 시간은 거의 같아요)');
	if (related > 0) parts.push(`정의가 달라 비교하지 않는 항목 ${related}개`);
	return parts.join(' · ');
}

/** 차이 열 표시: 유의하면 `+3.2%`, 아니면 `≈`; 값이 하나뿐이면 `—`(A-13 빈칸 통일), 관련 지표는 빈 문자열. */
export function diffText(row: ComparisonRow): { text: string; significant: boolean } {
	const d = row.diff;
	if (row.section === 'related') return { text: '', significant: false };
	if (!d) return { text: '—', significant: false };
	if (!d.significant) return { text: '≈', significant: false };
	const sign = d.pct > 0 ? '+' : '';
	return { text: `${sign}${d.pct.toFixed(Math.abs(d.pct) < 10 ? 1 : 0)}%`, significant: true };
}

/** 한 행의 소스별 값 표기 자릿수를 맞춘다 — `5.3` 옆의 `5`는 `5.0`(A-12). 숫자가 아닌 칸은 그대로. */
export function alignDecimals(texts: string[]): string[] {
	const isNum = (t: string) => /^-?\d+(\.\d+)?$/.test(t);
	const dp = Math.max(0, ...texts.filter(isNum).map((t) => (t.split('.')[1] ?? '').length));
	if (dp === 0) return texts;
	return texts.map((t) => (isNum(t) ? Number(t).toFixed(dp) : t));
}

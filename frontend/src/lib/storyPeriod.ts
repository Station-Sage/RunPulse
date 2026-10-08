/** 기간 id의 단위: 월 `YYYY-MM`, 주 `YYYY-Www`, 블록 `b-…`. */
export const storyScope = (id: string): 'month' | 'week' | 'block' =>
	id.startsWith('b-') ? 'block' : id.includes('-W') ? 'week' : 'month';

/** 기준일이 속한 ISO 주 id. */
export function isoWeekId(iso: string): string {
	const d = new Date(`${iso}T00:00:00Z`);
	d.setUTCDate(d.getUTCDate() + 4 - (d.getUTCDay() || 7));
	const jan1 = Date.UTC(d.getUTCFullYear(), 0, 1);
	const w = Math.ceil(((d.getTime() - jan1) / 86400000 + 1) / 7);
	return `${d.getUTCFullYear()}-W${String(w).padStart(2, '0')}`;
}

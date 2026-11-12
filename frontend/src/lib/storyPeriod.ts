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

/** M-15: 기간 중 가장 높았던 ACWR 한 줄 — 등급이 안전하면 '위험'이라 부르지 않는다. 문구 TXT-1 확정. */
export function riskPeakText(rp: { slug: string; value: number; date: string; status?: string | null; status_label?: string | null }): {
	title: string;
	body: string;
} {
	const risky = rp.status === 'poor' || (rp.status === 'caution' && rp.value > 1);
	const grade = rp.status_label ? ` · ${rp.status_label}` : '';
	return { title: risky ? '부하 위험 신호' : '가장 높았던 부하비', body: `${rp.slug.toUpperCase()} ${rp.value.toFixed(2)}${grade} (${rp.date})` };
}

/** 직전 기간 대비 % — 음수는 U+2212, 0 은 부호 없음. */
export function deltaPctText(pct: number): string {
	if (pct === 0) return '0%';
	return `${pct > 0 ? '+' : '−'}${Math.abs(pct)}%`;
}

/** 기기 기준 이번 달 id 'YYYY-MM'. */
export const thisMonthId = (today: string = new Date().toLocaleDateString('sv-SE')) => today.slice(0, 7);

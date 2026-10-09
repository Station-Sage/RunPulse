// 시트 상단 'REPLAN' 안내 배너의 순수 로직 (ADR-035 A6, DESIGN-PLAN-A6-REPLAN).
export interface PlanAdvisory {
	code: string;
	severity: string;
	text: string;
	link?: { distance_km?: number | null; race_date?: string | null; target_time_sec?: number | null };
}

export const HIDDEN_KEY = 'rp.replanHidden';

export function isoWeekStart(day: string): string {
	const d = new Date(day + 'T00:00:00Z');
	d.setUTCDate(d.getUTCDate() - ((d.getUTCDay() + 6) % 7));
	return d.toISOString().slice(0, 10);
}

export function replanBannerView(
	advisories: PlanAdvisory[] | null,
	hiddenWeek: string | null,
	today: string,
	isPain: boolean
): PlanAdvisory | null {
	if (isPain || !advisories) return null;
	if (hiddenWeek === isoWeekStart(today)) return null;
	return advisories.find((a) => a.code === 'REPLAN') ?? null;
}

export function replanHref(base: string, a: PlanAdvisory): string | null {
	return a.link?.race_date ? `${base}/coach/plan/replan` : null;
}

// 배너가 이미 보였으면 토스트에서 REPLAN 은 건너뛴다.
export function toastAdvisory(advisories: PlanAdvisory[] | undefined, bannerShown: boolean): string | undefined {
	return (advisories ?? []).find((a) => !(bannerShown && a.code === 'REPLAN'))?.text;
}

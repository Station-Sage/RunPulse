// 시트 상단 'REPLAN' 안내 배너의 순수 로직 (ADR-035 A6, DESIGN-PLAN-A6-REPLAN).
export interface PlanAdvisory {
	code: string;
	severity: string;
	text: string;
	link?: { distance_km?: number | null; race_date?: string | null; target_time_sec?: number | null; recent_weekly_km?: number };
}

// K1/K2(POST /coach/plan 의 부작용) 확인 전까지 링크는 끈다.
export const REPLAN_LINK_ENABLED = false;

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
	const l = a.link;
	if (!REPLAN_LINK_ENABLED || !l?.distance_km || !l.race_date) return null;
	const p = new URLSearchParams({ distance_km: String(l.distance_km), race_date: l.race_date });
	if (l.target_time_sec != null) p.set('target_time_sec', String(l.target_time_sec));
	if (l.recent_weekly_km != null) p.set('recent_weekly_km', String(l.recent_weekly_km));
	return `${base}/coach/plan/new?${p}`;
}

// 배너가 이미 보였으면 토스트에서 REPLAN 은 건너뛴다.
export function toastAdvisory(advisories: PlanAdvisory[] | undefined, bannerShown: boolean): string | undefined {
	return (advisories ?? []).find((a) => !(bannerShown && a.code === 'REPLAN'))?.text;
}

export interface PrefillGoal {
	distance_km: number;
	race_date: string;
	target_time_sec: number | null;
}

// 목표 → /coach/plan/new 쿼리 링크
export function planNewHref(base: string, goal: PrefillGoal): string {
	const p = new URLSearchParams({ distance_km: String(goal.distance_km), race_date: goal.race_date });
	if (goal.target_time_sec != null) p.set('target_time_sec', String(goal.target_time_sec));
	return `${base}/coach/plan/new?${p}`;
}

export const PLAN_DISTANCES_KM = [5, 10, 21.097, 42.195];

// 쿼리 → 폼 초기값. distance는 표준 거리에 ±1km 이내일 때만 채택.
export function parsePrefill(search: URLSearchParams): {
	km: number | null; raceDate: string; hh: string; mm: string; ss: string; completion: boolean;
} {
	const raw = Number(search.get('distance_km'));
	const km = PLAN_DISTANCES_KM.find((d) => Math.abs(d - raw) <= 1) ?? null;
	const raceDate = /^\d{4}-\d{2}-\d{2}$/.test(search.get('race_date') ?? '') ? (search.get('race_date') as string) : '';
	const t = Number(search.get('target_time_sec'));
	if (!Number.isFinite(t) || t <= 0) return { km, raceDate, hh: '', mm: '', ss: '', completion: false };
	return { km, raceDate, hh: String(Math.floor(t / 3600)), mm: String(Math.floor((t % 3600) / 60)), ss: String(Math.round(t % 60)), completion: false };
}

// 남은 기간 문구: 28일 이하 → "남은 N주", 아니면 "N주 로드맵"
export function roadmapLabel(daysLeft: number): string {
	const weeks = Math.max(1, Math.ceil(daysLeft / 7));
	return daysLeft <= 28 ? `남은 ${weeks}주 로드맵 만들기` : `${weeks}주 로드맵 만들기`;
}

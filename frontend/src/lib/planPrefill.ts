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

// 목표 생성 선택 입력(최근 주간 km·최장 km) — 기록이 적은 러너의 시작 볼륨 출처(설계 §5.2-1(a)).
export const REPORTED_MAX_KM = { weekly: 300, long: 60 };

// 문자열 → km(0 초과 max 이하, 0.1 단위). 비었거나 범위 밖이면 null.
export function parseKm(raw: string | null | undefined, max: number): number | null {
	if (raw == null || String(raw).trim() === '') return null;
	const v = Number(raw);
	if (!Number.isFinite(v) || v <= 0 || v > max) return null;
	return Math.round(v * 10) / 10;
}

// 쿼리 → 선택 입력. 잘못된 값은 버린다.
export function parseReportedLoad(search: URLSearchParams): { weeklyKm: number | null; longKm: number | null } {
	return {
		weeklyKm: parseKm(search.get('recent_weekly_km'), REPORTED_MAX_KM.weekly),
		longKm: parseKm(search.get('recent_long_km'), REPORTED_MAX_KM.long)
	};
}

// 폼 입력 → 쿼리에 넣을 [키, 값] 목록(유효한 것만).
export function reportedLoadEntries(weekly: string, long: string): [string, string][] {
	const out: [string, string][] = [];
	const w = parseKm(weekly, REPORTED_MAX_KM.weekly);
	const l = parseKm(long, REPORTED_MAX_KM.long);
	if (w != null) out.push(['recent_weekly_km', String(w)]);
	if (l != null) out.push(['recent_long_km', String(l)]);
	return out;
}

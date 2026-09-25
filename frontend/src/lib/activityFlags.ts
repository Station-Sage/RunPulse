export interface FlagInput {
	activity_type: string;
	distance_m: number | null;
	avg_hr: number | null;
	avg_pace_sec_km: number | null;
	route?: unknown[] | null;
}

export interface ActivityFlag {
	key: 'slow_pace' | 'no_hr' | 'no_gps';
	label: string;
	title: string;
}

const OUTDOOR_RUN = new Set(['running', 'trail_running']);
const SLOW_FACTOR = 1.5; // 목록 러닝 페이스 중앙값의 1.5배보다 느리면 의심
const MIN_RUNS_FOR_MEDIAN = 5;
const MIN_SLOW_DISTANCE_M = 3000;

export function medianPace(items: FlagInput[]): number | null {
	const v = items
		.filter((a) => OUTDOOR_RUN.has(a.activity_type) && a.avg_pace_sec_km != null && a.avg_pace_sec_km > 0)
		.map((a) => a.avg_pace_sec_km as number)
		.sort((x, y) => x - y);
	if (v.length < MIN_RUNS_FOR_MEDIAN) return null;
	const mid = Math.floor(v.length / 2);
	return v.length % 2 ? v[mid] : (v[mid - 1] + v[mid]) / 2;
}

// 행마다 최대 1개(우선순위 slow_pace > no_hr > no_gps). 정상이면 null. 트레드밀·실내는 GPS 없음이 정상이라 제외.
export function activityFlag(a: FlagInput, median: number | null): ActivityFlag | null {
	if (!OUTDOOR_RUN.has(a.activity_type)) return null;
	if (
		median != null &&
		a.avg_pace_sec_km != null &&
		(a.distance_m ?? 0) >= MIN_SLOW_DISTANCE_M &&
		a.avg_pace_sec_km > median * SLOW_FACTOR
	) {
		return { key: 'slow_pace', label: '평소보다 많이 느림', title: '걷기·휴식이 포함됐거나 페이스 데이터 오류일 수 있어요. 예측·통계에서는 제외해서 봐야 할 수 있어요.' };
	}
	if (a.avg_hr == null || a.avg_hr <= 0) {
		return { key: 'no_hr', label: '심박 없음', title: '심박 데이터가 없어 강도·부하 계산이 부정확할 수 있어요.' };
	}
	if (!a.route || a.route.length < 2) {
		return { key: 'no_gps', label: '경로 없음', title: '경로(GPS) 데이터가 없어 지도를 그릴 수 없어요.' };
	}
	return null;
}

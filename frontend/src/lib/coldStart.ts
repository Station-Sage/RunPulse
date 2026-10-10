// S2b 소량 데이터 히어로 요약 — DESIGN-P7-REVIEW03 §2.0. 가짜 기본값 없이 실제 최근 활동만 요약한다.
import type { RecentActivity } from './types';
import { formatDistance, formatDuration, formatPace } from './format.ts';

export interface ColdStartSummary {
	headline: string;
	stats: string;
	activityId: number;
}

export function coldStartSummary(acts: RecentActivity[] | null | undefined): ColdStartSummary | null {
	const runs = (acts ?? []).filter((a) => a.distance_m > 0 && a.duration_sec > 0);
	if (runs.length === 0) return null;
	const a = [...runs].sort((x, y) => y.start_time.localeCompare(x.start_time))[0];
	const pace = formatPace(a.duration_sec / (a.distance_m / 1000));
	return {
		headline: runs.length === 1 ? '첫 기록이 들어왔어요' : `기록 ${runs.length}건이 들어왔어요`,
		stats: `${formatDistance(a.distance_m)} · ${pace}/km · ${formatDuration(a.duration_sec)}`,
		activityId: a.id
	};
}

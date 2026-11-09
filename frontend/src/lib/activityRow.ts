// 활동 행 링크·표시 값 — 상세에서 "돌아가기" 목적지를 결정하는 ?from= 쿼리, 종목별 거리·페이스(A-31).
// 테스트: frontend/tests/activityListB2.test.mjs
import { formatPace, paceMmSs } from './format.ts';
import type { ActivityDisplay } from './types/index.ts';

export type ActivityOrigin = 'home' | 'list' | 'today';

export function activityDetailHref(base: string, id: number, from: ActivityOrigin): string {
	return `${base}/library/${id}?from=${from}`;
}

export interface RowFigures {
	/** 오른쪽 큰 숫자 — 거리가 없는 종목(근력·기타)은 null(시간을 대신 크게) */
	distance: { value: string; unit: string } | null;
	/** 둘째 줄 페이스·속도 — 없으면 null */
	pace: string | null;
}

/**
 * 행의 거리·페이스. 서버 display 계약(종목별)이 있으면 따르고, 없으면 기존처럼 km·/km.
 * 거리 자릿수는 D1c(목록 1자리, 상세 2자리)를 유지하되 수영은 상세 히어로처럼 m 로 보인다.
 */
export function rowFigures(act: {
	distance_m?: number | null;
	avg_pace_sec_km?: number | null;
	display?: ActivityDisplay | null;
}): RowFigures {
	const m = act.distance_m;
	const d = act.display;
	if (!d) {
		return {
			distance: m != null ? { value: (m / 1000).toFixed(1), unit: 'km' } : null,
			pace: act.avg_pace_sec_km != null ? formatPace(act.avg_pace_sec_km) : null
		};
	}
	let distance: RowFigures['distance'] = null;
	if (d.show_distance && m != null) {
		distance = d.family === 'swimming' ? { value: String(Math.round(m)), unit: 'm' } : { value: (m / 1000).toFixed(1), unit: 'km' };
	}
	let pace: string | null = null;
	if (d.pace) pace = `${paceMmSs(d.pace.value_sec)}${d.pace.unit}`;
	else if (d.speed_kmh != null) pace = `${d.speed_kmh.toFixed(1)} km/h`;
	return { distance, pace };
}

// 경로 지도 계산(순수) — 서버 series(lat/lon/pace/hr) 기반. 색은 토큰 color-mix 문자열로 반환(hex 금지).
import type { ActivitySeries } from '../types/index.ts';
import {
	projectRoute,
	robustRange,
	type ProjectedRoute,
	type RoutePoint
} from '../routeGeometry.ts';

export interface SeriesRoute {
	route: ProjectedRoute;
	dists: number[]; // route.points와 같은 순서(m)
}

/** GPS 유효점만 모아 투영. 유효점 2개 미만(실내 등)이면 null. */
export function routeFromSeries(s: ActivitySeries | null | undefined, maxSize = 320, pad = 12): SeriesRoute | null {
	if (!s) return null;
	const pts: RoutePoint[] = [];
	const dists: number[] = [];
	for (let i = 0; i < s.dist_m.length; i++) {
		const lat = s.lat?.[i];
		const lng = s.lon?.[i];
		if (lat == null || lng == null || !Number.isFinite(lat) || !Number.isFinite(lng)) continue;
		if (Math.abs(lat) > 90 || Math.abs(lng) > 180 || (lat === 0 && lng === 0)) continue;
		pts.push({ lat, lng, pace: s.pace_sec_km?.[i] ?? null, hr: s.hr?.[i] ?? null });
		dists.push(s.dist_m[i]);
	}
	const route = projectRoute(pts, maxSize, pad);
	return route ? { route, dists } : null;
}

export function valueFraction(v: number | null, range: { lo: number; hi: number } | null): number | null {
	if (v == null || !range) return null;
	return Math.min(1, Math.max(0, (v - range.lo) / (range.hi - range.lo)));
}

/** 5~95퍼센타일 기준 색. 페이스: 빠름=delta-better→느림=delta-worse, 심박: series-3→series-1. 값 없으면 muted. */
export function mixColor(frac: number | null, mode: 'pace' | 'hr'): string {
	if (frac == null) return 'var(--color-fg-muted)';
	const [a, b] = mode === 'pace' ? ['--color-delta-better', '--color-delta-worse'] : ['--color-series-3', '--color-series-1'];
	const p = Math.round(frac * 100);
	return `color-mix(in oklab, var(${b}) ${p}%, var(${a}))`;
}

export function rangesOf(r: SeriesRoute) {
	return {
		pace: robustRange(r.route.points.map((p) => p.pace)),
		hr: robustRange(r.route.points.map((p) => p.hr))
	};
}

/** 정수 km 경계마다 가장 가까운 점의 좌표(마지막 km는 제외하지 않음). */
export function kmMarkers(r: SeriesRoute): { km: number; x: number; y: number }[] {
	const out: { km: number; x: number; y: number }[] = [];
	const total = r.dists[r.dists.length - 1] ?? 0;
	for (let km = 1; km * 1000 <= total; km++) {
		const i = nearestDistIndex(r.dists, km * 1000);
		out.push({ km, x: r.route.points[i].x, y: r.route.points[i].y });
	}
	return out;
}

export function nearestDistIndex(dists: number[], d: number): number {
	let best = 0;
	for (let i = 1; i < dists.length; i++) if (Math.abs(dists[i] - d) < Math.abs(dists[best] - d)) best = i;
	return best;
}

/** 스플릿 seg(1-based, 1km 기준) 구간에 속한 선분 인덱스(i → i-1~i)인지. */
export function inSegment(distM: number, seg: number | null): boolean {
	return seg != null && distM > (seg - 1) * 1000 && distM <= seg * 1000;
}

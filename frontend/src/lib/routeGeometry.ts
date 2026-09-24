// frontend/src/lib/routeGeometry.ts
// 경로 지도 순수 함수 — GPS 유효점 추출·다운샘플·등장방형 투영·색 보간. 테스트: frontend/tests/routeGeometry.test.mjs

export interface StreamLike {
	latitude?: number | null;
	longitude?: number | null;
	speed_ms?: number | null;
	heart_rate?: number | null;
}
export interface RoutePoint { lat: number; lng: number; pace: number | null; hr: number | null }
export interface ProjectedPoint { x: number; y: number; pace: number | null; hr: number | null }
export interface ProjectedRoute { width: number; height: number; points: ProjectedPoint[] }

/** GPS가 유효한 스트림 점만 RoutePoint로. 유효: 유한수, |lat|≤90, |lng|≤180, (0,0) 제외. pace는 speed_ms>0일 때 1000/speed_ms(초/km), 아니면 null. */
export function routePoints(streams: StreamLike[]): RoutePoint[] {
	const out: RoutePoint[] = [];
	for (const s of streams) {
		const lat = s.latitude;
		const lng = s.longitude;
		if (lat == null || lng == null || !Number.isFinite(lat) || !Number.isFinite(lng)) continue;
		if (Math.abs(lat) > 90 || Math.abs(lng) > 180 || (lat === 0 && lng === 0)) continue;
		out.push({
			lat,
			lng,
			pace: s.speed_ms != null && s.speed_ms > 0 ? 1000 / s.speed_ms : null,
			hr: s.heart_rate ?? null
		});
	}
	return out;
}

/** 균등 간격으로 최대 max개로 줄인다(첫·끝 점 항상 포함). items.length ≤ max면 그대로. */
export function downsample<T>(items: T[], max: number): T[] {
	if (items.length <= max || max < 2) return items;
	const out: T[] = [];
	for (let i = 0; i < max; i++) out.push(items[Math.round((i * (items.length - 1)) / (max - 1))]);
	return out;
}

/** 위경도를 등장방형(위도 중앙 cos 보정) 투영해 긴 변이 maxSize−2·pad가 되게 SVG 좌표로. 북쪽이 위(y 반전). 점이 2개 미만이거나 범위가 0이면 null. */
export function projectRoute(points: RoutePoint[], maxSize: number, pad: number): ProjectedRoute | null {
	if (points.length < 2) return null;
	let minLat = Infinity, maxLat = -Infinity, minLng = Infinity, maxLng = -Infinity;
	for (const p of points) {
		if (p.lat < minLat) minLat = p.lat;
		if (p.lat > maxLat) maxLat = p.lat;
		if (p.lng < minLng) minLng = p.lng;
		if (p.lng > maxLng) maxLng = p.lng;
	}
	const k = Math.cos((((minLat + maxLat) / 2) * Math.PI) / 180);
	const spanX = (maxLng - minLng) * k;
	const spanY = maxLat - minLat;
	const span = Math.max(spanX, spanY);
	if (!(span > 0)) return null;
	const scale = (maxSize - 2 * pad) / span;
	return {
		width: spanX * scale + 2 * pad,
		height: spanY * scale + 2 * pad,
		points: points.map((p) => ({
			x: (p.lng - minLng) * k * scale + pad,
			y: (maxLat - p.lat) * scale + pad,
			pace: p.pace,
			hr: p.hr
		}))
	};
}

/** 유효 값의 5~95퍼센타일 범위(이상치 제외). 유효 값 2개 미만이면 null, lo===hi면 hi=lo+1. */
export function robustRange(values: (number | null)[]): { lo: number; hi: number } | null {
	const v = values.filter((x): x is number => x != null && Number.isFinite(x)).sort((a, b) => a - b);
	if (v.length < 2) return null;
	const at = (q: number) => v[Math.min(v.length - 1, Math.max(0, Math.round(q * (v.length - 1))))];
	const lo = at(0.05);
	let hi = at(0.95);
	if (hi === lo) hi = lo + 1;
	return { lo, hi };
}

/** '#rrggbb' 두 색 사이 선형 보간(t는 0~1로 clamp). */
export function lerpColor(a: string, b: string, t: number): string {
	const c = Math.min(1, Math.max(0, t));
	const pa = [1, 3, 5].map((i) => parseInt(a.slice(i, i + 2), 16));
	const pb = [1, 3, 5].map((i) => parseInt(b.slice(i, i + 2), 16));
	return '#' + pa.map((x, i) => Math.round(x + (pb[i] - x) * c).toString(16).padStart(2, '0')).join('');
}

/** 값→색. pace: 빠름(작은 값) 파랑 #3b82f6 → 느림 주황 #f97316. hr: 낮음 청록 #14b8a6 → 높음 빨강 #ef4444. 값 또는 범위가 없으면 회색 #64748b. */
export function segmentColor(value: number | null, range: { lo: number; hi: number } | null, mode: 'pace' | 'hr'): string {
	if (value == null || !range) return '#64748b';
	const t = (value - range.lo) / (range.hi - range.lo);
	return mode === 'pace' ? lerpColor('#3b82f6', '#f97316', t) : lerpColor('#14b8a6', '#ef4444', t);
}

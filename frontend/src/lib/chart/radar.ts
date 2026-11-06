// 레이더 차트 기하(순수) — 각도·반경·clamp·결측 축 점선 구간. BalanceRadar.svelte 가 쓴다. 테스트: tests/radar.test.mjs
export const SCORE_MAX = 150;

export interface Pt {
	x: number;
	y: number;
}

/** i 번째 축 각도(라디안). 0번 축은 12시 방향, 시계 방향. */
export function axisAngle(i: number, n: number): number {
	return -Math.PI / 2 + (2 * Math.PI * i) / n;
}

export function clampScore(score: number): number {
	return Math.min(Math.max(score, 0), SCORE_MAX);
}

/** 점수 → 반경(0~150 → 0~R). */
export function radiusOf(score: number, R: number): number {
	return (clampScore(score) / SCORE_MAX) * R;
}

const r2 = (v: number) => Math.round(v * 100) / 100;

export function polar(i: number, n: number, radius: number, cx = 0, cy = 0): Pt {
	const a = axisAngle(i, n);
	return { x: r2(cx + radius * Math.cos(a)), y: r2(cy + radius * Math.sin(a)) };
}

export function pointFor(i: number, n: number, score: number, R: number, cx = 0, cy = 0): Pt {
	return polar(i, n, radiusOf(score, R), cx, cy);
}

const fmt = (pts: Pt[]) => pts.map((p) => `${p.x},${p.y}`).join(' ');

/** 모든 축이 같은 점수인 기준 링(예: 100) polygon points. */
export function ringPoints(score: number, n: number, R: number, cx = 0, cy = 0): string {
	return fmt(Array.from({ length: n }, (_, i) => pointFor(i, n, score, R, cx, cy)));
}

/** 축별 다른 점수(균형 구간 경계) polygon points. */
export function shapePoints(scores: number[], R: number, cx = 0, cy = 0): string {
	return fmt(scores.map((s, i) => pointFor(i, scores.length, s, R, cx, cy)));
}

export interface RadarShape {
	/** 유효 꼭짓점만으로 만든 채움 polygon points(유효 <3 이면 빈 문자열). */
	fill: string;
	/** 이웃한 유효 축끼리 잇는 실선 구간. */
	solid: [Pt, Pt][];
	/** 결측 축을 사이에 둔 유효 축끼리 잇는 점선 구간(중심으로 꺾지 않는다). */
	dashed: [Pt, Pt][];
	vertices: (Pt | null)[];
}

/** 점수 배열(null=결측) → 채움·실선·점선 구간. */
export function radarShape(scores: (number | null)[], R: number, cx = 0, cy = 0): RadarShape {
	const n = scores.length;
	const vertices = scores.map((s, i) => (s == null ? null : pointFor(i, n, s, R, cx, cy)));
	const valid = vertices.map((v, i) => (v ? i : -1)).filter((i) => i >= 0);
	const solid: [Pt, Pt][] = [];
	const dashed: [Pt, Pt][] = [];
	if (valid.length >= 2) {
		const pairs = valid.length === 2 ? [[valid[0], valid[1]]] : valid.map((v, k) => [v, valid[(k + 1) % valid.length]]);
		for (const [a, b] of pairs) {
			const seg: [Pt, Pt] = [vertices[a] as Pt, vertices[b] as Pt];
			const adjacent = (a + 1) % n === b || (valid.length === 2 && (b + 1) % n === a);
			(adjacent ? solid : dashed).push(seg);
		}
	}
	const fill = valid.length >= 3 ? fmt(valid.map((i) => vertices[i] as Pt)) : '';
	return { fill, solid, dashed, vertices };
}

/** 축 라벨 위치·정렬. pad 만큼 R 바깥. */
export function labelAnchor(i: number, n: number, R: number, pad: number, cx = 0, cy = 0): Pt & { anchor: 'start' | 'middle' | 'end' } {
	const p = polar(i, n, R + pad, cx, cy);
	const dx = p.x - cx;
	const anchor = Math.abs(dx) < 1 ? 'middle' : dx > 0 ? 'start' : 'end';
	return { ...p, anchor };
}

/** 상태 꼭짓점 모양: 과다 ▲(위 삼각형), 부족 ▼(아래 삼각형), 균형은 원(null). */
export function markerPath(p: Pt, status: string | null, size = 5): string | null {
	if (status === 'high') return `M${p.x},${r2(p.y - size)} L${r2(p.x + size)},${r2(p.y + size)} L${r2(p.x - size)},${r2(p.y + size)} Z`;
	if (status === 'low') return `M${p.x},${r2(p.y + size)} L${r2(p.x + size)},${r2(p.y - size)} L${r2(p.x - size)},${r2(p.y - size)} Z`;
	return null;
}

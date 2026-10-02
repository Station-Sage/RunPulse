// 활동 타임라인(3트랙) 순수 계산 — 도메인·경로·x 눈금. 렌더링은 ActivityTimeline.svelte.

export interface Domain {
	min: number;
	max: number;
}

/** 값 배열의 도메인. 유효값이 없으면 null. minSpan보다 좁으면 중앙 기준으로 넓힌다. */
export function trackDomain(values: (number | null)[], minSpan = 0): Domain | null {
	const v = values.filter((x): x is number => x != null && Number.isFinite(x));
	if (v.length === 0) return null;
	let min = Math.min(...v);
	let max = Math.max(...v);
	if (max - min < minSpan) {
		const mid = (min + max) / 2;
		min = mid - minSpan / 2;
		max = mid + minSpan / 2;
	}
	return { min, max };
}

/** 페이스처럼 작을수록 위로 가야 하면 invert. 결과는 0(위)~1(아래). */
export function yFraction(v: number, d: Domain, invert = false): number {
	const span = d.max - d.min || 1;
	const f = (v - d.min) / span;
	return invert ? f : 1 - f;
}

/** null을 만나면 선을 끊는 SVG path. x는 인덱스 분율 × width, y는 yFraction × height. */
export function linePath(
	values: (number | null)[],
	d: Domain,
	width: number,
	height: number,
	invert = false
): string {
	const n = values.length;
	let out = '';
	let pen = false;
	for (let i = 0; i < n; i++) {
		const v = values[i];
		if (v == null || !Number.isFinite(v)) {
			pen = false;
			continue;
		}
		const x = n > 1 ? (i / (n - 1)) * width : 0;
		const y = yFraction(v, d, invert) * height;
		out += `${pen ? 'L' : 'M'}${x.toFixed(1)},${y.toFixed(1)}`;
		pen = true;
	}
	return out;
}

/** x축(거리) 눈금 — ≤10km는 1km, 그 이상은 5km 간격. 단위 m. */
export function distanceTicks(totalM: number): number[] {
	if (!(totalM > 0)) return [];
	const step = totalM <= 10000 ? 1000 : 5000;
	const out: number[] = [];
	for (let m = 0; m <= totalM; m += step) out.push(m);
	return out;
}

/** 고도 변화폭이 10m 미만이면 평지 문구(누적 상승 포함). 아니면 null. */
export function flatNote(alts: (number | null)[], gainM: number | null): string | null {
	const d = trackDomain(alts);
	if (!d || d.max - d.min >= 10) return null;
	return gainM != null ? `거의 평지 · 누적 상승 ${Math.round(gainM)}m` : '거의 평지';
}

export function meanOf(values: (number | null)[]): number | null {
	const v = values.filter((x): x is number => x != null && Number.isFinite(x));
	return v.length ? v.reduce((a, b) => a + b, 0) / v.length : null;
}

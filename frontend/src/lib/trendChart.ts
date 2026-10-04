// frontend/src/lib/trendChart.ts
// 추세 차트 순수 함수 — 공통 y 범위·날짜 x 위치·스크럽 최근접점·변화 라벨. 테스트: frontend/tests/trendChart.test.mjs

export interface TrendPoint {
	date: string;
	value: number;
}

export interface TrendSeries {
	key: string;
	label: string;
	color: string;
	points: TrendPoint[];
}

/** 모든 시리즈를 한 축에 그릴 공통 y 범위(위아래 5% 여백, 데이터가 전부 0 이상이면 아래 여백이 0을 넘지 않음). 값이 하나도 없으면 null. 최댓값=최솟값이면 ±1. */
export function commonRange(series: TrendSeries[]): { min: number; max: number } | null {
	const vals = series.flatMap((s) => s.points.map((p) => p.value));
	if (vals.length === 0) return null;
	let min = Math.min(...vals);
	let max = Math.max(...vals);
	if (min === max) {
		min -= 1;
		max += 1;
	}
	const pad = (max - min) * 0.05;
	const lo = min >= 0 ? Math.max(0, min - pad) : min - pad;
	return { min: lo, max: max + pad };
}

/** 날짜(YYYY-MM-DD)의 [t0, t1] 구간 내 위치 0~1 — 시리즈마다 날짜가 달라도 같은 x축에 놓기 위함. 구간 길이가 0이면 0. */
export function xFraction(date: string, t0: string, t1: string): number {
	const a = Date.parse(t0);
	const b = Date.parse(t1);
	if (!(b > a)) return 0;
	return Math.min(1, Math.max(0, (Date.parse(date) - a) / (b - a)));
}

/** 위치 frac(0~1)에 가장 가까운 날짜의 점. 점이 없으면 null. */
export function nearestPoint(
	points: TrendPoint[],
	frac: number,
	t0: string,
	t1: string
): TrendPoint | null {
	let best: TrendPoint | null = null;
	let bestD = Infinity;
	for (const p of points) {
		const d = Math.abs(xFraction(p.date, t0, t1) - frac);
		if (d < bestD) {
			bestD = d;
			best = p;
		}
	}
	return best;
}

/** "N일 변화" 라벨 — 기준값(N일 전 이하의 마지막 점, 없으면 첫 점)이 작으면(|기준|<10) 퍼센트가 무의미하므로 절대 변화(+33.4)로, 아니면 퍼센트(+13.0%)로. 점이 없으면 '—'. */
export function changeLabel(points: TrendPoint[], days = 30): string {
	if (points.length === 0) return '—';
	const last = points[points.length - 1];
	const cutoff = Date.parse(last.date) - days * 86_400_000;
	let base = points[0];
	for (const p of points) if (Date.parse(p.date) <= cutoff) base = p;
	const delta = last.value - base.value;
	const sign = delta >= 0 ? '+' : '';
	if (Math.abs(base.value) < 10) return `${sign}${delta.toFixed(1)}`;
	return `${sign}${((delta / base.value) * 100).toFixed(1)}%`;
}

/** 7일 이동평균(해당 날짜 포함 직전 7일 창, 창 안 점이 하나라도 있으면 평균). 입력은 날짜 오름차순. */
export function movingAverage(points: TrendPoint[], windowDays = 7): TrendPoint[] {
	const span = (windowDays - 1) * 86_400_000;
	return points.map((p, i) => {
		const t = Date.parse(p.date);
		let sum = 0;
		let n = 0;
		for (let j = i; j >= 0 && t - Date.parse(points[j].date) <= span; j--) {
			sum += points[j].value;
			n++;
		}
		return { date: p.date, value: sum / n };
	});
}

/** 점 사이가 maxGapDays 초과로 벌어지면 선을 끊어 여러 구간으로 나눈다(결측을 이어 그리지 않기 위함). */
export function splitOnGaps(points: TrendPoint[], maxGapDays = 2): TrendPoint[][] {
	const out: TrendPoint[][] = [];
	let cur: TrendPoint[] = [];
	for (const p of points) {
		const prev = cur[cur.length - 1];
		if (prev && Date.parse(p.date) - Date.parse(prev.date) > maxGapDays * 86_400_000) {
			out.push(cur);
			cur = [];
		}
		cur.push(p);
	}
	if (cur.length) out.push(cur);
	return out;
}

/** y 범위를 최소 폭(minSpan) 이상으로 보장 — 값 변동이 작은 스파크라인이 과장돼 보이지 않게 중심 기준으로 넓힌다. */
export function spanRange(min: number, max: number, minSpan: number): { min: number; max: number } {
	if (max - min >= minSpan) return { min, max };
	const mid = (min + max) / 2;
	return { min: mid - minSpan / 2, max: mid + minSpan / 2 };
}

/** 스크린리더용 요약: "UTRS 3개월: 현재 60, 최고 89(8월 8일), 최저 37". 점이 없으면 데이터 없음 문구. */
export function trendAriaLabel(
	name: string,
	periodLabel: string,
	points: TrendPoint[],
	fmt: (v: number) => string = (v) => String(Math.round(v * 10) / 10)
): string {
	if (points.length === 0) return `${name} ${periodLabel}: 데이터 없음`;
	const hi = points.reduce((a, b) => (b.value > a.value ? b : a));
	const lo = points.reduce((a, b) => (b.value < a.value ? b : a));
	const md = (d: string) => `${Number(d.slice(5, 7))}월 ${Number(d.slice(8, 10))}일`;
	const last = points[points.length - 1];
	return `${name} ${periodLabel}: 현재 ${fmt(last.value)}, 최고 ${fmt(hi.value)}(${md(hi.date)}), 최저 ${fmt(lo.value)}(${md(lo.date)})`;
}

/** [t0, t1] 안의 월요일 날짜 목록(YYYY-MM-DD) — 4주 보기의 주 경계 x 눈금용. */
export function weekTicks(t0: string, t1: string): string[] {
	if (!t0 || !t1) return [];
	const out: string[] = [];
	const end = Date.parse(t1);
	const d = new Date(Date.parse(t0));
	while (d.getTime() <= end) {
		if (d.getUTCDay() === 1) out.push(d.toISOString().slice(0, 10));
		d.setUTCDate(d.getUTCDate() + 1);
	}
	return out;
}

/** t0에서 offset일 뒤 날짜(YYYY-MM-DD). 차트 스크럽 인덱스 → 선택일 변환용. */
export function dateAtOffset(t0: string, offset: number): string {
	const d = new Date(Date.parse(t0));
	d.setUTCDate(d.getUTCDate() + offset);
	return d.toISOString().slice(0, 10);
}

/** 선택 기간 전체(첫 점→마지막 점)의 변화. 점이 2개 미만이면 null. pct는 첫 값이 0이면 null. */
export function periodChange(points: TrendPoint[]): { delta: number; pct: number | null } | null {
	if (points.length < 2) return null;
	const first = points[0].value;
	const delta = points[points.length - 1].value - first;
	return { delta, pct: first !== 0 ? (delta / Math.abs(first)) * 100 : null };
}

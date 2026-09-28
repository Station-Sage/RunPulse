// §C1 ChartScrub 코어(ux-review-2026-09/10-today/design.md) — 순수 함수만.
// FormChart·TrendChart·Sparkline·Library 스트림 차트가 공유할 스케일·눈금·최근접점 계산.
// 인터랙션 레이어(포인터·키보드·툴팁)는 ChartScrub.svelte(2-4 다음 단계)가 맡는다.
// 각 차트는 그동안 만들어 둔 자기 x축 변환(날짜 기반 xFrac 등)을 그대로 쓰고, 이 모듈의
// 함수들은 그 결과(0~1 분율 배열)를 받아 눈금·최근접 탐색만 공통화한다 — 기존 3곳(trendChart.ts
// xFraction/nearestPoint, formChart.ts xFrac/nearestByFrac, streamAxis.ts indexAtFraction)을
// 걷어내는 마이그레이션은 각 차트를 하나씩 옮기며 진행(회귀 위험 — 서두르지 않음).

/** "보기 좋은" 눈금 간격 — 1·2·2.5·5 × 10ⁿ 중 하나를 고른다. */
function niceStep(rawStep: number): number {
	if (rawStep <= 0) return 1;
	const exponent = Math.floor(Math.log10(rawStep));
	const base = rawStep / 10 ** exponent;
	let niceBase: number;
	if (base <= 1) niceBase = 1;
	else if (base <= 2) niceBase = 2;
	else if (base <= 2.5) niceBase = 2.5;
	else if (base <= 5) niceBase = 5;
	else niceBase = 10;
	return niceBase * 10 ** exponent;
}

/**
 * y축 nice tick 값 목록(§C1 "1·2·2.5·5×10ⁿ", 3~5개). min===max면 그 값 하나만 반환.
 * 반환값은 min~max 범위를 벗어날 수 있다(호출부가 필요하면 잘라 쓴다) — 패딩 경계값을
 * 라벨로 쓰지 않으려면, 눈금이 실제 렌더 영역 경계에 너무 가까운 경우를 호출부에서 걸러낸다.
 */
export function niceTicks(min: number, max: number, targetCount = 4): number[] {
	if (min === max) return [min];
	if (min > max) [min, max] = [max, min];
	const step = niceStep((max - min) / Math.max(1, targetCount - 1));
	const start = Math.ceil(min / step) * step;
	const ticks: number[] = [];
	for (let v = start; v <= max + step * 1e-9; v += step) {
		// 부동소수 잡음 제거(0.1+0.2 같은) — step 자릿수만큼 반올림
		const decimals = Math.max(0, -Math.floor(Math.log10(step)) + 2);
		ticks.push(Number(v.toFixed(decimals)));
	}
	return ticks;
}

/** 0~1로 자른다. */
export function clamp01(x: number): number {
	return Math.min(1, Math.max(0, x));
}

/**
 * 분율(0~1) 배열에서 target에 가장 가까운 인덱스. 빈 배열이면 -1.
 * 여러 차트가 각자 x축(날짜/샘플 인덱스)을 분율로 바꾼 뒤 이 함수로 탐색을 공유한다.
 */
export function nearestIndexByFraction(fractions: number[], target: number): number {
	let bestIdx = -1;
	let bestDist = Infinity;
	for (let i = 0; i < fractions.length; i++) {
		const d = Math.abs(fractions[i] - target);
		if (d < bestDist) {
			bestDist = d;
			bestIdx = i;
		}
	}
	return bestIdx;
}

const MONTH_KO = (m: number) => `${m}월`;

/**
 * x축 날짜 라벨(§C1) — 기간 길이에 따라 형식을 바꾼다.
 * spanDays ≤14: '9/12' 형식(요일/일, 요일은 호출부가 따로 붙이길 원하면 formatDateShort 사용),
 * ≤180(6개월): 월 경계일 때만 '7월', 그 외 ''(달 경계에서만 라벨을 찍는다는 뜻이라 호출부가
 * "이 점이 그 달의 첫 표시 지점인지"를 판단해 넘겨야 하므로 isMonthBoundary로 표시),
 * >180: '25.10' 분기 라벨.
 */
export function axisDateLabel(
	isoDate: string,
	spanDays: number,
	isMonthBoundary = false
): string {
	const d = new Date(`${isoDate.slice(0, 10)}T00:00:00Z`);
	if (spanDays <= 14) {
		return `${d.getUTCMonth() + 1}/${d.getUTCDate()}`;
	}
	if (spanDays <= 180) {
		return isMonthBoundary ? MONTH_KO(d.getUTCMonth() + 1) : '';
	}
	const yy = String(d.getUTCFullYear()).slice(-2);
	return `${yy}.${String(d.getUTCMonth() + 1).padStart(2, '0')}`;
}

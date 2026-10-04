// frontend/src/lib/streamAxis.ts
// 스트림 화면 시간축 계산 유틸. 순수 함수만 포함 — 테스트: frontend/tests/streamAxis.test.mjs

/**
 * n개 포인트 배열에서 분율 fraction(0~1)에 해당하는 인덱스를 반환한다.
 * fraction=0 → 0, fraction=1 → n-1.
 */
export function indexAtFraction(n: number, fraction: number): number {
	if (n <= 0) return 0;
	const clamped = Math.max(0, Math.min(1, fraction));
	return Math.round(clamped * (n - 1));
}

/**
 * elapsed_sec 배열과 눈금 개수를 받아 x축 눈금 목록을 반환한다.
 * 반환값: { frac: 0~1 위치(CSS left 용), label: "0" | "15m" | "1h 03m" 형식 }[]
 * 위치는 포인트 인덱스 기준 등간격, 라벨은 해당 인덱스의 실제 elapsed_sec.
 */
export function axisTicks(
	elapsed: (number | null)[],
	count: number = 5
): { label: string; frac: number }[] {
	const n = elapsed.length;
	if (n === 0 || count < 2) return [];

	const ticks: { label: string; frac: number }[] = [];
	for (let t = 0; t < count; t++) {
		const frac = t / (count - 1);
		const idx = indexAtFraction(n, frac);
		const sec = elapsed[idx] ?? nearestNonNull(elapsed, idx);
		ticks.push({ frac, label: formatElapsed(sec) });
	}
	return ticks;
}

function nearestNonNull(arr: (number | null)[], start: number): number {
	for (let d = 1; d < arr.length; d++) {
		if (start - d >= 0 && arr[start - d] != null) return arr[start - d]!;
		if (start + d < arr.length && arr[start + d] != null) return arr[start + d]!;
	}
	return 0;
}

/**
 * elapsed_sec 배열과 활동 총 시간(초)을 받아 시간 눈금에 쓸 elapsed 배열을 반환한다.
 * 마지막 non-null elapsed_sec가 totalSec의 90% 미만이면 등간격 샘플로 보고
 * totalSec에 비례해 재환산한다(Garmin downsample 시 elapsed_sec가 샘플 인덱스로
 * 저장되는 경우 대응). 유효한 경우에는 원본 값을 그대로 반환한다.
 * 반환값에 null은 포함되지 않는다(null → 0으로 대체).
 */
export function streamSeconds(elapsed: (number | null)[], totalSec: number): number[] {
	const n = elapsed.length;
	if (n === 0 || totalSec <= 0) return elapsed.map((v) => v ?? 0);
	if (n === 1) return [0];

	// 마지막 non-null elapsed_sec 찾기
	let lastSec = 0;
	for (let i = n - 1; i >= 0; i--) {
		if (elapsed[i] != null) {
			lastSec = elapsed[i]!;
			break;
		}
	}

	if (lastSec >= totalSec * 0.9) {
		// 저장값이 신뢰할 만한 수준 — 그대로 사용
		return elapsed.map((v) => v ?? 0);
	}

	// 등간격 재환산: i번째 샘플 → (i / (n-1)) * totalSec
	return elapsed.map((_, i) => Math.round((i / (n - 1)) * totalSec));
}

/**
 * elapsed_sec 값을 "0" | "15m" | "1h 03m" 형식으로 포맷한다.
 */
export function formatElapsed(sec: number | null | undefined): string {
	if (sec == null) return '—';
	const s = Math.round(sec);
	if (s === 0) return '0';
	const h = Math.floor(s / 3600);
	const m = Math.floor((s % 3600) / 60);
	if (h > 0) return `${h}h ${m.toString().padStart(2, '0')}m`;
	return `${m}m`;
}

/** 거리 기준 x축 눈금 — 포인트 등간격 위치에 해당 포인트의 누적 거리(km) 라벨. */
export function distanceTicks(
	distM: (number | null)[],
	count: number = 5
): { label: string; frac: number }[] {
	const n = distM.length;
	if (n === 0 || count < 2) return [];
	return Array.from({ length: count }, (_, t) => {
		const frac = t / (count - 1);
		const d = distM[indexAtFraction(n, frac)] ?? nearestNonNull(distM, indexAtFraction(n, frac));
		return { frac, label: `${(d / 1000).toFixed(d >= 10000 ? 0 : 1)}km` };
	});
}

/** 크로스헤어 점의 세로 위치(%, 위=0). Sparkline의 min–max 선형 매핑과 동일. */
export function dotTopPct(values: (number | null)[], v: number | null, invert: boolean): number | null {
	if (v == null) return null;
	const nums = values.filter((x): x is number => x != null);
	if (nums.length === 0) return null;
	const mn = Math.min(...nums);
	const mx = Math.max(...nums);
	if (mx === mn) return 50;
	const frac = (v - mn) / (mx - mn);
	return (invert ? frac : 1 - frac) * 100;
}

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

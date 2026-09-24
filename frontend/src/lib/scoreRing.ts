// frontend/src/lib/scoreRing.ts
// 링 게이지 순수 계산 — 값→채움 비율, 원 둘레 dasharray. 테스트: frontend/tests/scoreRing.test.mjs

/** 값(min~max)을 0~1 비율로. null·NaN은 0, 범위 밖은 clamp, max<=min이면 0. */
export function ringFraction(value: number | null | undefined, min = 0, max = 100): number {
	if (value == null || !Number.isFinite(value) || !(max > min)) return 0;
	return Math.min(1, Math.max(0, (value - min) / (max - min)));
}

/** 반지름 r 원에서 frac만큼 채우는 stroke-dasharray 값('채움 나머지'). */
export function ringDash(frac: number, r: number): string {
	const circ = 2 * Math.PI * r;
	const len = Math.min(1, Math.max(0, frac)) * circ;
	return `${len.toFixed(2)} ${(circ - len).toFixed(2)}`;
}

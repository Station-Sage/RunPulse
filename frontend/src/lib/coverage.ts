// 월별 활동 수 → 0~3 농도. 소스 자신의 최대치 대비(소스 간 규모 차이를 지운다).
export function coverageLevels(counts: number[]): (0 | 1 | 2 | 3)[] {
	const max = Math.max(0, ...counts);
	return counts.map((n) => (n <= 0 || max <= 0 ? 0 : n <= max * 0.25 ? 1 : n <= max * 0.6 ? 2 : 3));
}

// 마지막 활동 이후 연속으로 빈 달 수(데이터가 전혀 없으면 null). 이번 달은 아직 진행 중이라 세지 않는다.
export function trailingGap(counts: number[]): number | null {
	const lastIdx = counts.map((n, i) => (n > 0 ? i : -1)).reduce((a, b) => Math.max(a, b), -1);
	if (lastIdx < 0) return null;
	return Math.max(0, counts.length - 2 - lastIdx);
}

// 타임라인 아래 안내 문장. 정상이면 null.
export function coverageNote(counts: number[]): string | null {
	const gap = trailingGap(counts);
	if (gap === null) return null;
	return gap >= 2 ? `최근 ${gap}개월 동안 활동이 없어요 — 동기화가 끊겼을 수 있어요.` : null;
}

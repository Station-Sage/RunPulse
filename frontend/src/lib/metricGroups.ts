// 메트릭 브라우저 — 8의도 그룹 URL 호환·전체 보기 카드 제한.
const LEGACY: Record<string, string> = {
	readiness: 'today',
	prediction: 'race',
	capacity: 'ability',
	efficiency: 'ability',
	hr: 'hr_ref',
	body: 'vitals',
	stress: 'vitals',
	weather: 'env'
};
const KNOWN = new Set(['all', 'today', 'load', 'race', 'ability', 'sleep', 'vitals', 'hr_ref', 'env', 'other']);

export function normalizeCategory(raw: string | null | undefined): string {
	if (!raw) return 'all';
	if (KNOWN.has(raw)) return raw;
	return LEGACY[raw] ?? 'all';
}

// 전체 보기에서 섹션당 보이는 카드 수 — 보조 그룹(환경·심박 기준)은 2개로 줄여 모바일 스크롤을 줄인다.
export function cardLimit(group: string): number {
	return group === 'env' || group === 'hr_ref' ? 2 : 4;
}

export function limitCards<T>(items: T[], group: string, expanded: boolean): { shown: T[]; hidden: number } {
	if (expanded) return { shown: items, hidden: 0 };
	const n = cardLimit(group);
	return { shown: items.slice(0, n), hidden: Math.max(0, items.length - n) };
}

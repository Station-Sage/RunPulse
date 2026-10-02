import type { VerdictEvidence } from './types/index.ts';

/** 근거 칩의 드릴 슬러그 — `m.fearp` → `fearp`. drill이 아니거나 target이 없으면 null. */
export function verdictDrillSlug(e: VerdictEvidence): string | null {
	if (e.kind !== 'drill' || !e.target) return null;
	const slug = e.target.startsWith('m.') ? e.target.slice(2) : e.target;
	return slug || null;
}

/** 칩은 최대 3개만 보여준다(드릴 가능한 근거 우선, 원래 순서 유지). */
export function pickVerdictEvidence(evidence: VerdictEvidence[], max = 3): VerdictEvidence[] {
	const drill = evidence.filter((e) => verdictDrillSlug(e) !== null);
	const rest = evidence.filter((e) => verdictDrillSlug(e) === null);
	const keep = new Set([...drill, ...rest].slice(0, max));
	return evidence.filter((e) => keep.has(e));
}

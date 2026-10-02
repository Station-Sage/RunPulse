// 활동 상세 헤더 순수 로직 — 출처 병합 배지, 뒤로가기 목적지(F-UX-05/F-UX-12).
import { providerLabelCompact } from './provider.ts';
import type { ProviderKey } from '$lib/types';

export interface SiblingSource {
	id: number;
	provider: string;
	is_canonical: boolean;
}

/** "Garmin ★ · Intervals" — 대표 소스(★)를 맨 앞에. 형제 없으면 단일 이름. */
export function mergedSourceLabel(source: string, siblings: SiblingSource[] | undefined): string {
	const list = siblings && siblings.length > 0 ? siblings : [];
	if (list.length <= 1) return providerLabelCompact(source as ProviderKey);
	const ordered = [...list].sort((a, b) => Number(b.is_canonical) - Number(a.is_canonical));
	return ordered
		.map((s) => providerLabelCompact(s.provider as ProviderKey) + (s.is_canonical ? ' ★' : ''))
		.join(' · ');
}

const FROM_LABELS: Record<string, { label: string; path: string }> = {
	today: { label: '오늘', path: '/' },
	coach: { label: '코치', path: '/coach' },
	plan: { label: '계획', path: '/plan' },
	library: { label: '활동', path: '/library/activities' }
};

/** ?from= 값 → 뒤로가기 링크. 알 수 없으면 활동 목록. */
export function backTarget(from: string | null): { label: string; path: string } {
	return (from && FROM_LABELS[from]) || FROM_LABELS.library;
}

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
	metric: { label: '메트릭', path: '/library/metrics' },
	library: { label: '활동', path: '/library/activities' },
	list: { label: '활동', path: '/library/activities' },
	home: { label: 'Library', path: '/library' },
	pb: { label: 'Library', path: '/library' },
	heatmap: { label: 'Library', path: '/library' },
	month: { label: '월별 활동', path: '/library/activities' },
	providers: { label: '소스 비교', path: '/library/providers' }
};

/** ?from= 값 → 뒤로가기 링크. 알 수 없으면 활동 목록. */
export function backTarget(from: string | null): { label: string; path: string } {
	return (from && FROM_LABELS[from]) || FROM_LABELS.library;
}

const WEEKDAY_KO = ['일', '월', '화', '수', '목', '금', '토'];

/** 헤더 날짜 — 올해면 '10/19(토)', 다른 해면 '2024. 10/19(토)'(A-07, wall-clock 날짜). */
export function headerDate(isoDate: string, now: Date = new Date()): string {
	const d = new Date(`${isoDate.slice(0, 10)}T00:00:00Z`);
	const md = `${d.getUTCMonth() + 1}/${d.getUTCDate()}(${WEEKDAY_KO[d.getUTCDay()]})`;
	return d.getUTCFullYear() === now.getFullYear() ? md : `${d.getUTCFullYear()}. ${md}`;
}

/** 받침에 따라 '으로'/'로' — ㄹ 받침은 '로'. 한글이 아니면 '로'(E-28). */
export function withEuro(word: string): string {
	const code = word.charCodeAt(word.length - 1) - 0xac00;
	if (code < 0 || code > 11171) return `${word}로`;
	const jong = code % 28;
	return jong === 0 || jong === 8 ? `${word}로` : `${word}으로`;
}

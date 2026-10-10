// /welcome 온보딩 단계 전이·리다이렉트 판정 — DESIGN-P7-REVIEW03 §2.3, 40 design §2.10.
import type { OnboardingState } from './api/me';

export const LAST_STEP = 4;
export type RangeKey = '90d' | '1y' | 'all';

export const RANGES: { key: RangeKey; label: string; recommended?: boolean }[] = [
	{ key: '90d', label: '최근 90일', recommended: true },
	{ key: '1y', label: '최근 1년' },
	{ key: 'all', label: '전체' }
];

export function clampStep(n: unknown): number {
	const v = Number(n);
	return Number.isInteger(v) && v >= 0 && v <= LAST_STEP ? v : 0;
}

export const nextStep = (s: number) => Math.min(LAST_STEP, clampStep(s) + 1);
export const prevStep = (s: number) => Math.max(0, clampStep(s) - 1);
export const isLast = (s: number) => clampStep(s) >= LAST_STEP;

/** 소스 0개·활동 0건·온보딩 미종료일 때만 /welcome으로 보낸다. */
export function shouldRedirect(
	sync: { connected_count: number; activity_count: number } | null,
	onboarding: OnboardingState
): boolean {
	if (!sync || onboarding !== 'pending') return false;
	return sync.connected_count === 0 && sync.activity_count === 0;
}

const iso = (d: Date) => d.toISOString().slice(0, 10);

export function rangeFor(key: RangeKey, today: Date = new Date()): { from: string; to: string } {
	const from = new Date(today);
	if (key === '90d') from.setDate(from.getDate() - 90);
	else if (key === '1y') from.setFullYear(from.getFullYear() - 1);
	else from.setFullYear(2000, 0, 1);
	return { from: iso(from), to: iso(today) };
}

/** 추정 소요 시간 라벨 — "최근 90일 · 약 3분". 요청 수 기준 대략치(분당 ~20요청). */
export function etaLabel(label: string, requests: number | null | undefined): string {
	if (!requests || requests <= 0) return label;
	return `${label} · 약 ${Math.max(1, Math.round(requests / 20))}분`;
}

/** ?step= 쿼리 → 시작 단계. 저장된 단계보다 쿼리가 우선(OAuth 복귀). */
export function startStep(query: string | null, saved: number): number {
	return query === null ? clampStep(saved) : clampStep(query);
}

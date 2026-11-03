// 토스트 정책(순수) — 오류는 자동으로 닫지 않고 assertive 로 공지, 그 외는 5초 후 닫고 polite.
import type { Politeness } from './announce.ts';

export type ToastLevel = 'info' | 'error';

export function toastPolicy(level: ToastLevel, durationMs = 5000): { politeness: Politeness; autoCloseMs: number | null } {
	return level === 'error'
		? { politeness: 'assertive', autoCloseMs: null }
		: { politeness: 'polite', autoCloseMs: durationMs };
}

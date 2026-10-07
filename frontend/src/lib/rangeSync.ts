// 기간 동기화 폼의 순수 로직 — 입력 검증과 추정 결과 문구.
import type { SyncEstimate } from '$lib/api/data';

export function validateRange(from: string, to: string, today: string): string | null {
	if (!from || !to) return '시작일과 종료일을 고르세요';
	if (from > to) return '시작일이 종료일보다 늦어요';
	if (to > today) return '종료일이 오늘보다 늦어요';
	return null;
}

export interface EstimateView {
	canStart: boolean;
	lines: string[];
}

export function estimateView(e: SyncEstimate): EstimateView {
	const lines = [`약 ${e.requests}회 요청 (${e.days}일, ${e.batches}묶음)`];
	const { window_15m_left: w, daily_left: d } = e.rate_limit;
	lines.push(`남은 한도: 15분 ${w}회 · 오늘 ${d}회`);
	if (!e.allowed) lines.push(e.message_ko ?? '이 기간은 한 번에 가져올 수 없어요');
	else if (e.message_ko) lines.push(e.message_ko);
	if (e.allowed && e.requests > d) lines.push('오늘 남은 한도보다 많아 중간에 멈출 수 있어요');
	return { canStart: e.allowed, lines };
}

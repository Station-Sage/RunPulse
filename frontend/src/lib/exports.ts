// 내보내기 화면 표시 헬퍼.
import type { ExportItem } from '$lib/api/data';

export function formatBytes(n: number): string {
	if (n < 1024) return `${n}B`;
	if (n < 1024 * 1024) return `${(n / 1024).toFixed(0)}KB`;
	return `${(n / 1024 / 1024).toFixed(1)}MB`;
}

export function expiryText(item: ExportItem, now: Date = new Date()): string {
	if (item.state === 'expired') return '보관 기간이 지났어요';
	if (!item.result) return '';
	const days = Math.ceil((new Date(item.result.expires_at).getTime() - now.getTime()) / 86400000);
	return days <= 1 ? '오늘까지 받을 수 있어요' : `${days}일 안에 받을 수 있어요`;
}

export function rangeBody(from: string, to: string): { from?: string; to?: string } {
	return { ...(from ? { from } : {}), ...(to ? { to } : {}) };
}

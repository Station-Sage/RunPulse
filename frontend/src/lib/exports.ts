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

const ERROR_TEXT: Record<string, string> = {
	EXPORT_SECRET_DETECTED: '민감한 값이 섞여 있어 안전을 위해 만들지 않았어요',
	EXPORT_DISK_FULL: '저장 공간이 부족해요',
	EXPORT_FAILED: '파일을 만들지 못했어요'
};

export function errorText(item: ExportItem): string {
	const base = (item.error_code && ERROR_TEXT[item.error_code]) || '실패';
	return item.error && !item.error_code ? `${base} — ${item.error}` : base;
}

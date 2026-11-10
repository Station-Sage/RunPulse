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

/** D-02: 훈련 계획 ICS 는 v2 밖(Flask 루트) 라우트라 `{base}` 를 붙이지 않는다. 이번 주(월~일) 계획만 담긴다. */
export const PLAN_ICS_URL = '/training/export.ics';
export const PLAN_ICS_NAME = 'runpulse-training.ics';

/** D-16: 받은 CSV 의 데이터 행 수(X-Export-Rows)가 0 이면 안내 문구. 헤더가 없으면(null) 말하지 않는다. */
export function quickResultText(rows: number | null): string {
	return rows === 0 ? '이 기간에는 기록이 없어 머리글만 담았어요' : '';
}

/** D-18: 아카이브 진행 문구 — 테이블 단위 완료/전체. */
export function progressText(item: ExportItem): string {
	const p = item.progress;
	return p && p.total > 0 ? `만드는 중… ${Math.min(p.done, p.total)}/${p.total}` : '만드는 중…';
}

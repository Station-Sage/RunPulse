// Data 영역 표시 규칙 — 서브탭·실행 상태 라벨·용량 포맷 (40 design §2.4).
export const DATA_TABS = [
	{ href: '/data', label: '개요' },
	{ href: '/data/sync', label: '동기화' },
	{ href: '/data/sources', label: '소스' },
	{ href: '/data/export', label: '내보내기' },
	{ href: '/data/settings', label: '설정' }
] as const;

/** 현재 경로(base 제거됨)에 해당하는 탭 href — 소스 상세는 '소스' 탭으로 묶는다 */
export function activeDataTab(rel: string): string {
	const p = rel.replace(/\/$/, '') || '/data';
	if (p.startsWith('/data/sources')) return '/data/sources';
	return DATA_TABS.some((t) => t.href === p) ? p : '/data';
}

const STATUS_LABEL: Record<string, string> = {
	completed: '완료',
	running: '진행 중',
	pending: '대기',
	paused: '일시정지',
	stopped: '중지됨',
	failed: '실패',
	rate_limited: '요청 한도',
	auth_required: '재인증 필요'
};

export const runStatusLabel = (status: string): string => STATUS_LABEL[status] ?? status;

export const runIsBad = (status: string): boolean =>
	status === 'failed' || status === 'rate_limited' || status === 'auth_required';

export function formatBytes(n: number): string {
	if (n < 1024) return `${n} B`;
	if (n < 1024 * 1024) return `${(n / 1024).toFixed(0)} KB`;
	if (n < 1024 ** 3) return `${(n / 1024 / 1024).toFixed(1)} MB`;
	return `${(n / 1024 ** 3).toFixed(2)} GB`;
}

/** D-31: 자동 동기화 시각 — 오늘/어제/내일이면 그 말을, 아니면 날짜를 붙인다(iso 는 서버 로컬 벽시계). */
export function scheduleTime(iso: string | null, todayLocal: string): string | null {
	if (!iso || iso.length < 16) return null;
	const day = iso.slice(0, 10);
	const hm = iso.slice(11, 16);
	const diff = Math.round((Date.parse(`${day}T00:00:00Z`) - Date.parse(`${todayLocal}T00:00:00Z`)) / 86400000);
	const word = diff === 0 ? '오늘' : diff === -1 ? '어제' : diff === 1 ? '내일' : `${Number(day.slice(5, 7))}월 ${Number(day.slice(8, 10))}일`;
	return `${word} ${hm}`;
}

export function runRange(from: string | null, to: string | null): string {
	if (!from || !to) return '';
	const md = (d: string) => d.slice(5).replace('-', '/');
	return from === to ? md(from) : `${md(from)}~${md(to)}`;
}

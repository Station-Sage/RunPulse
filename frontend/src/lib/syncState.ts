// SyncState 계약(GET /api/v1/data/sync-state) 타입과 Pill·패널 표시 규칙 — 40 design §2.1~2.3, §3.2.
export type SyncSourceState =
	| 'not_connected'
	| 'disabled'
	| 'running'
	| 'never'
	| 'idle-ok'
	| 'idle-stale'
	| 'error-auth'
	| 'error-access'
	| 'error-upstream';

export interface SyncSource {
	provider: string;
	connection: 'connected' | 'not_connected';
	enabled: boolean;
	state: SyncSourceState;
	last_attempt_at: string | null;
	last_success_at: string | null;
	last_new_data_at: string | null;
	last_error: { code: string; message_ko: string; action: string } | null;
	running: { job_id: number; progress_pct: number } | null;
}

export interface SyncState {
	as_of: string;
	latest_data_date: string | null;
	overall: { level: 'ok' | 'stale' | 'error' | 'running'; label_ko: string; last_success_at: string | null };
	connected_count: number;
	first_sync_running: boolean;
	sources: SyncSource[];
	caveats: { code: string; provider: string; days: number }[];
	open_errors: number;
}

export type PillTone = 'ok' | 'stale' | 'error' | 'running' | 'empty';

export interface PillView {
	tone: PillTone;
	glyph: string; // 색 외에 모양으로도 구분(접근성)
	text: string;
}

const PROVIDER_KO: Record<string, string> = {
	garmin: 'Garmin',
	strava: 'Strava',
	intervals: 'Intervals',
	runalyze: 'Runalyze'
};

export const syncProviderName = (p: string): string => PROVIDER_KO[p] ?? p;

function md(date: string): string {
	const [, m, d] = date.split('-');
	return `${Number(m)}/${Number(d)}`;
}

export function relativeAgo(iso: string | null, now: Date): string | null {
	if (!iso) return null;
	const mins = Math.floor((now.getTime() - new Date(iso).getTime()) / 60000);
	if (mins < 1) return '방금';
	if (mins < 60) return `${mins}분 전`;
	if (mins < 60 * 24) return `${Math.floor(mins / 60)}시간 전`;
	return `${Math.floor(mins / (60 * 24))}일 전`;
}

export function pillView(s: SyncState | null, now: Date = new Date()): PillView {
	if (!s) return { tone: 'empty', glyph: '○', text: '동기화 상태' };
	if (s.connected_count === 0) return { tone: 'empty', glyph: '○', text: '기기 연결' };
	const ago = relativeAgo(s.overall.last_success_at, now);
	const date = s.latest_data_date ? md(s.latest_data_date) : null;
	if (s.overall.level === 'running') {
		const n = s.sources.filter((x) => x.state === 'running').length;
		return { tone: 'running', glyph: '⟳', text: `동기화 중 ${n}` };
	}
	if (s.overall.level === 'error') {
		const bad = s.sources.find((x) => x.state.startsWith('error-'));
		return { tone: 'error', glyph: '▲', text: `${bad ? syncProviderName(bad.provider) : '소스'} 확인 필요` };
	}
	const tail = ago ? `${ago}` : '기록 없음';
	if (s.overall.level === 'stale') {
		return { tone: 'stale', glyph: '●', text: `${date ? `${date} 기준 · ` : ''}${tail}` };
	}
	return { tone: 'ok', glyph: '●', text: `${date ? `${date} · ` : ''}${tail}` };
}

export function sourceLine(src: SyncSource, now: Date = new Date()): { glyph: string; text: string } {
	const ago = relativeAgo(src.last_success_at, now);
	switch (src.state) {
		case 'not_connected':
			return { glyph: '○', text: '미연결' };
		case 'disabled':
			return { glyph: '○', text: '동기화 꺼짐' };
		case 'running':
			return { glyph: '⟳', text: `동기화 중 ${src.running?.progress_pct ?? 0}%` };
		case 'never':
			return { glyph: '○', text: '아직 동기화 안 함' };
		case 'idle-stale':
			return { glyph: '●', text: `${ago ?? '오래됨'} · 갱신 필요` };
		case 'idle-ok':
			return { glyph: '●', text: ago ?? '완료' };
		default:
			return { glyph: '▲', text: src.last_error?.message_ko ?? '오류' };
	}
}

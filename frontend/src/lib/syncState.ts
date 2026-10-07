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
	running: { job_id: string | number; progress_pct: number } | null;
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

export const isSyncRunning = (s: SyncState | null): boolean =>
	!!s && (s.first_sync_running || s.sources.some((x) => x.state === 'running'));

/** 트리거 직후 이 시간 동안은 서버 상태가 아직 running이 아니어도 5초 폴링 */
export const TRIGGER_FAST_POLL_MS = 15000;

/** 동기화 진행 중(또는 방금 트리거)엔 5초, 평시엔 60초 주기로 폴링 */
export const pollIntervalMs = (
	s: SyncState | null,
	triggeredAt: number | null = null,
	now: number = Date.now()
): number =>
	isSyncRunning(s) || (triggeredAt !== null && now - triggeredAt < TRIGGER_FAST_POLL_MS) ? 5000 : 60000;

// --- POST /data/sync (sync-trigger-design §4) ---
export interface TriggerSkip {
	provider: string;
	code: string;
	message_ko: string;
	retry_after_sec?: number;
	job_id?: string | number;
}

export interface TriggerResponse {
	runs: { id: string | number; provider: string; state: string; from: string; to: string }[];
	skipped: TriggerSkip[];
}

export interface TriggerOutcome {
	notice: string | null;
	skipped: TriggerSkip[];
	cooldownSec: number | null;
	kick: boolean;
}

// 미연결·꺼짐은 소스 행에 이미 보이므로 안내 줄에서 뺀다
const asSkips = (v: unknown): TriggerSkip[] =>
	Array.isArray(v) ? (v as TriggerSkip[]).filter((x) => x.code !== 'not_connected' && x.code !== 'disabled') : [];

export function outcomeFromResponse(r: TriggerResponse): TriggerOutcome {
	return { notice: null, skipped: asSkips(r.skipped), cooldownSec: null, kick: true };
}

/** 실패 응답(status/code/details) → 화면 문구. 네트워크 오류는 status 0 */
export function outcomeFromError(status: number, details: unknown): TriggerOutcome {
	const d = (details ?? {}) as { retry_after_sec?: number; skipped?: unknown };
	const base = { skipped: [] as TriggerSkip[], cooldownSec: null, kick: false };
	if (status === 409) return { ...base, notice: '이미 동기화 중이에요', kick: true };
	if (status === 429) {
		const sec = Math.max(1, Number(d.retry_after_sec) || 60);
		return { ...base, notice: null, skipped: asSkips(d.skipped), cooldownSec: sec };
	}
	if (status === 422) return { ...base, notice: '연결된 소스가 없어요. 설정에서 연결해 주세요' };
	return { ...base, notice: '요청하지 못했어요. 다시 눌러 주세요' };
}

export function waitLabel(sec: number): string {
	return sec < 60 ? `${Math.max(1, Math.ceil(sec))}초 후 가능` : `${Math.ceil(sec / 60)}분 후 가능`;
}

export function skipLine(s: TriggerSkip): string {
	const name = syncProviderName(s.provider);
	if ((s.code === 'cooldown' || s.code === 'rate_limited') && s.retry_after_sec)
		return `⏱ ${name} ${waitLabel(s.retry_after_sec)}`;
	if (s.code === 'running') return `${name} 이미 동기화 중`;
	return `${name} ${s.message_ko}`;
}

export interface TriggerButtonView {
	label: string;
	disabled: boolean;
	settingsLink?: boolean;
}

export function triggerButtonView(
	s: SyncState,
	ctx: { triggering: boolean; cooldownUntil: number | null; now: number }
): TriggerButtonView {
	if (!s.sources.some((x) => x.connection === 'connected' && x.enabled))
		return { label: '연결된 소스가 없어요', disabled: true, settingsLink: true };
	if (ctx.triggering) return { label: '요청 중…', disabled: true };
	const running = s.sources.filter((x) => x.state === 'running').length;
	if (running > 0) {
		const total = s.sources.filter((x) => x.connection === 'connected' && x.enabled).length;
		return { label: `동기화 중 ${running}/${total}`, disabled: true };
	}
	if (ctx.cooldownUntil !== null && ctx.cooldownUntil > ctx.now)
		return { label: waitLabel((ctx.cooldownUntil - ctx.now) / 1000), disabled: true };
	return { label: '지금 동기화', disabled: false };
}

/** running → 비실행 전이 감지 — 이전엔 어느 소스든 running이었고 지금은 모두 아닐 때만 true */
export function justFinished(prev: SyncState | null, next: SyncState | null): boolean {
	if (!prev || !next) return false;
	const was = prev.sources.some((s) => s.state === 'running');
	const now = next.sources.some((s) => s.state === 'running');
	return was && !now;
}

/** 완료 한 줄 요약 — 전이가 아니면 null. 소스별 건수는 계약에 없어 상태 변화만 센다(D2). */
export function completionSummary(prev: SyncState | null, next: SyncState | null): string | null {
	if (!prev || !next || !justFinished(prev, next)) return null;
	const wasRunning = new Set(prev.sources.filter((s) => s.state === 'running').map((s) => s.provider));
	const after = next.sources.filter((s) => wasRunning.has(s.provider));
	const ok = after.filter((s) => s.state === 'idle-ok').length;
	const bad = after.filter((s) => s.state.startsWith('error-'));
	const parts = ['동기화 완료'];
	if (ok > 0) parts.push(`${ok}개 소스 갱신`);
	if (bad.length > 0) parts.push(`${bad.map((s) => syncProviderName(s.provider)).join('·')} 확인 필요`);
	return parts.join(' · ');
}

// 데이터 영역 API — SyncState 계약(40 design §7.3).
import { apiFetch } from './client';
import type { SyncSource, SyncState, TriggerResponse } from '$lib/syncState';

export const getSyncState = () => apiFetch<SyncState>('/data/sync-state');

// POST는 자동 재시도하지 않는다(중복 시작 방지) — 실패 처리는 syncStore.runTrigger.
export const triggerSync = (sources?: string[]) =>
	apiFetch<TriggerResponse>('/data/sync', {
		method: 'POST',
		body: JSON.stringify({ mode: 'incremental', ...(sources ? { sources } : {}) })
	});

// 중지 요청은 멱등 — 이미 끝난 작업이면 현재 상태만 돌려준다.
export const cancelSyncRun = (id: string | number) =>
	apiFetch<{ id: string; provider: string; state: string; requested: boolean }>(
		`/data/sync/runs/${encodeURIComponent(String(id))}/cancel`,
		{ method: 'POST' }
	);

// --- Data 영역 읽기 API (40 design §7.3) ---

export interface DataRun {
	id: string | number;
	provider: string;
	status: string;
	from_date: string | null;
	to_date: string | null;
	trigger: string | null;
	started_at: string | null;
	finished_at: string | null;
	synced_count: number;
	counts: Record<string, number> | null;
	error_code: string | null;
	last_error: string | null;
}

export interface DataSummary {
	activities: number;
	wellness_days: number;
	period: { first: string | null; last: string | null };
	storage_bytes: number;
	recent_runs: DataRun[];
}

export type DataSourceCard = SyncSource & { activity_count: number };

export interface DataSourceDetail extends DataSourceCard {
	counts: { activities: number; wellness_days: number; streams: number; laps: number };
	coverage: { first: string | null; last: string | null; months: { month: string; count: number }[] };
	recent_runs: DataRun[];
}

export const getDataSummary = () => apiFetch<DataSummary>('/data/summary');
export const getDataSources = () => apiFetch<{ sources: DataSourceCard[] }>('/data/sources');
export const getDataSource = (provider: string) =>
	apiFetch<DataSourceDetail>(`/data/sources/${encodeURIComponent(provider)}`);
export const getDataRuns = (opts: { provider?: string; errorsOnly?: boolean; limit?: number } = {}) => {
	const q = new URLSearchParams();
	if (opts.provider) q.set('provider', opts.provider);
	if (opts.errorsOnly) q.set('errors_only', '1');
	if (opts.limit) q.set('limit', String(opts.limit));
	const s = q.toString();
	return apiFetch<{ runs: DataRun[] }>(`/data/runs${s ? `?${s}` : ''}`);
};

export interface AutoSyncSettings {
	enabled: boolean;
	interval_h: number;
	window_days: number;
	last_run_at: string | null;
	next_run_at: string | null;
}

export const getAutoSync = () => apiFetch<AutoSyncSettings>('/data/sync/auto');
export const patchAutoSync = (
	body: Partial<Pick<AutoSyncSettings, 'enabled' | 'interval_h' | 'window_days'>>
) => apiFetch<AutoSyncSettings>('/data/sync/auto', { method: 'PATCH', body: JSON.stringify(body) });
export const patchSourceEnabled = (provider: string, syncEnabled: boolean) =>
	apiFetch<{ provider: string; sync_enabled: boolean }>(`/data/sources/${encodeURIComponent(provider)}`, {
		method: 'PATCH',
		body: JSON.stringify({ sync_enabled: syncEnabled })
	});

// --- 기간 동기화 (40 design §7.3) ---
export interface SyncEstimate {
	provider: string;
	days: number;
	batches: number;
	requests: number;
	rate_limit: { window_15m_left: number; daily_left: number };
	allowed: boolean;
	message_ko: string | null;
}

export const estimateSync = (provider: string, from: string, to: string) =>
	apiFetch<SyncEstimate>(
		`/data/sync/estimate?provider=${encodeURIComponent(provider)}&from=${from}&to=${to}`
	);

export const triggerRangeSync = (sources: string[], from: string, to: string) =>
	apiFetch<TriggerResponse>('/data/sync', {
		method: 'POST',
		body: JSON.stringify({ mode: 'range', sources, from, to })
	});

// --- 소스 연결·테스트·해제 (40 design §7.3). 키 원문은 응답에 오지 않는다 ---
export interface ConnectResult {
	ok?: boolean;
	message_ko?: string;
	redirect_url?: string;
}

export const connectSource = (
	provider: string,
	body: { api_key?: string; athlete_id?: string; return_to?: string } = {}
) =>
	apiFetch<ConnectResult>(`/data/sources/${encodeURIComponent(provider)}/connect`, {
		method: 'POST',
		body: JSON.stringify(body)
	});

export const testSource = (provider: string) =>
	apiFetch<{ ok: boolean; message_ko: string }>(`/data/sources/${encodeURIComponent(provider)}/test`, {
		method: 'POST'
	});

export const disconnectSource = (provider: string) =>
	apiFetch<{ provider: string; keep_data: boolean }>(
		`/data/sources/${encodeURIComponent(provider)}/disconnect`,
		{ method: 'POST', body: JSON.stringify({ keep_data: true }) }
	);

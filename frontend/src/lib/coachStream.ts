// Coach 답변 스트림 상태 기계(30-coach-chat design §6.2·§7.1) — SSE 이벤트를 화면 상태로 접는 순수 로직.
// phase: pending → working → streaming → done | fallback | error | cancelled. 네트워크 계층은 api/coachSse.ts.

export type StreamPhase = 'pending' | 'working' | 'streaming' | 'done' | 'fallback' | 'error' | 'cancelled';

export interface StreamStage {
	key: string;
	label: string;
}

export interface StreamState {
	phase: StreamPhase;
	text: string;
	stages: StreamStage[];
	lastEventId: number;
	/** 폴백이 일어났음 — 이후 delta는 규칙 답변이다. */
	fallbackReason: string | null;
	/** error 단계의 서버 사유(reasonText 키). */
	errorReason: string | null;
	terminal: boolean;
}

export const SLOW_MS = 20_000;
export const MAX_RECONNECTS = 3;
export const POLL_MS = 2_000;

export function initialStream(): StreamState {
	return {
		phase: 'pending', text: '', stages: [], lastEventId: 0,
		fallbackReason: null, errorReason: null, terminal: false
	};
}

type Json = Record<string, unknown>;

function upsertStage(stages: StreamStage[], key: string, label: string): StreamStage[] {
	const i = stages.findIndex((s) => s.key === key);
	if (i < 0) return [...stages, { key, label }];
	return stages.map((s, j) => (j === i ? { key, label } : s));
}

/** 이벤트 하나를 반영한 새 상태. 이미 본 id(Last-Event-ID 재전송)와 종료 후 이벤트는 무시한다. */
export function applyEvent(state: StreamState, name: string, data: unknown, id?: number): StreamState {
	if (state.terminal) return state;
	if (id !== undefined && id <= state.lastEventId) return state;
	const next: StreamState = { ...state, lastEventId: id ?? state.lastEventId };
	const d = (data ?? {}) as Json;
	switch (name) {
		case 'stage':
			next.stages = upsertStage(state.stages, String(d.key ?? ''), String(d.label ?? ''));
			if (state.phase === 'pending') next.phase = 'working';
			break;
		case 'delta':
			next.text = state.text + String(d.text ?? '');
			next.phase = 'streaming';
			break;
		case 'error':
			if (d.status === 'fallback') {
				next.fallbackReason = (d.reason as string | null) ?? 'unknown';
				next.stages = [];
				next.text = '';
			} else {
				next.phase = 'error';
				next.errorReason = (d.reason as string | null) ?? 'internal';
				next.terminal = true;
			}
			break;
		case 'done': {
			const s = d.status as string;
			next.phase = s === 'fallback' || s === 'cancelled' || s === 'error' ? s : 'done';
			next.terminal = true;
			break;
		}
		default:
			break;
	}
	return next;
}

/** 마지막 이벤트 이후 SLOW_MS 넘게 조용하면 "느림" 안내. 종료 상태에서는 없다. */
export function isSlow(state: StreamState, lastEventAt: number, now: number): boolean {
	return !state.terminal && now - lastEventAt >= SLOW_MS;
}

/** 연결이 끊긴 횟수 → 다음 행동. 3회 실패하면 폴링으로 내려간다. */
export function reconnectStep(failures: number): 'retry' | 'poll' {
	return failures >= MAX_RECONNECTS ? 'poll' : 'retry';
}

/** 지금 보여줄 단계 문구("◌ 데이터 확인 중: …") — 마지막 stage, 없으면 기본 문구. */
export function stageLine(state: StreamState): string {
	if (state.phase === 'pending') return '답변 준비 중…';
	const last = state.stages[state.stages.length - 1];
	return last?.label ? `${last.label}…` : '답변 작성 중…';
}

/** 서버 메시지 status → 진행 중(스트림을 열어야 하는) 여부. */
export function isPendingStatus(status: string | undefined): boolean {
	return status === 'pending' || status === 'working';
}

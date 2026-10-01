// Coach 답변 SSE 연결 — EventSource 자동 재연결(Last-Event-ID) → 3회 실패 시 2초 폴링(design §6.2).
import { getMessage } from './coach';
import { MAX_RECONNECTS, POLL_MS, reconnectStep } from '$lib/coachStream';
import type { ChatMessage } from '$lib/types';

const EVENTS = ['stage', 'delta', 'evidence', 'done', 'error'] as const;

export interface StreamHandlers {
	onEvent: (name: string, data: unknown, id: number) => void;
	/** 연결이 끊겨 다시 잇는 중이면 true, 복구되면 false. */
	onReconnecting: (reconnecting: boolean) => void;
	/** 폴링으로 내려간 뒤 서버 행이 더는 진행 중이 아닐 때 최종 메시지. */
	onPolled: (message: ChatMessage) => void;
}

export interface StreamHandle {
	close: () => void;
}

export function openMessageStream(messageId: number, handlers: StreamHandlers, lastEventId = 0): StreamHandle {
	let closed = false;
	let failures = 0;
	let source: EventSource | null = null;
	let pollTimer: ReturnType<typeof setTimeout> | null = null;
	let lastId = lastEventId;

	const close = () => {
		closed = true;
		source?.close();
		if (pollTimer) clearTimeout(pollTimer);
	};

	const poll = async () => {
		if (closed) return;
		try {
			const msg = await getMessage(messageId);
			if (msg.status !== 'pending' && msg.status !== 'working') {
				close();
				handlers.onPolled(msg);
				return;
			}
		} catch {
			// 네트워크가 아직 안 돌아왔다 — 계속 폴링한다.
		}
		if (!closed) pollTimer = setTimeout(poll, POLL_MS);
	};

	const connect = () => {
		source = new EventSource(`/api/v1/coach/messages/${messageId}/stream?last_event_id=${lastId}`);
		source.onopen = () => {
			failures = 0;
			handlers.onReconnecting(false);
		};
		for (const name of EVENTS) {
			source.addEventListener(name, (ev) => {
				const me = ev as MessageEvent<string>;
				const id = Number(me.lastEventId) || lastId + 1;
				lastId = id;
				failures = 0;
				handlers.onReconnecting(false);
				let data: unknown = null;
				try {
					data = JSON.parse(me.data);
				} catch {
					return;
				}
				handlers.onEvent(name, data, id);
			});
		}
		source.onerror = () => {
			if (closed) return;
			failures += 1;
			handlers.onReconnecting(true);
			if (reconnectStep(failures) === 'poll' || failures > MAX_RECONNECTS) {
				source?.close();
				void poll();
			}
			// 그 전에는 EventSource가 Last-Event-ID를 실어 스스로 다시 연결한다.
		};
	};

	connect();
	return { close };
}

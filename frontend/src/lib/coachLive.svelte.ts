// 진행 중인 Coach 답변들의 실시간 상태 — 메시지별 StreamState + 느림/재연결 플래그 (design §6.2·§7.1).
// 종료(done/error) 이벤트가 오면 스트림을 닫고 서버 행을 다시 읽어 onSettled로 넘긴다.
import { applyEvent, initialStream, isSlow, type StreamState } from './coachStream';
import { getMessage } from './api/coach';
import { openMessageStream, type StreamHandle } from './api/coachSse';
import type { ChatMessage } from './types';

export interface LiveEntry {
	stream: StreamState;
	slow: boolean;
	reconnecting: boolean;
}

export class CoachLive {
	entries = $state<Record<number, LiveEntry>>({});
	private handles = new Map<number, StreamHandle>();
	private lastEventAt = new Map<number, number>();
	private timer: ReturnType<typeof setInterval> | null = null;

	constructor(private onSettled: (message: ChatMessage) => void) {}

	/** pending 메시지의 스트림을 연다. 이미 보고 있으면 무시. */
	watch(messageId: number): void {
		if (this.handles.has(messageId)) return;
		this.entries[messageId] = { stream: initialStream(), slow: false, reconnecting: false };
		this.lastEventAt.set(messageId, Date.now());
		this.handles.set(
			messageId,
			openMessageStream(messageId, {
				onEvent: (name, data, id) => this.event(messageId, name, data, id),
				onReconnecting: (r) => this.patch(messageId, { reconnecting: r }),
				onPolled: (msg) => this.settle(messageId, msg)
			})
		);
		this.timer ??= setInterval(() => this.tick(), 1000);
	}

	private patch(id: number, p: Partial<LiveEntry>): void {
		const cur = this.entries[id];
		if (cur) this.entries[id] = { ...cur, ...p };
	}

	private event(id: number, name: string, data: unknown, eid: number): void {
		const cur = this.entries[id];
		if (!cur) return;
		this.lastEventAt.set(id, Date.now());
		const stream = applyEvent(cur.stream, name, data, eid);
		this.entries[id] = { ...cur, stream, slow: false, reconnecting: false };
		if (stream.terminal) void this.finish(id);
	}

	private async finish(id: number): Promise<void> {
		this.handles.get(id)?.close();
		try {
			this.settle(id, await getMessage(id));
		} catch {
			// 서버 행을 못 읽으면 스트림이 만든 화면 상태를 그대로 둔다.
			this.drop(id);
		}
	}

	private settle(id: number, msg: ChatMessage): void {
		this.drop(id);
		this.onSettled(msg);
	}

	private drop(id: number): void {
		this.handles.get(id)?.close();
		this.handles.delete(id);
		this.lastEventAt.delete(id);
		delete this.entries[id];
		if (this.handles.size === 0 && this.timer) {
			clearInterval(this.timer);
			this.timer = null;
		}
	}

	private tick(): void {
		const now = Date.now();
		for (const [id, e] of Object.entries(this.entries)) {
			const slow = isSlow(e.stream, this.lastEventAt.get(Number(id)) ?? now, now);
			if (slow !== e.slow) this.patch(Number(id), { slow });
		}
	}

	/** "계속 기다리기" — 느림 안내만 접고 20초를 다시 센다. */
	keepWaiting(id: number): void {
		this.lastEventAt.set(id, Date.now());
		this.patch(id, { slow: false });
	}

	/** 사용자가 취소/대체했을 때 스트림만 정리한다(서버 행 갱신은 호출 쪽 몫). */
	stop(id: number): void {
		this.drop(id);
	}

	stopAll(): void {
		for (const id of [...this.handles.keys()]) this.drop(id);
	}
}

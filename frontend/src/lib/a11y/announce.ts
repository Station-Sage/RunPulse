// R3 — 화면낭독 공지 발신(순수 큐). LiveRegion 이 구독해 상시 영역에 비웠다 채운다.
export type Politeness = 'polite' | 'assertive';
export type Listener = (level: Politeness, text: string) => void;

const DEDUP_MS = 1000;

export function createAnnouncer(now: () => number = Date.now) {
	const listeners = new Set<Listener>();
	const last = new Map<string, number>();

	function announce(text: string | null | undefined, level: Politeness = 'polite'): boolean {
		const t = (text ?? '').trim();
		if (!t) return false;
		const key = `${level}|${t}`;
		const at = now();
		const prev = last.get(key);
		if (prev !== undefined && at - prev < DEDUP_MS) return false;
		last.set(key, at);
		for (const [k, v] of last) if (at - v >= DEDUP_MS) last.delete(k);
		for (const l of listeners) l(level, t);
		return true;
	}

	function subscribe(l: Listener): () => void {
		listeners.add(l);
		return () => listeners.delete(l);
	}

	return { announce, subscribe };
}

const shared = createAnnouncer();
export const announce = shared.announce;
export const subscribeAnnounce = shared.subscribe;

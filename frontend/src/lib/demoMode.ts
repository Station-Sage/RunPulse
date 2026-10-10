// /demo 체험 모드 — 합성 러너 스냅샷을 fetch 층에서 대신 응답하고, 쓰기는 시트로 돌린다(REVIEW03 §2.2).
// 같은 컴포넌트를 그대로 쓰기 위해 화면 코드는 건드리지 않고 window.fetch만 감싼다.

import { writable } from 'svelte/store';

export const DEMO_FLAG = 'runpulse.demo';
const API_PREFIX = '/api/v1';

export type DemoDecision =
	| { kind: 'pass' }
	| { kind: 'read'; key: string }
	| { kind: 'blocked' };

/** 요청을 분류한다: API가 아니면 통과, GET이면 스냅샷 키, 그 외 쓰기는 차단. */
export function classifyRequest(method: string | undefined, url: string): DemoDecision {
	const path = url.startsWith('http') ? url.replace(/^https?:\/\/[^/]+/, '') : url;
	if (!path.startsWith(API_PREFIX)) return { kind: 'pass' };
	if ((method ?? 'GET').toUpperCase() !== 'GET') return { kind: 'blocked' };
	return { kind: 'read', key: snapshotKey(path) };
}

/** `/api/v1/today?x=1` → `/today?x=1` (쿼리 순서는 정렬해 안정화). */
export function snapshotKey(path: string): string {
	const [p, q] = path.slice(API_PREFIX.length).split('?');
	if (!q) return p;
	const params = [...new URLSearchParams(q).entries()].sort(([a], [b]) => a.localeCompare(b));
	return `${p}?${new URLSearchParams(params).toString()}`;
}

export type Snapshot = Record<string, unknown>;

const json = (status: number, body: unknown) =>
	new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });

export function demoResponse(decision: DemoDecision, snap: Snapshot): Response | null {
	if (decision.kind === 'pass') return null;
	if (decision.kind === 'blocked') {
		return json(403, { error: { code: 'DEMO_READONLY', message: '데모에서는 저장되지 않아요' } });
	}
	const hit = snap[decision.key];
	if (hit === undefined) {
		return json(404, { error: { code: 'DEMO_NOT_AVAILABLE', message: '데모에 없는 화면이에요' } });
	}
	return json(200, hit);
}

export function isDemoActive(): boolean {
	return typeof sessionStorage !== 'undefined' && sessionStorage.getItem(DEMO_FLAG) === '1';
}

/** 배너·시트·셸 표시용 — installDemo/exitDemo가 갱신한다. */
export const demoActive = writable(false);

type Listener = () => void;
const writeListeners = new Set<Listener>();
export function onDemoWrite(fn: Listener): () => void {
	writeListeners.add(fn);
	return () => writeListeners.delete(fn);
}

let realFetch: typeof fetch | null = null;
let snapshot: Snapshot | null = null;

async function loadSnapshot(): Promise<Snapshot> {
	if (!snapshot) {
		const res = await (realFetch ?? fetch)('/v2/demo/snapshot.json');
		if (!res.ok) throw new Error('snapshot');
		snapshot = (await res.json()) as Snapshot;
	}
	return snapshot;
}

/** fetch를 감싼다(멱등). 스냅샷을 못 읽으면 reject — 호출부가 오류 화면을 보인다. */
export async function installDemo(): Promise<void> {
	if (typeof window === 'undefined') return;
	sessionStorage.setItem(DEMO_FLAG, '1');
	if (realFetch) {
		demoActive.set(true);
		return;
	}
	realFetch = window.fetch.bind(window);
	try {
		await loadSnapshot();
	} catch (e) {
		window.fetch = realFetch;
		realFetch = null;
		sessionStorage.removeItem(DEMO_FLAG);
		throw e;
	}
	demoActive.set(true);
	window.fetch = async (input, init) => {
		const url = typeof input === 'string' ? input : input instanceof URL ? input.href : input.url;
		const method = init?.method ?? (typeof input === 'object' && 'method' in input ? input.method : 'GET');
		const decision = classifyRequest(method, url);
		if (decision.kind === 'blocked') writeListeners.forEach((fn) => fn());
		return demoResponse(decision, snapshot ?? {}) ?? realFetch!(input, init);
	};
}

export function exitDemo(): void {
	sessionStorage.removeItem(DEMO_FLAG);
	demoActive.set(false);
}

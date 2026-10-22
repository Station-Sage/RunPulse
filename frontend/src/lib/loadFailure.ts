// 로드 실패 분류 — 순수 모듈(DOM·Svelte 비의존). design error-retry-common §2.2.
import { ApiError } from './api/client.ts';

export type FailureKind = 'not_found' | 'network' | 'server' | 'aborted';

export interface Failure {
	kind: FailureKind;
	status: number;
	code: string;
	detail: string;
}

export type LoadResult<T> = { ok: true; data: T } | { ok: false; failure: Failure };

// 같은 예외가 두 번 찍히지 않도록 console.error 는 여기(분류 시점)에서만 남긴다(ERR-9).
export function classifyFailure(e: unknown): Failure {
	if (e instanceof ApiError) {
		const detail = `${e.status} ${e.code}`;
		if (e.code === 'ABORTED') return { kind: 'aborted', status: 0, code: e.code, detail };
		if (e.status === 404) return { kind: 'not_found', status: 404, code: e.code, detail };
		if (e.status === 0 || e.code === 'NETWORK')
			return { kind: 'network', status: e.status, code: e.code, detail };
		return { kind: 'server', status: e.status, code: e.code, detail };
	}
	console.error(e);
	const name = e instanceof Error ? e.name : typeof e;
	return { kind: 'server', status: 0, code: 'UNKNOWN', detail: name };
}

// 문구는 초안(TXT-1 미결). 404 는 오류 문구가 아니라 화면별 EmptyState 를 쓴다(ERR-6).
export function failureMessage(kind: FailureKind): string {
	return kind === 'network'
		? '연결이 끊겨 불러오지 못했어요. 연결을 확인하고 다시 시도해 주세요.'
		: '서버 오류로 불러오지 못했어요. 잠시 후 다시 시도해 주세요.';
}

// 404 일 때만 null, 나머지 실패는 다시 던진다.
export async function nullOn404<T>(p: Promise<T>): Promise<T | null> {
	try {
		return await p;
	} catch (e) {
		if (e instanceof ApiError && e.status === 404) return null;
		throw e;
	}
}

export async function toResult<T>(p: Promise<T>): Promise<LoadResult<T>> {
	try {
		return { ok: true, data: await p };
	} catch (e) {
		return { ok: false, failure: classifyFailure(e) };
	}
}

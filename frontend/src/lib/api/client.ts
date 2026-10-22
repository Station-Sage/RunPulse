// 05-tech-architecture.md §4.2 apiFetch 그대로 — 개발/프로덕션 모두 동일 출처 요청.
// 개발 중엔 vite.config.ts의 server.proxy가 /api를 Flask(src/serve.py, 18080)로 프록시한다.

const API_BASE = '/api/v1';

interface ApiErrorBody {
	error?: { code?: string; message?: string; details?: unknown };
}

export class ApiError extends Error {
	code: string;
	status: number;
	details?: unknown;

	constructor(status: number, body: ApiErrorBody) {
		super(body.error?.message ?? 'API 오류');
		this.code = body.error?.code ?? 'UNKNOWN';
		this.status = status;
		this.details = body.error?.details;
	}
}

// 모든 실패를 ApiError 로 정규화한다(design error-retry-common §2.1): 네트워크 → NETWORK(0), 사용자 취소 → ABORTED(0),
// JSON 이 아닌 응답 → BAD_RESPONSE(res.status). 자동 재시도는 하지 않는다(ERR-3).
export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
	let res: Response;
	try {
		res = await fetch(`${API_BASE}${path}`, {
			headers: { 'Content-Type': 'application/json' },
			...init
		});
	} catch (e) {
		const aborted = e instanceof Error && e.name === 'AbortError';
		throw new ApiError(0, {
			error: {
				code: aborted ? 'ABORTED' : 'NETWORK',
				message: aborted ? '요청이 취소되었습니다' : '네트워크 연결 실패'
			}
		});
	}
	let body: unknown;
	try {
		body = await res.json();
	} catch {
		throw new ApiError(res.status, {
			error: { code: 'BAD_RESPONSE', message: `응답을 해석할 수 없습니다 (${res.status})` }
		});
	}
	if (!res.ok) {
		throw new ApiError(res.status, body as ApiErrorBody);
	}
	return (body as { data: T }).data;
}

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

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
	const res = await fetch(`${API_BASE}${path}`, {
		headers: { 'Content-Type': 'application/json' },
		...init
	});
	const body = await res.json();
	if (!res.ok) {
		throw new ApiError(res.status, body as ApiErrorBody);
	}
	return (body as { data: T }).data;
}

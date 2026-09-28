// 드릴다운 스택 URL 파싱 — SvelteKit 의존 없는 순수 함수만(테스트 가능하게 분리).
export const DRILL_MAX_DEPTH = 3;

export function parseDrillStack(url: URL): string[] {
	const raw = url.searchParams.get('drill');
	if (!raw) return [];
	return raw
		.split(',')
		.map((t) => t.trim())
		.filter(Boolean);
}

export function tokenSlug(token: string): string {
	return token.startsWith('m.') ? token.slice(2) : token;
}

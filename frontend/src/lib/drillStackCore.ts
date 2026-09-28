// 드릴다운 스택 URL 파싱 — SvelteKit 의존 없는 순수 함수만(테스트 가능하게 분리).
// 토큰 문법(§C3.3 D1d): `m.{slug}` 또는 활동 scope가 있으면 `m.{slug}@{scope}`.
// scope는 `YYYY-MM-DD`(daily) — 생략하면 호출부가 화면 기준일로 채운다.
export const DRILL_MAX_DEPTH = 3;

export interface DrillTokenParts {
	slug: string;
	scope?: string;
}

export function parseDrillStack(url: URL): string[] {
	const raw = url.searchParams.get('drill');
	if (!raw) return [];
	return raw
		.split(',')
		.map((t) => t.trim())
		.filter(Boolean);
}

export function parseDrillToken(token: string): DrillTokenParts {
	const body = token.startsWith('m.') ? token.slice(2) : token;
	const at = body.indexOf('@');
	if (at === -1) return { slug: body };
	return { slug: body.slice(0, at), scope: body.slice(at + 1) || undefined };
}

export function formatDrillToken(slug: string, scope?: string): string {
	return scope ? `m.${slug}@${scope}` : `m.${slug}`;
}

// 하위 호환 별칭 — 슬러그만 필요한 기존 소비처용.
export function tokenSlug(token: string): string {
	return parseDrillToken(token).slug;
}
